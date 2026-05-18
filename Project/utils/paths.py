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
