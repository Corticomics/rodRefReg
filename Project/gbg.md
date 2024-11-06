conelab@raspberrypi:~/Documents/GitHub/new_rrr/RRR/Project $ sudo python3 main.py
QStandardPaths: XDG_RUNTIME_DIR not set, defaulting to '/tmp/runtime-root'
Initialized relay hat 0
Traceback (most recent call last):
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/main.py", line 192, in <module>
    main()
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/main.py", line 178, in main
    setup()
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/main.py", line 47, in setup
    gui = RodentRefreshmentGUI(run_program, stop_program, change_relay_hats, settings)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/ui/gui.py", line 29, in __init__
    self.init_ui(style)
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/ui/gui.py", line 97, in init_ui
    self.projects_section = ProjectsSection(self.settings, self.print_to_terminal)
                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/ui/projects_section.py", line 18, in __init__
    self.schedules_tab = SchedulesTab(settings, print_to_terminal)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/ui/schedules_tab.py", line 14, in __init__
    self.setup_ui()
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/ui/schedules_tab.py", line 23, in setup_ui
    self.load_schedules()
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/ui/schedules_tab.py", line 37, in load_schedules
    schedules = self.database_handler.get_all_schedules()
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'function' object has no attribute 'get_all_schedules'
