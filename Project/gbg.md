conelab@raspberrypi:~/Documents/GitHub/new_rrr/RRR/Project $ sudo python3 main.py
QStandardPaths: XDG_RUNTIME_DIR not set, defaulting to '/tmp/runtime-root'
Tables created or confirmed to exist.
Tables created or confirmed to exist.
Running in Guest mode. Displaying all data.
Initialized relay hat 0
Traceback (most recent call last):
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/main.py", line 208, in <module>
    main()
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/main.py", line 194, in main
    setup()
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/main.py", line 63, in setup
    gui = RodentRefreshmentGUI(run_program, stop_program, change_relay_hats, settings, database_handler=database_handler, login_system=login_system)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/ui/gui.py", line 37, in __init__
    self.init_ui(style)
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/ui/gui.py", line 75, in init_ui
    self.projects_section = ProjectsSection(self.settings, self.print_to_terminal, self.database_handler)
                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/ui/projects_section.py", line 24, in __init__
    self.schedules_tab = SchedulesTab(settings, print_to_terminal, database_handler, trainer_id=self.trainer_id)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: SchedulesTab.__init__() got an unexpected keyword argument 'trainer_id'
