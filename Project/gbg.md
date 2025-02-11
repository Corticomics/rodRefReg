Traceback (most recent call last):
  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/main.py", line 308, in <module>
    main()
  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/main.py", line 299, in main
    setup()
  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/main.py", line 81, in setup
    gui.settings_tab = SettingsTab(
                       ^^^^^^^^^^^^
  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/ui/SettingsTab.py", line 24, in __init__
    self.settings = system_controller.settings
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'dict' object has no attribute 'settings'
