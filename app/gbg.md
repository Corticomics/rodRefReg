conelab@raspberrypi:~/Documents/GitHub/new_rrr/RRR/app $ sudo python3 main.py
QStandardPaths: XDG_RUNTIME_DIR not set, defaulting to '/tmp/runtime-root'
error: XDG_RUNTIME_DIR is invalid or not set in the environment.
qt.xkb.compose: failed to create compose table
Initialized relay hat 0
Traceback (most recent call last):
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/app/main.py", line 224, in <module>
    main()
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/app/main.py", line 202, in main
    setup()
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/app/main.py", line 60, in setup
    gui = RodentRefreshmentGUI(run_program, stop_program, change_relay_hats, settings, db_manager)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/app/ui/gui.py", line 28, in __init__
    self.init_ui(style)
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/app/ui/gui.py", line 85, in init_ui
    self.projects_section = ProjectsSection(
                            ^^^^^^^^^^^^^^^^
TypeError: ProjectsSection.__init__() takes 3 positional arguments but 6 were given
