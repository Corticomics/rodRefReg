rrrinstaller@raspberrypi:~ $ ~/rodent-refreshment-regulator/start_rrr.sh
Checking for UI updates...
=== Checking for UI Updates ===
Current branch: main
Current commit: 6bcdfc3c1babf6f51d6ff90a101c4beddb5c55e9
Fetching latest updates...
remote: Enumerating objects: 14, done.
remote: Counting objects: 100% (14/14), done.
remote: Compressing objects: 100% (2/2), done.
remote: Total 8 (delta 7), reused 6 (delta 6), pack-reused 0 (from 0)
Unpacking objects: 100% (8/8), 1.85 KiB | 316.00 KiB/s, done.
From https://github.com/Corticomics/rodRefReg
 * branch            main       -> FETCH_HEAD
   2b27eeb..a119858  main       -> origin/main
Latest remote commit: a119858bbf1c806aac231b59094dd13d8dcc2b7c
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
Failed to initialize hat 0: Fail to init the card with exception [Errno 11] Resource temporarily unavailable
ERROR:root:Hat initialization error: Fail to init the card with exception [Errno 11] Resource temporarily unavailable
Database schema created/updated successfully.
Running in Guest mode. Displaying all data.
Falling back to get_all_relay_units
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
  File "/home/rrrinstaller/rodent-refreshment-regulator/Project/ui/schedules_tab.py", line 193, in __init__
    self.load_schedules()
  File "/home/rrrinstaller/rodent-refreshment-regulator/Project/ui/schedules_tab.py", line 410, in load_schedules
    self.schedule_list.clear()
    ^^^^^^^^^^^^^^^^^^
AttributeError: 'SchedulesTab' object has no attribute 'schedule_list'
wget -O setup_rrr.sh https://raw.githubusercontent.com/Corticomics/rodRefReg/main/setup_rrr.sh && chmod +x setup_rrr.sh && ./setup_rrr.sh
