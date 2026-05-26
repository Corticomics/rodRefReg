# Dialog template

Standard pattern for modal dialogs in RRR. Two real-world references:

- [`Project/ui/schedules_hub.py:36`](Project/ui/schedules_hub.py) `ScheduleEditDialog`
  — the canonical schedule-edit dialog (lives *inside* `schedules_hub.py`,
  not as a standalone file).
- [`Project/ui/edit_animal_dialog.py`](Project/ui/edit_animal_dialog.py)
  `EditAnimalDialog` — simpler form-only dialog, parameterized on the
  animal record dict.

## Constructor signature

Always accept the collaborators the dialog needs as explicit arguments;
never reach up through `parent()` to find them.

```python
class MyEditDialog(QDialog):
    def __init__(self, entity, database_handler, system_controller=None, parent=None):
        super().__init__(parent)
        self._entity = entity
        self._database_handler = database_handler
        self._system_controller = system_controller

        self.setWindowTitle(f"Edit: {entity.name}")
        self.setMinimumSize(800, 600)
        self.setModal(True)

        self._load_data()      # DB reads up-front, not inside _init_ui
        self._init_ui()
```

## Why `setModal(True)` and not `exec_()` only

`setModal(True)` plus `exec_()` blocks input to the parent window while the
dialog is open. Using `show()` instead leaves the parent clickable and is a
common source of double-save bugs (operator double-clicks the underlying
list while the dialog still has a pending write).

## Loading data

Pre-fetch from `DatabaseHandler` in a dedicated `_load_*` method called
*before* `_init_ui`, so widget construction has all the values it needs.
Don't query the DB inside paint events, slot bodies, or model
`data()` callbacks — those run on every repaint.

## Saving — return through `accept()`

Connect the OK button to a `_on_accept` slot that:

1. Validates input (raise `QMessageBox.warning` and return early on bad data),
2. Writes via the handler (`self._database_handler.update_xxx(...)`),
3. Calls `self.accept()` to close with `QDialog.Accepted`.

Callers use `if dlg.exec_() == QDialog.Accepted: refresh_list()` to react.

## Don't do this

- Don't write to the DB from `__init__` — operators expect "Cancel" to mean
  "nothing changed."
- Don't subclass the deleted `EditScheduleDialog` from
  `Project/ui/edit_schedule_dialog.py` — that file was removed in Phase 1.
  Use the in-hub `ScheduleEditDialog` as the template instead.
- Don't store the dialog instance on the parent (`self.dlg = ...`) and reuse
  it. Modal dialogs are short-lived; construct on demand, let Python GC.
