conelab@raspberrypi:~/Documents/GitHub/new_rrr/RRR/app $ sudo python3 main.py
QStandardPaths: XDG_RUNTIME_DIR not set, defaulting to '/tmp/runtime-root'
error: XDG_RUNTIME_DIR is invalid or not set in the environment.
qt.xkb.compose: failed to create compose table
Initialized relay hat 0
Traceback (most recent call last):
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/app/main.py", line 208, in <module>
    main()
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/app/main.py", line 195, in main
    setup()
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/app/main.py", line 51, in setup
    gui = RodentRefreshmentGUI(run_program, stop_program, change_relay_hats, settings)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/app/ui/gui.py", line 40, in __init__
    self.init_ui(style)
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/app/ui/gui.py", line 138, in init_ui
    self.suggest_settings_section = SuggestSettingsSection(
                                    ^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/app/ui/suggest_settings.py", line 34, in __init__
    self.suggest_tab = SuggestSettingsTab(suggest_settings_callback, push_settings_callback, self.db_manager)
                                                                                             ^^^^^^^^^^^^^^^
AttributeError: 'SuggestSettingsSection' object has no attribute 'db_manager'