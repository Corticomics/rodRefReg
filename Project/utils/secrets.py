"""Credential storage for RRR.

Slack tokens (and any future secrets) live in a dedicated mode-0600 file —
kept separate from the SQLite database and never tracked in git — so they
can be rotated, audited, or wiped without touching the rest of the app
state, and so a leaked database backup never exposes the token.

Phase 2.5b of the update system; see docs/UPDATE_SYSTEM.md §13.8.

The functions here are pure file I/O; the credential lifecycle (load on
startup, route writes from the UI, migrate from the DB or the legacy
``settings.json``) is owned by
:class:`controllers.system_controller.SystemController`.
"""

import json
import os
import tempfile

from utils import paths


def exists() -> bool:
    """True when a secrets file is on disk, regardless of contents."""
    return os.path.exists(paths.secrets_path())


def get_credentials() -> dict:
    """Return the stored credentials, or an empty dict if absent or unreadable.

    Never raises. A malformed file is treated as "no credentials" so a
    hand-edited typo cannot brick the app at startup.
    """
    path = paths.secrets_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as handle:
            data = json.load(handle)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def save_credentials(slack_token: str = "", channel_id: str = "") -> bool:
    """Write the credentials atomically with mode 0600. Returns success.

    The file is created via :func:`tempfile.mkstemp` (which yields a 0600
    file on POSIX), written, then atomically renamed into place — readers
    never see a partial write.
    """
    payload = {
        "slack_token": slack_token or "",
        "channel_id": channel_id or "",
    }
    dest = paths.secrets_path()
    try:
        directory = os.path.dirname(dest) or "."
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".secrets-", dir=directory)
        try:
            with os.fdopen(fd, "w") as handle:
                json.dump(payload, handle, indent=2)
            os.chmod(tmp, 0o600)          # belt-and-braces — mkstemp already 0600
            os.replace(tmp, dest)          # atomic on POSIX
            return True
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    except Exception:
        return False
