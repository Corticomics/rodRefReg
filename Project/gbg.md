conelab@raspberrypi:~/Documents/GitHub/new_rrr/RRR/Project $ sudo python3 main.py
QStandardPaths: XDG_RUNTIME_DIR not set, defaulting to '/tmp/runtime-root'
Tables created or confirmed to exist.
Tables created or confirmed to exist.
Running in Guest mode. Displaying all data.
Initialized relay hat 0
Traceback (most recent call last):
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/main.py", line 200, in <module>
    main()
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/main.py", line 186, in main
    setup()
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/main.py", line 55, in setup
    gui = RodentRefreshmentGUI(run_program, stop_program, change_relay_hats, settings, database_handler=database_handler, login_system=login_system)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/ui/gui.py", line 32, in __init__
    self.init_ui(style)
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/ui/gui.py", line 78, in init_ui
    self.user_icon.login_signal.connect(self.on_login)
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'UserIcon' object has no attribute 'login_signal'
