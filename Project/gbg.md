mouseuser@raspberrypi:~/Documents/GitHub/rodRefReg/Project $ sudo python3 main.py
QStandardPaths: XDG_RUNTIME_DIR not set, defaulting to '/tmp/runtime-root'
Database schema created/updated successfully.
Database schema created/updated successfully.
Running in Guest mode. Displaying all data.
Initialized relay unit 1 with relays (1, 2)
Initialized relay unit 2 with relays (3, 4)
Initialized relay unit 3 with relays (5, 6)
Initialized relay unit 4 with relays (7, 8)
Initialized relay unit 5 with relays (9, 10)
Initialized relay unit 6 with relays (11, 12)
Initialized relay unit 7 with relays (13, 14)
Initialized relay unit 8 with relays (15, 16)
Initialized relay hat 0
Retrieved 2 animals from the database.
Traceback (most recent call last):
  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/main.py", line 350, in <module>
    main()
  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/main.py", line 336, in main
    setup()
  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/main.py", line 78, in setup
    gui = RodentRefreshmentGUI(
          ^^^^^^^^^^^^^^^^^^^^^
  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/ui/gui.py", line 51, in __init__
    self.init_ui()
  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/ui/gui.py", line 264, in init_ui
    self.run_stop_section,
    ^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'RodentRefreshmentGUI' object has no attribute 'run_stop_section'

