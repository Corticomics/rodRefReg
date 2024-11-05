conelab@raspberrypi:~/Documents/GitHub/new_rrr/RRR/app $ sudo python3 main.py
QStandardPaths: XDG_RUNTIME_DIR not set, defaulting to '/tmp/runtime-root'
error: XDG_RUNTIME_DIR is invalid or not set in the environment.
qt.xkb.compose: failed to create compose table
Initialized relay hat 0
Failed to initialize hat 1: Fail to init the card with exception [Errno 5] Input/output error
Failed to initialize hat 2: Fail to init the card with exception [Errno 5] Input/output error
Traceback (most recent call last):
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/app/main.py", line 224, in <module>
    main()
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/app/main.py", line 202, in main
    setup()
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/app/main.py", line 60, in setup
    gui = RodentRefreshmentGUI(run_program, stop_program, change_relay_hats, settings, db_manager)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/app/ui/gui.py", line 62, in __init__
    self.init_ui(style)
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/app/ui/gui.py", line 144, in init_ui
    self.suggest_settings_section = SuggestSettingsSection(
                                    ^^^^^^^^^^^^^^^^^^^^^^^
TypeError: SuggestSettingsSection.__init__() missing 2 required positional arguments: 'advanced_settings' and 'run_stop_section'
