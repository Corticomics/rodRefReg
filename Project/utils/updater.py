"""Update checking for RRR.

Phase 1 of the update system (notify-only): this module asks GitHub whether a
newer release exists and reports the result. It does not download or apply
anything — see docs/UPDATE_SYSTEM.md for the full design and later phases.

The network call always runs on a background thread (see ``run_check``) so the
GUI never blocks, and every failure path is swallowed: offline devices simply
get "no result", never an error.
"""

import re

import requests
from PyQt5.QtCore import QObject, QThread, pyqtSignal

from version import __version__ as CURRENT_VERSION

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

    def __init__(self, version, url, notes, available):
        self.version = version      # e.g. "1.1.0" (no leading "v")
        self.url = url              # GitHub release page URL
        self.notes = notes          # release notes / changelog text
        self.available = available  # True if `version` is newer than CURRENT_VERSION


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

    return UpdateInfo(
        version=version,
        url=data.get("html_url") or _RELEASES_PAGE,
        notes=(data.get("body") or "").strip(),
        available=is_newer(version),
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
