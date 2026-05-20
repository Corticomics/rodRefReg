"""Tests for the Phase 2.5a settings-persistence refactor (v1.5.0).

Covers:

- type-aware round-trip of values through the ``system_settings`` SQLite table
  (bool / int / float / str / list / dict via the new ``json`` type tag),
- the one-time legacy-JSON migration plus its sentinel row,
- ``save_settings`` semantics — only managed keys persist; the call merges
  into the in-memory settings dict rather than replacing it,
- regression: ``theme`` is no longer silently dropped on save
  (was missing from the pre-v1.5.0 JSON-keys list),
- the legacy ``settings.json`` is left intact (copy-not-move).

See docs/UPDATE_SYSTEM.md §13.8.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Type-aware round-trip
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(True,                 True,                 id="bool-true"),
        pytest.param(False,                False,                id="bool-false"),
        pytest.param(42,                   42,                   id="int-positive"),
        pytest.param(0,                    0,                    id="int-zero"),
        pytest.param(3.14,                 3.14,                 id="float"),
        pytest.param("hello",              "hello",              id="str-nonempty"),
        pytest.param("",                   "",                   id="str-empty"),
        pytest.param([1, 2, 3],            [1, 2, 3],            id="list-of-int"),
        pytest.param([],                   [],                   id="list-empty"),
        pytest.param({"x": 1, "y": [2, 3]},{"x": 1, "y": [2, 3]},id="nested-dict"),
        pytest.param({},                   {},                   id="dict-empty"),
    ],
)
def test_round_trip_through_db(system_controller, database_handler, value, expected):
    """Each managed value type round-trips through ``system_settings`` unchanged."""
    system_controller._write_setting_to_db("probe", value)
    out = database_handler.get_system_settings()
    assert out["probe"] == expected


# ---------------------------------------------------------------------------
# Defaults and reload precedence
# ---------------------------------------------------------------------------

def test_defaults_returned_when_db_empty_and_no_legacy(system_controller):
    """No legacy file, no DB rows → defaults populate ``self.settings``."""
    assert system_controller.settings["num_hats"] == 1
    assert system_controller.settings["hardware_mode"] == "solenoid"


def test_db_values_override_defaults_on_reload(database_handler):
    """A second ``SystemController`` against the same DB sees prior writes."""
    from controllers.system_controller import SystemController

    sc1 = SystemController(database_handler)
    sc1.save_settings({"num_hats": 8})

    sc2 = SystemController(database_handler)
    assert sc2.settings["num_hats"] == 8
    # Defaults still fill in any keys the DB lacks.
    assert sc2.settings["hardware_mode"] == "solenoid"


# ---------------------------------------------------------------------------
# Legacy-JSON migration
# ---------------------------------------------------------------------------

def test_migration_copies_managed_legacy_keys_into_db(database_handler, write_legacy_settings):
    """Managed keys from a legacy ``settings.json`` are written to ``system_settings``."""
    write_legacy_settings({
        "num_hats": 3,
        "theme": "dark",
        "cage_relays": {"1": 7, "2": 8},
        "unmanaged_key": "should_not_be_copied",
    })
    from controllers.system_controller import SystemController

    sc = SystemController(database_handler)
    out = database_handler.get_system_settings()
    assert out["num_hats"] == 3
    assert out["theme"] == "dark"
    assert out["cage_relays"] == {"1": 7, "2": 8}
    assert "unmanaged_key" not in out, "unmanaged keys must not migrate to the DB"
    assert sc.settings["num_hats"] == 3
    assert sc.settings["theme"] == "dark"


def test_migration_writes_sentinel_even_with_no_legacy_file(system_controller, database_handler):
    """Migration on a fresh device leaves the sentinel so it never re-runs."""
    out = database_handler.get_system_settings()
    assert system_controller._MIGRATION_SENTINEL_KEY in out


def test_migration_is_idempotent_after_sentinel(database_handler, write_legacy_settings):
    """Once the sentinel is set, mutating the legacy file does *not* re-migrate."""
    write_legacy_settings({"num_hats": 5})

    from controllers.system_controller import SystemController
    SystemController(database_handler)                  # first run migrates

    write_legacy_settings({"num_hats": 999, "theme": "wat"})
    SystemController(database_handler)                  # second run must be a no-op

    out = database_handler.get_system_settings()
    assert out["num_hats"] == 5, "migration must not overwrite the DB on a re-run"
    assert "theme" not in out, "migration must not add new keys after sentinel"


def test_migration_does_not_modify_legacy_file(database_handler, write_legacy_settings):
    """Copy-not-move: the legacy ``settings.json`` is read but never written."""
    path = write_legacy_settings({"num_hats": 6})
    before = path.read_bytes()

    from controllers.system_controller import SystemController
    SystemController(database_handler)

    assert path.read_bytes() == before


# ---------------------------------------------------------------------------
# ``save_settings`` semantics
# ---------------------------------------------------------------------------

def test_save_settings_only_persists_managed_keys(system_controller, database_handler):
    """Unmanaged keys (runtime objects, ephemeral state) stay in memory only."""
    runtime_object = object()
    system_controller.save_settings({"num_hats": 7, "an_object": runtime_object})

    out = database_handler.get_system_settings()
    assert out["num_hats"] == 7
    assert "an_object" not in out
    assert system_controller.settings["an_object"] is runtime_object


def test_save_settings_merges_into_in_memory_settings(system_controller):
    """``save_settings`` must merge — unrelated keys must survive a partial save."""
    system_controller.settings["runtime_obj"] = "keepme"
    system_controller.save_settings({"num_hats": 4})

    assert system_controller.settings["num_hats"] == 4
    assert system_controller.settings["runtime_obj"] == "keepme"


# ---------------------------------------------------------------------------
# Regression: the silent ``theme`` drop, fixed in v1.5.0
# ---------------------------------------------------------------------------

def test_theme_now_persists_through_save_settings(system_controller, database_handler):
    """Pre-v1.5.0, ``theme`` was missing from the JSON-keys list and was dropped."""
    system_controller.save_settings({"theme": "dark"})
    out = database_handler.get_system_settings()
    assert out["theme"] == "dark"
