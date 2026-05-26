---
name: pyqt5-ui-conventions
description: Apply the RRR project's PyQt5 conventions when building or editing UI — RodentRefreshmentGUI main window, ProjectsSection tabs (SchedulesHub + AnimalsTab + WizardTab + CagesVisualizationTab), SettingsTab sub-tabs, dialog patterns, login gating via LoginGateWidget, and the threading boundary between widgets and RelayWorker. Use when adding a tab, a dialog, a widget, hooking up a signal, or touching any file under Project/ui/.
---

# PyQt5 UI conventions

The UI is a single `RodentRefreshmentGUI` window holding a `QTabWidget`.
Every user-facing screen is a tab, a sub-tab, or a modal dialog. This skill
captures the conventions so new UI lands consistently.

## The main window contract

[Project/ui/gui.py](Project/ui/gui.py) `RodentRefreshmentGUI.__init__` takes
these collaborators and stores them as attributes — **the UI never
constructs them itself**:

```python
RodentRefreshmentGUI(
    run_callback, stop_callback, change_relay_callback,
    system_controller, database_handler, login_system,
    relay_handler, notification_handler,
)
```

Construction is in [Project/main.py](Project/main.py)'s `setup()` /
`_create_gui_from_components()`. New widgets that need data should
accept the relevant handler in their `__init__` — never reach into
`gui.parent()` or use globals.

## Live tab tree (truth, post-Phase-1)

```
RodentRefreshmentGUI (QTabWidget)
├── ProjectsSection      ─── QTabWidget
│   ├── SchedulesHub         (card grid; replaces legacy SchedulesTab)
│   ├── AnimalsTab
│   ├── WizardTab            (wraps ScheduleCreationWizard)
│   └── CagesVisualizationTab (relay-board layout + inline cage naming)
├── SettingsTab          ─── QTabWidget
│   ├── Delivery (Hardware/Pump)
│   ├── Calibration         (per-cage; opens CalibrationWizard)
│   ├── Priming             (embeds PrimingControlWidget)
│   ├── General
│   └── Updates             (UpdatesTab; in-app updater)
├── UserTab                  (login / profile)
└── HelpTab                  (uses HelpContentManager)
```

**Do not** instantiate `SchedulesTab`, `CageManagerWidget`,
`AdvancedSettingsSection`, `LoginDialog`, `ProfileDialog`, `IntervalSettings`,
`EditScheduleDialog`, `RelayContainer`, `DragDropContainer`, or
`ScheduleCreationWidget` — they were deleted in Phase 1 as orphans. If you
find a reference to one, treat it as a bug.

## Login gating

[Project/ui/login_gate_widget.py](Project/ui/login_gate_widget.py)
`LoginGateWidget` wraps any inner widget and hides/shows it based on
`LoginSystem.is_logged_in()`. `gui.py` uses it to gate `ProjectsSection`.

```python
self.login_gate = LoginGateWidget(self.projects_section, self.login_system)
left_layout.addWidget(self.login_gate)
```

The pattern is: connect `login_system.login_status_changed` →
widget refresh. Don't poll `is_logged_in()`.

## Signal/slot conventions

- **Signals are defined on the class**, not on instances. Use type hints
  in the `pyqtSignal(...)` declaration when the payload is non-trivial.
- **Cross-thread signals require `Qt.QueuedConnection`**. The relay
  worker thread is the only non-main-thread Qt object you should
  routinely encounter; see the threading skill.
- **One signal, one concern.** `wizard_tab.schedule_created` emits a
  `dict`; `schedules_hub.create_requested` emits nothing — it just asks
  the parent to switch tabs.

Reference pattern (from [projects_section.py:99](Project/ui/projects_section.py#L99)):

```python
self.wizard_tab.schedule_created.connect(self._on_wizard_schedule_created)
self.schedules_tab.create_requested.connect(self._switch_to_wizard)
```

## Card-based components

Card-style UI lives in [Project/ui/components/](Project/ui/components/):

- `card.py` `Card(QFrame)` — non-interactive container with `Card` objectName for QSS.
- `interactive_card.py` `InteractiveCard`, `SelectableCardGroup` — clickable selection.
- `primary_button.py` `PrimaryButton` — branded button.
- `wizard.py` `WizardContainer`, `WizardStep` — used by `schedule_wizard.py`.

The card pattern replaces the older drag-drop schedule UI. If you're
about to write `QListWidget` + drag/drop for a list of *project entities*
(schedules, animals, cages), use cards instead.

## Styling

Centralized QSS in [Project/ui/style/theme.py](Project/ui/style/theme.py)
`StyleManager` + `app-light.qss` / `app-dark.qss`. **No per-widget
`setStyleSheet`** unless the rule is genuinely one-off.
Set `objectName` to a QSS-friendly identifier (`InfoButton`, `Card`,
`Title`) and target it in the global stylesheet.

## Dialogs

See [`references/dialog-template.md`](references/dialog-template.md) for the
standard pattern. Two notes:

- Dialogs that need the database/login system **receive them in
  `__init__`** — don't reach up through `parent()`.
- For schedule editing, the canonical dialog is `ScheduleEditDialog`
  defined **inside** [schedules_hub.py:36](Project/ui/schedules_hub.py#L36),
  not the deleted standalone `EditScheduleDialog`.

## Tabs

See [`references/tab-template.md`](references/tab-template.md) for adding a
new sub-tab. Settings sub-tabs go in `SettingsTab.init_ui`; Projects sub-tabs
go in `ProjectsSection.__init__`. **Do not add a new top-level tab on
`RodentRefreshmentGUI` casually** — that's a significant UX change.

## Threading from a widget

A widget that needs to do non-trivial work should not block the UI thread.
The standard pattern is a `QObject` worker moved to a `QThread`, with
signals using `Qt.QueuedConnection`. See
[`references/threading-checklist.md`](references/threading-checklist.md)
and the implementation in
[Project/gpio/relay_worker.py](Project/gpio/relay_worker.py).

## Don't do this

- Don't import `pandas`/`numpy` from a widget that needs to import cheaply
  (e.g. nothing on the hot import path of the smoke test). `SettingsTab`
  already pulls pandas at top level — accept the existing cost, don't add
  more.
- Don't re-export deleted classes from `Project/ui/__init__.py`. The
  current `__all__` is the public surface; touching it bumps the project
  to a MINOR per MAINTENANCE.md.
- Don't call `QMessageBox.exec_()` from a slot connected to a worker-thread
  signal without `QueuedConnection` — dialogs must run on the main thread.
- Don't add a new `*.ui` (Qt Designer XML) file or `.qrc` resource.
  Current code builds widgets in Python; introducing the XML build step
  is a deliberate decision, not an incremental change.
