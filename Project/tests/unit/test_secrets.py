"""Tests for the Phase 2.5b secrets store (v1.5.1).

Covers:

- ``secrets.json`` is written atomically with mode 0600,
- get/save round-trip, including absent and malformed inputs,
- ``SystemController.save_settings`` routes Slack credentials to the
  secrets file and **never** writes them to ``system_settings``,
- ``SystemController.load_settings`` exposes the secrets in
  ``self.settings`` for backward-compatible reads,
- one-time migration from a v1.5.0 device (creds in ``system_settings``)
  copies them into ``secrets.json`` and removes the DB rows,
- one-time migration from a pre-v1.5.0 device (creds in legacy
  ``settings.json``) copies them into ``secrets.json``,
- the migration is idempotent and sweeps any DB leftovers on re-runs.

See docs/UPDATE_SYSTEM.md §13.8.
"""

from __future__ import annotations

import os
import stat


# ---------------------------------------------------------------------------
# secrets.py primitives
# ---------------------------------------------------------------------------

def test_save_then_get_round_trips(isolated_data_dir):
    from utils import secrets
    assert secrets.save_credentials("xoxb-token", "C0123")
    assert secrets.get_credentials() == {"slack_token": "xoxb-token", "channel_id": "C0123"}


def test_get_returns_empty_when_file_absent(isolated_data_dir):
    from utils import secrets
    assert not secrets.exists()
    assert secrets.get_credentials() == {}


def test_get_returns_empty_when_file_is_malformed(isolated_data_dir):
    from utils import secrets, paths
    with open(paths.secrets_path(), "w") as handle:
        handle.write("not json{{{")
    assert secrets.get_credentials() == {}


def test_save_writes_file_with_mode_0600(isolated_data_dir):
    from utils import secrets, paths
    secrets.save_credentials("x", "y")
    mode = stat.S_IMODE(os.stat(paths.secrets_path()).st_mode)
    assert mode == 0o600, f"expected mode 0600, got {oct(mode)}"


def test_save_leaves_no_temp_files_behind(isolated_data_dir):
    from utils import secrets
    secrets.save_credentials("a", "b")
    leftovers = [name for name in os.listdir(isolated_data_dir) if name.startswith(".secrets-")]
    assert leftovers == []


# ---------------------------------------------------------------------------
# SystemController routing
# ---------------------------------------------------------------------------

def test_save_settings_routes_slack_creds_to_secrets_not_db(system_controller, database_handler):
    from utils import secrets
    system_controller.save_settings({"slack_token": "xoxb-1", "channel_id": "C9"})

    assert secrets.get_credentials() == {"slack_token": "xoxb-1", "channel_id": "C9"}
    db = database_handler.get_system_settings()
    assert "slack_token" not in db
    assert "channel_id" not in db
    assert system_controller.settings["slack_token"] == "xoxb-1"
    assert system_controller.settings["channel_id"] == "C9"


def test_partial_save_preserves_the_other_credential(system_controller):
    from utils import secrets
    system_controller.save_settings({"slack_token": "first", "channel_id": "Cfirst"})
    system_controller.save_settings({"slack_token": "updated"})           # token only
    creds = secrets.get_credentials()
    assert creds["slack_token"] == "updated"
    assert creds["channel_id"] == "Cfirst"                                 # not clobbered


def test_load_settings_merges_secrets_into_in_memory_dict(database_handler, isolated_data_dir):
    from utils import secrets
    from controllers.system_controller import SystemController
    secrets.save_credentials("preset", "Cpre")

    sc = SystemController(database_handler)
    assert sc.settings["slack_token"] == "preset"
    assert sc.settings["channel_id"] == "Cpre"


# ---------------------------------------------------------------------------
# Migration paths
# ---------------------------------------------------------------------------

def test_migration_moves_slack_from_db_to_secrets(database_handler, isolated_data_dir):
    """v1.5.0 -> v1.5.1: 2.5a put creds in system_settings; 2.5b extracts them."""
    from utils import secrets
    database_handler.update_system_setting("slack_token", "from-db", "str")
    database_handler.update_system_setting("channel_id", "Cdb", "str")
    assert not secrets.exists()

    from controllers.system_controller import SystemController
    SystemController(database_handler)

    creds = secrets.get_credentials()
    assert creds["slack_token"] == "from-db"
    assert creds["channel_id"] == "Cdb"
    db = database_handler.get_system_settings()
    assert "slack_token" not in db, "DB row must be removed after migration"
    assert "channel_id" not in db, "DB row must be removed after migration"


def test_migration_copies_legacy_slack_into_secrets(database_handler, write_legacy_settings):
    """Pre-v1.5.0 -> v1.5.1 direct: creds in legacy settings.json move out."""
    from utils import secrets
    write_legacy_settings({"slack_token": "legacy", "channel_id": "Cleg"})
    assert not secrets.exists()

    from controllers.system_controller import SystemController
    SystemController(database_handler)

    creds = secrets.get_credentials()
    assert creds["slack_token"] == "legacy"
    assert creds["channel_id"] == "Cleg"


def test_migration_does_not_overwrite_existing_secrets_file(database_handler, isolated_data_dir):
    """An existing secrets.json wins; a stale DB row is cleaned up anyway."""
    from utils import secrets
    secrets.save_credentials("already-set", "Cset")
    database_handler.update_system_setting("slack_token", "should-be-ignored", "str")

    from controllers.system_controller import SystemController
    SystemController(database_handler)

    assert secrets.get_credentials()["slack_token"] == "already-set"
    # the migration also sweeps stale DB leftovers
    assert "slack_token" not in database_handler.get_system_settings()


def test_migration_on_fresh_device_creates_empty_secrets_file(database_handler, isolated_data_dir):
    """No legacy data anywhere → secrets.json is created empty (marker for the next boot)."""
    from utils import secrets
    from controllers.system_controller import SystemController

    SystemController(database_handler)

    assert secrets.exists()
    assert secrets.get_credentials() == {"slack_token": "", "channel_id": ""}


def test_phase_2_5a_legacy_migration_does_not_copy_slack_keys(database_handler, write_legacy_settings):
    """Regression for the 2.5b half of the contract: the legacy-JSON-to-DB
    migration introduced in 2.5a must no longer copy slack_token / channel_id
    into the DB (those keys are owned by the secrets file in 2.5b)."""
    write_legacy_settings({"slack_token": "leg", "channel_id": "Cleg", "num_hats": 4})

    from controllers.system_controller import SystemController
    SystemController(database_handler)

    db = database_handler.get_system_settings()
    assert db.get("num_hats") == 4, "non-secret keys still migrate to DB"
    assert "slack_token" not in db, "slack_token must not enter system_settings"
    assert "channel_id" not in db, "channel_id must not enter system_settings"
