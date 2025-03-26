rrrinstaller@raspberrypi:~ $ ~/rodent-refreshment-regulator/start_rrr.sh
Checking for UI updates...
=== Checking for UI Updates ===
Current branch: main
Current commit: 6bcdfc3c1babf6f51d6ff90a101c4beddb5c55e9
Fetching latest updates...
From https://github.com/Corticomics/rodRefReg
 * branch            main       -> FETCH_HEAD
Latest remote commit: f54acc8c1a6d5c1cdda07225b634d50b2f9a8e0f
Updates available. Backing up important files...
Backing up database...
Backing up settings...
Saved working directory and index state WIP on main: 6bcdfc3 Merge pull request #22 from Corticomics/version-beta-0.01
Applying UI updates...
UI files updated successfully!
Restoring database...
Restoring settings...
Creating update notification...
Update notification created. User will be informed on next launch.
UI update check complete.
Database schema created/updated successfully.
Initialized relay unit 1 with relays (1, 2)
Initialized relay unit 2 with relays (3, 4)
Initialized relay unit 3 with relays (5, 6)
Initialized relay unit 4 with relays (7, 8)
Initialized relay unit 5 with relays (9, 10)
Initialized relay unit 6 with relays (11, 12)
Initialized relay unit 7 with relays (13, 14)
Initialized relay unit 8 with relays (15, 16)
Failed to initialize hat 0: [Errno 2] No such file or directory: '/dev/i2c-1'
ERROR:root:Hat initialization error: [Errno 2] No such file or directory: '/dev/i2c-1'
Database schema created/updated successfully.
Running in Guest mode. Displaying all data.
Traceback (most recent call last):
  File "/home/rrrinstaller/rodent-refreshment-regulator/Project/main.py", line 320, in <module>
    main()
  File "/home/rrrinstaller/rodent-refreshment-regulator/Project/main.py", line 303, in main
    setup()
  File "/home/rrrinstaller/rodent-refreshment-regulator/Project/main.py", line 70, in setup
    gui = RodentRefreshmentGUI(
          ^^^^^^^^^^^^^^^^^^^^^
  File "/home/rrrinstaller/rodent-refreshment-regulator/Project/ui/gui.py", line 51, in __init__
    self.init_ui()
  File "/home/rrrinstaller/rodent-refreshment-regulator/Project/ui/gui.py", line 240, in init_ui
    self.projects_section = ProjectsSection(
                            ^^^^^^^^^^^^^^^^
  File "/home/rrrinstaller/rodent-refreshment-regulator/Project/ui/projects_section.py", line 23, in __init__
    self.schedules_tab = SchedulesTab(
                         ^^^^^^^^^^^^^
  File "/home/rrrinstaller/rodent-refreshment-regulator/Project/ui/schedules_tab.py", line 34, in __init__
    self.available_animals_list = AvailableAnimalsList(self.database_handler)
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/rrrinstaller/rodent-refreshment-regulator/Project/ui/available_animals_list.py", line 9, in __init__
    super().__init__(parent)
TypeError: QListWidget(parent: typing.Optional[QWidget] = None): argument 1 has unexpected type 'DatabaseHandler'
