# Adding a new tab

Three flavors, depending on where the new screen belongs.

## A. New sub-tab under SettingsTab

Settings sub-tabs are the cheapest UI to add — they reuse the existing
`SettingsTab.tab_widget` and the auto-save plumbing.

1. Add a `_create_<name>_tab(self) -> QWidget` method to `SettingsTab`.
2. Wire it in `SettingsTab.init_ui` next to the existing sub-tabs:
   ```python
   self.my_tab = self._create_my_tab()
   self.tab_widget.addTab(self.my_tab, "My Tab")
   ```
3. If the tab has widgets the user can edit, connect them to
   `_auto_save_settings` in `_connect_auto_save_handlers()`. The auto-save
   reads every widget at once, so you only add the connection, not the
   read logic.
4. Add new keys to the `updated_settings` dict in `_auto_save_settings`
   if you introduce new persistable values; they must be listed in
   `SystemController` as managed keys (see schedule-database-ops skill).

## B. New sub-tab under ProjectsSection

For a new project-wide screen alongside Schedules/Animals/Wizard/Cages.

1. Build a `QWidget` subclass in `Project/ui/<name>_tab.py` that takes
   `(settings, print_to_terminal, database_handler, login_system,
   system_controller=None)` in `__init__` — same shape as siblings.
2. Add it in `ProjectsSection.__init__`:
   ```python
   self.my_tab = MyTab(settings, self.print_to_terminal, database_handler, login_system)
   self.my_tab_index = self.tab_widget.addTab(self.my_tab, "My Tab")
   ```
3. Connect any cross-tab signals at the bottom of `ProjectsSection.__init__`
   (e.g. wizard's `schedule_created` → schedules hub's `refresh`).
4. **Do not** add a top-level tab on `RodentRefreshmentGUI` for a project
   concept — that breaks the Schedules/Animals/Wizard/Cages mental model.

## C. New top-level tab on RodentRefreshmentGUI

Reserved for cross-cutting concerns (Settings, Help, User). Adding one is
a deliberate UX decision; loop in the user before doing it. Pattern:

1. Build the widget the same way as a project sub-tab but with the
   collaborators the top-level tab needs (often `system_controller`).
2. Add in `RodentRefreshmentGUI.init_ui` next to the existing
   `self.settings_tab` / `self.user_tab` / `self.help_tab` block.
3. If the tab depends on login state, wrap it in `LoginGateWidget`.

## Smoke test

`Project/tests/unit/test_gui_smoke.py` parametrizes over every
`Project/ui/*.py`. A new tab module is picked up automatically and
verified to import cleanly + appear in `ui.__init__.__all__` if exported.
Run locally: `pytest Project/tests/unit/test_gui_smoke.py -v`.
