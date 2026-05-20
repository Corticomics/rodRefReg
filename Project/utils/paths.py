"""Filesystem locations for RRR persistent data.

Single source of truth for where the application reads and writes its data —
the SQLite database, settings.json, and log files. Phase 2a of the update
system; see docs/UPDATE_SYSTEM.md §13.1 and §14.

On an installed device the launcher exports ``RRR_DATA`` (e.g.
``~/rrr/shared/data``) so data lives separately from the swappable application
code. When ``RRR_DATA`` is unset — a developer running from a git clone, or an
install that predates the blue-green layout — every path falls back to its
historical location, so behaviour is unchanged.
"""

import os

# The application's code directory (.../Project), used only for the legacy
# fallbacks below. This file is .../Project/utils/paths.py.
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_root():
    """Return the configured data directory, or None when unset (legacy mode)."""
    return os.environ.get("RRR_DATA") or None


def data_dir():
    """Directory holding persistent data. Created if it does not exist."""
    root = _data_root()
    if root:
        os.makedirs(root, exist_ok=True)
        return root
    return _PROJECT_DIR


def database_path():
    """Absolute path to the SQLite database file."""
    root = _data_root()
    if root:
        os.makedirs(root, exist_ok=True)
        return os.path.join(root, "rrr_database.db")
    # Legacy: alongside the code.
    return os.path.join(_PROJECT_DIR, "rrr_database.db")


def settings_path():
    """Absolute path to settings.json."""
    root = _data_root()
    if root:
        os.makedirs(root, exist_ok=True)
        return os.path.join(root, "settings.json")
    # Legacy: Project/settings/settings.json.
    return os.path.join(_PROJECT_DIR, "settings", "settings.json")


def secrets_path():
    """Absolute path to the secrets file (mode 0600; gitignored).

    Stored alongside the database/settings; the launcher's ``RRR_DATA`` env
    var decides the location. Phase 2.5b of the update system.
    """
    return os.path.join(data_dir(), "secrets.json")


def pump_log_path():
    """Absolute path to the offline pump-trigger log (pump_log.json)."""
    root = _data_root()
    if root:
        os.makedirs(root, exist_ok=True)
        return os.path.join(root, "pump_log.json")
    # Legacy: CWD-relative; the launcher cd's into Project/.
    return os.path.join(_PROJECT_DIR, "pump_log.json")


def debug_log_path():
    """Absolute path to the runtime debug log."""
    root = _data_root()
    if root:
        logs = os.path.join(os.path.dirname(root.rstrip("/")), "logs")
        os.makedirs(logs, exist_ok=True)
        return os.path.join(logs, "rrr_app_debug.log")
    # Legacy: home directory.
    return os.path.expanduser("~/rrr_app_debug.log")


# ---------------------------------------------------------------------------
# Blue-green layout (~/rrr) — used by the update apply engine (Phase 2c).
# These resolve only when the launcher has exported RRR_HOME; on a developer
# clone they return None and in-app updates are simply unavailable.
# ---------------------------------------------------------------------------

def home_dir():
    """The blue-green home (~/rrr) when running under it, else None."""
    return os.environ.get("RRR_HOME") or None


def releases_dir():
    """Directory holding extracted releases, or None off-device."""
    home = home_dir()
    return os.path.join(home, "releases") if home else None


def current_link():
    """Path of the `current` symlink, or None off-device."""
    home = home_dir()
    return os.path.join(home, "current") if home else None


def previous_link():
    """Path of the `previous` symlink (rollback target), or None off-device."""
    home = home_dir()
    return os.path.join(home, "previous") if home else None


def venv_python():
    """Path to the shared venv's python3, or None off-device."""
    home = home_dir()
    return os.path.join(home, "shared", "venv", "bin", "python3") if home else None


def state_dir():
    """Directory for launcher/update state (created), or None off-device."""
    home = home_dir()
    if not home:
        return None
    path = os.path.join(home, "state")
    os.makedirs(path, exist_ok=True)
    return path


def boot_state_path():
    """Path of the boot sentinel file, or None off-device."""
    state = state_dir()
    return os.path.join(state, "boot.json") if state else None
