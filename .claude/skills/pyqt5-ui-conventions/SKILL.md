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
│   ├── Delivery            (hardware mode + valve topology, both guarded; solenoid/pump settings)
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

Log Out has a gate of its own: Stop needs a login, so while a schedule runs
`UserTab` greys Log Out out and `UserTab.logout` refuses (**Schedule
running**). Both read the `schedule_running` callable `gui.py` passes (the
Run/Stop section's `job_in_progress`): the button is refreshed whenever the
operation lock's `state_changed` fires, and `logout()` asks the callable
again when it is called, so a stale button state can never let a logout
through.

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

- `card.py` `Card(QFrame)` — non-interactive container with `Card` objectName for QSS;
  `Card(elevated=True)` carries the card shadow (see Styling). `CardHeader` and `Divider`
  put a card's title inside it, over a 1px rule (Controls and Schedule Queue).
- `interactive_card.py` `InteractiveCard`, `SelectableCardGroup` — clickable selection.
  An `InteractiveCard` carries the card shadow at rest.
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
`Title`) and target it in the global stylesheet's template.

The two `.qss` files are **generated — never edit them.** Every rule lives
once in [app.qss.tmpl](Project/ui/style/app.qss.tmpl), and every colour is a
role in [tokens.py](Project/ui/style/tokens.py) (`${bg.surface}` in the
template, a light and a dark value in the table). Edit either, run
`python3 Project/ui/style/build_qss.py`, and commit all three: what you
edited and both stylesheets ([CONTRIBUTING.md §7](CONTRIBUTING.md#7-colours-and-themes)).
`test_qss_generated.py` fails on a stale stylesheet, and
`test_no_new_raw_colours.py` fails when a file under `Project/ui` gains a
raw colour (hex, `rgb()` or `hsv()`, `QColor(200, 0, 0)` or
`QColor.fromRgb(…)`, `Qt.white`, `color: white`), or loses one without
lowering its count in `BASELINE`. The Help tab's HTML takes its colours from
`tokens.HELP_HTML` and is counted the same way.

`StyleManager.apply` also sets a QPalette built from the same tokens
([qt_palette.py](Project/ui/style/qt_palette.py)), before the stylesheet, and
emits `theme_changed`. The palette colours what no rule names: the window, plain
containers (transparent over it), input text and placeholders, alternate rows,
selection, links. So:

- **Never** add a universal `QWidget { background; color }` rule.
- **Never** put a `color` on a rule that matches an input. Qt would draw the
  input's placeholder in that colour: at half alpha from Qt 5.15.12 (under
  4.5:1), and on the Pi's 5.15.8 at full strength, like typed text.
- Content the stylesheet cannot reach (HTML, a painter) listens to
  `theme_changed`, as `HelpTab` does.

The light theme follows Fluent 2 / WinUI: a near-white page (`bg.page`), white
tab panes (`bg.pane`) and cards (`bg.surface`), one stroke round each
(`border.subtle`), and a lighter rule inside a card (`border.divider`). Never a
box inside a box: a group box in a group box or a card is drawn as a section
(its title over a rule), a card's title is a `CardHeader` over a `Divider`, and
a table or list in a box has no frame of its own.

Card shadows ([elevation.py](Project/ui/style/elevation.py), CONTRIBUTING.md §7):

- **Never** `setGraphicsEffect` / `QGraphicsDropShadowEffect` outside the
  splash (`test_elevation.py` fails): it re-renders the card and its children
  on every change and turns near-black on the Pi's Qt 5.15.8 (QTBUG-102374).
- An elevated card is `Card(elevated=True)`, or a `QFrame` subclass with
  `ElevatedMixin` before `QFrame` that calls `init_elevation(level, radius,
  at_rest=True|False)` in `__init__`. `radius` must equal its rule's
  `border-radius`; `at_rest=False` shows the shadow only under the pointer
  (schedule cards).
- The card reserves room round its box for the shadow (a margin
  `build_qss.py` writes from `tokens.SHADOWS`), so it is bigger than its box by
  `elevation.ROOM`. The parent gives that room back: its side margins less
  `ROOM.left` / `ROOM.right`, and the rows beside the card inset by as much.
- `tokens.ELEVATION` alone picks the recipe for each theme; dark is `None`
  and paints nothing, but keeps the room, so a theme switch moves nothing.

`test_theme_contrast.py` checks every pair of roles drawn together, in both
themes. Add the pair when you combine two roles in a new way (every role a
`color:` declaration names needs one), and keep the status-word colours
apart (it checks them with CIEDE2000).

A state that changes a widget's look is a dynamic property the template
selects on (`QFrame#ScheduleCard[selected="true"]`), never a second
`setStyleSheet`. After `setProperty`, call `restyle(widget)` from
`ui.style.theme`: it unpolishes and polishes the widget and sends the
`QEvent.StyleChange` that `setStyleSheet` would, so a `QFrame` re-reads its
frame width when the rule changes a border's width.

A colour that code paints itself comes from the QSS too. Declare it as a
`pyqtProperty(QColor)` on a named widget and set it with `qproperty-*` in
the template, from a token; a theme switch sets it again. The Animals tab's
red cell is the pattern: `_LastRunDelegate` (a `QStyledItemDelegate`) fills
the cell with `AnimalsTab.alertFill` and writes `alertText`, which
`QWidget#AnimalsTab { qproperty-alertFill: ${danger.alert}; qproperty-alertText: ${danger.on-alert}; }`
sets for each theme. A one-off painting, such as the Schedules hub's drag
pixmap, can instead ask for the role when it paints: `theme_colour("accent.tint")`
from `ui.style.theme` is the current theme's `QColor`. Never read a colour at
import, and redraw what stays on screen on `theme_changed`. Colouring a table
cell:

- `QTableWidgetItem.setBackground()` is not painted under the app QSS, and
  `setForeground()` gives way on a selected row to `::item:selected`'s
  on-accent text.
- A word in a status colour (the Calibration table's *[OK]*, *Stale*, CV%):
  `setForeground(theme_colour(role))` as the table fills, with the role kept
  on the item (`SettingsTab.CAL_TONE_ROLE`) so that a slot on
  `style_manager().theme_changed` can set it again.
- A widget put in a cell (`setCellWidget`) sits inside the `::item`
  padding, so it fills only a band of the cell. A delegate fills it all,
  and then paints the selected state itself (the red cell keeps its fill
  and gets a frame in its text colour).
- Keep the text in the item, so the filter, the tooltip and the selection
  still work, and never let colour alone carry the meaning: the red cell
  starts with a status word (*Stopped*, *Incomplete*, *Interrupted*).

## Dialogs

See [`references/dialog-template.md`](references/dialog-template.md) for the
standard pattern. Two notes:

- Dialogs that need the database/login system **receive them in
  `__init__`** — don't reach up through `parent()`.
- For schedule editing, the canonical dialog is `ScheduleEditDialog`
  defined **inside** [schedules_hub.py:53](Project/ui/schedules_hub.py#L53),
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
