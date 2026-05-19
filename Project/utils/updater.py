"""Update checking and applying for RRR.

This module (a) asks GitHub whether a newer release exists and (b) downloads,
verifies, and installs it into the blue-green layout. See docs/UPDATE_SYSTEM.md
§13 and §14.

Network and filesystem work always runs on a background thread (see
``run_check`` / ``run_apply``) so the GUI never blocks; failure paths are
swallowed or returned as messages, never raised into the UI.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile

import requests
from PyQt5.QtCore import QObject, QThread, pyqtSignal

from version import __version__ as CURRENT_VERSION
from utils import paths

# The repository whose Releases are the update channel.
GITHUB_REPO = "Corticomics/rodRefReg"
_LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
_RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases"
_REQUEST_TIMEOUT_S = 10


def _version_tuple(text):
    """Parse ``v1.2.3`` / ``1.2.3`` / ``1.2.3-beta`` into a comparable tuple.

    Returns ``(1, 2, 3)`` or ``None`` if the string is not a recognisable
    MAJOR.MINOR.PATCH version. The pre-release suffix is ignored.
    """
    match = re.match(r"v?(\d+)\.(\d+)\.(\d+)", (text or "").strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def is_newer(candidate, current=CURRENT_VERSION):
    """True when ``candidate`` is a strictly higher version than ``current``."""
    parsed_candidate = _version_tuple(candidate)
    parsed_current = _version_tuple(current)
    if parsed_candidate is None or parsed_current is None:
        return False
    return parsed_candidate > parsed_current


class UpdateInfo:
    """The outcome of a successful update check."""

    def __init__(self, version, url, notes, available,
                 bundle_url=None, sha256_url=None):
        self.version = version      # e.g. "1.1.0" (no leading "v")
        self.url = url              # GitHub release page URL
        self.notes = notes          # release notes / changelog text
        self.available = available  # True if `version` is newer than CURRENT_VERSION
        self.bundle_url = bundle_url  # download URL of the .rrrupdate bundle
        self.sha256_url = sha256_url  # download URL of the .rrrupdate.sha256 file


def fetch_latest():
    """Query GitHub for the latest stable release.

    Returns an :class:`UpdateInfo`, or ``None`` if the check could not be
    completed — offline, rate-limited, or no releases published yet. Never
    raises. Pre-releases (``v*-beta``) are excluded by the GitHub endpoint.
    """
    try:
        response = requests.get(
            _LATEST_RELEASE_API,
            timeout=_REQUEST_TIMEOUT_S,
            headers={"Accept": "application/vnd.github+json"},
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return None

    tag = data.get("tag_name", "")
    version = tag[1:] if tag.startswith("v") else tag
    if _version_tuple(version) is None:
        return None

    # Resolve the bundle + checksum download URLs from the release assets.
    bundle_url = sha256_url = None
    for asset in (data.get("assets") or []):
        name = asset.get("name", "")
        if name.endswith(".rrrupdate.sha256"):
            sha256_url = asset.get("browser_download_url")
        elif name.endswith(".rrrupdate"):
            bundle_url = asset.get("browser_download_url")

    return UpdateInfo(
        version=version,
        url=data.get("html_url") or _RELEASES_PAGE,
        notes=(data.get("body") or "").strip(),
        available=is_newer(version),
        bundle_url=bundle_url,
        sha256_url=sha256_url,
    )


class UpdateCheckWorker(QObject):
    """Runs :func:`fetch_latest` off the GUI thread."""

    finished = pyqtSignal(object)  # emits an UpdateInfo, or None

    def run(self):
        self.finished.emit(fetch_latest())


def run_check(parent, on_done):
    """Run an update check on a background thread.

    ``on_done(info)`` is called when the check finishes, with an
    :class:`UpdateInfo` or ``None``.

    IMPORTANT: ``on_done`` must be a bound method of a QObject that lives on
    the GUI thread (e.g. ``some_widget._on_result``). PyQt then delivers the
    result via a queued connection, so ``on_done`` runs safely on the GUI
    thread. A plain function/closure would run on the worker thread instead.

    ``parent`` (a QObject, typically the calling widget) holds strong
    references to the thread and worker until the check completes, so neither
    is garbage-collected mid-flight.
    """
    thread = QThread()
    worker = UpdateCheckWorker()
    worker.moveToThread(thread)

    holder = getattr(parent, "_rrr_update_checks", None)
    if holder is None:
        holder = []
        parent._rrr_update_checks = holder
    holder.append((thread, worker))

    def _cleanup():
        try:
            holder.remove((thread, worker))
        except ValueError:
            pass

    thread.started.connect(worker.run)
    worker.finished.connect(on_done)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.finished.connect(_cleanup)
    thread.start()
    return thread


# ===========================================================================
# Apply engine (Phase 2c) — download, verify, install, roll back.
# See docs/UPDATE_SYSTEM.md §13.3 and §14.7.
# ===========================================================================

_MIN_FREE_BYTES = 200 * 1024 * 1024   # refuse to apply with less free space
_RELEASES_TO_KEEP = 3

# A delivery schedule must never be interrupted by an update. main.py registers
# a real check here at startup; until then, assume not busy.
_busy_check = lambda: False  # noqa: E731


def set_busy_check(fn):
    """Register a callable returning True while a delivery schedule is running.

    ``apply_update`` refuses to proceed whenever it returns True.
    """
    global _busy_check
    _busy_check = fn


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url, dest):
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as handle:
            for chunk in resp.iter_content(1 << 16):
                handle.write(chunk)


def _fetch_sha256(url):
    """Return the expected hex digest from a .sha256 asset, or None."""
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=_REQUEST_TIMEOUT_S)
        resp.raise_for_status()
        return resp.text.strip().split()[0]
    except Exception:
        return None


def _read_manifest(release_dir):
    try:
        with open(os.path.join(release_dir, "manifest.json")) as handle:
            return json.load(handle)
    except Exception:
        return {}


def _atomic_symlink(target, link):
    """Point `link` at `target` via an atomic rename (never a gap)."""
    tmp = link + ".tmp"
    if os.path.lexists(tmp):
        os.remove(tmp)
    os.symlink(target, tmp)
    os.replace(tmp, link)


def _sync_venv_if_needed(new_dir, venv_python, progress):
    """pip-install the new release's requirements iff they changed."""
    current = paths.current_link()
    old_hash = None
    if current and os.path.exists(current):
        old_hash = _read_manifest(os.path.realpath(current)).get("requirements_hash")
    new_hash = _read_manifest(new_dir).get("requirements_hash")
    req = os.path.join(new_dir, "requirements.txt")
    if new_hash and new_hash == old_hash:
        return  # dependencies unchanged — reuse the venv untouched
    if not (venv_python and os.path.exists(venv_python) and os.path.exists(req)):
        return
    progress("Updating dependencies…")
    subprocess.run(
        [venv_python, "-m", "pip", "install", "--disable-pip-version-check",
         "-q", "-r", req],
        check=True, timeout=600,
    )


def _selftest_release(release_dir, venv_python):
    """Run `<release>/Project/main.py --selftest`. Returns (ok, detail)."""
    if not (venv_python and os.path.exists(venv_python)):
        return True, "venv unavailable; health check skipped"
    main_py = os.path.join(release_dir, "Project", "main.py")
    if not os.path.exists(main_py):
        return False, "release is missing Project/main.py"
    try:
        proc = subprocess.run(
            [venv_python, main_py, "--selftest"],
            cwd=os.path.join(release_dir, "Project"),
            env=dict(os.environ), capture_output=True, text=True, timeout=120,
        )
    except Exception as exc:
        return False, str(exc)
    if proc.returncode == 0:
        return True, "ok"
    return False, (proc.stdout + proc.stderr).strip()[-300:] or "non-zero exit"


def _swap_current(new_dir):
    """Point `current` at new_dir, recording the outgoing release as `previous`."""
    current = paths.current_link()
    previous = paths.previous_link()
    if current and os.path.lexists(current):
        old_target = os.path.realpath(current)
        if os.path.isdir(old_target) and old_target != os.path.realpath(new_dir):
            _atomic_symlink(old_target, previous)
    _atomic_symlink(new_dir, current)


def _prune_releases(keep=_RELEASES_TO_KEEP):
    """Delete old release dirs, never touching `current` or `previous`."""
    releases = paths.releases_dir()
    if not releases or not os.path.isdir(releases):
        return
    protected = set()
    for link in (paths.current_link(), paths.previous_link()):
        if link and os.path.lexists(link):
            protected.add(os.path.realpath(link))
    dirs = [
        os.path.join(releases, name)
        for name in os.listdir(releases)
        if not name.startswith(".") and os.path.isdir(os.path.join(releases, name))
    ]
    spare = [d for d in dirs if d not in protected]
    spare.sort(key=os.path.getmtime, reverse=True)
    for old in spare[keep:]:
        shutil.rmtree(old, ignore_errors=True)


def apply_update(info, progress=lambda message: None):
    """Download, verify, health-check and install the release in ``info``.

    Runs the full apply sequence (docs/UPDATE_SYSTEM.md §14.7). Returns
    ``(ok, message)``. Any failure before the symlink swap leaves the running
    release completely untouched.
    """
    if not paths.home_dir():
        return False, "Updates are only available on an installed device."
    if not info or not getattr(info, "bundle_url", None):
        return False, "No update bundle is available for this release."
    if _busy_check():
        return False, ("A delivery schedule is running. Stop it before "
                        "installing an update.")

    releases = paths.releases_dir()
    new_dir = os.path.join(releases, info.version)
    venv_python = paths.venv_python()

    try:
        if shutil.disk_usage(releases).free < _MIN_FREE_BYTES:
            return False, "Not enough free disk space to install the update."

        with tempfile.TemporaryDirectory(prefix="rrr-dl-") as tmp:
            bundle = os.path.join(tmp, "bundle.rrrupdate")

            progress("Downloading update…")
            _download(info.bundle_url, bundle)

            progress("Verifying download…")
            expected = _fetch_sha256(info.sha256_url)
            if expected and _sha256_file(bundle) != expected:
                return False, "Download verification failed (checksum mismatch)."

            progress("Extracting…")
            staging = os.path.join(releases, ".incoming-%s" % info.version)
            shutil.rmtree(staging, ignore_errors=True)
            os.makedirs(staging)
            with tarfile.open(bundle, "r:gz") as tar:
                tar.extractall(staging)

        # Move the staged release into place (the download tmp is now gone).
        shutil.rmtree(new_dir, ignore_errors=True)
        os.replace(staging, new_dir)

        _sync_venv_if_needed(new_dir, venv_python, progress)

        progress("Health-checking the new version…")
        ok, detail = _selftest_release(new_dir, venv_python)
        if not ok:
            shutil.rmtree(new_dir, ignore_errors=True)
            return False, "The update failed its health check: %s" % detail

        progress("Activating…")
        _swap_current(new_dir)
        _reset_boot_state(info.version)
        _prune_releases()

        return True, ("Version %s installed. Restart RRR to use it."
                       % info.version)
    except Exception as exc:
        return False, "Update failed: %s" % exc


def revert():
    """Roll back to the previous release. Returns ``(ok, message)``."""
    if not paths.home_dir():
        return False, "Rollback is only available on an installed device."
    previous = paths.previous_link()
    if not (previous and os.path.lexists(previous)):
        return False, "There is no previous version to roll back to."
    target = os.path.realpath(previous)
    if not os.path.isdir(os.path.join(target, "Project")):
        return False, "The previous version is no longer available."
    current = paths.current_link()
    if os.path.realpath(current) == target:
        return False, "Already running the previous version."
    if _busy_check():
        return False, "A delivery schedule is running. Stop it before rolling back."

    leaving = os.path.realpath(current)
    _atomic_symlink(leaving, previous)   # so a re-apply path still exists
    _atomic_symlink(target, current)
    version = os.path.basename(target)
    _reset_boot_state(version)
    return True, "Rolled back to version %s. Restart RRR to use it." % version


def _reset_boot_state(release):
    """Clear the boot-failure counter for `release` (see the boot sentinel)."""
    path = paths.boot_state_path()
    if not path:
        return
    try:
        with open(path, "w") as handle:
            json.dump({"release": release, "fail_count": 0}, handle)
    except Exception:
        pass


def mark_boot_healthy():
    """Clear the boot-failure counter — the running release started cleanly.

    Called a few seconds after the GUI is up; without it the launcher's boot
    sentinel would eventually auto-roll-back a release that actually works.
    """
    _reset_boot_state(CURRENT_VERSION)


def has_previous_release():
    """True when a rollback target exists."""
    previous = paths.previous_link()
    return bool(previous and os.path.lexists(previous))


def restart_app():
    """Restart the application. Returns ``(restarted, message)``.

    Restarts the systemd user service when one is active; otherwise the
    operator must relaunch manually (there is no service to bounce).
    """
    try:
        active = subprocess.run(
            ["systemctl", "--user", "is-active", "--quiet", "rrr"], timeout=10
        ).returncode == 0
    except Exception:
        active = False
    if not active:
        return False, "Please close and reopen RRR to finish the update."
    try:
        subprocess.Popen(["systemctl", "--user", "restart", "rrr"])
        return True, "Restarting…"
    except Exception as exc:
        return False, "Could not restart automatically: %s" % exc


class ApplyWorker(QObject):
    """Runs :func:`apply_update` off the GUI thread."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)   # (ok, message)

    def __init__(self, info):
        super().__init__()
        self._info = info

    def run(self):
        ok, message = apply_update(self._info, self.progress.emit)
        self.finished.emit(ok, message)


def run_apply(parent, info, on_progress, on_done):
    """Run :func:`apply_update` on a background thread.

    ``on_progress(str)`` and ``on_done(bool, str)`` must be bound methods of a
    GUI-thread QObject (see :func:`run_check` for why). ``parent`` holds the
    thread/worker references until the job completes.
    """
    thread = QThread()
    worker = ApplyWorker(info)
    worker.moveToThread(thread)

    holder = getattr(parent, "_rrr_apply_jobs", None)
    if holder is None:
        holder = []
        parent._rrr_apply_jobs = holder
    holder.append((thread, worker))

    def _cleanup():
        try:
            holder.remove((thread, worker))
        except ValueError:
            pass

    thread.started.connect(worker.run)
    worker.progress.connect(on_progress)
    worker.finished.connect(on_done)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.finished.connect(_cleanup)
    thread.start()
    return thread
