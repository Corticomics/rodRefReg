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
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/ui/gui.py", line 33, in __init__
    self.init_ui(style)
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/ui/gui.py", line 106, in init_ui
    self.projects_section = ProjectsSection(self.settings, self.print_to_terminal)
                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/ui/projects_section.py", line 22, in __init__
    self.animals_tab = AnimalsTab(settings, print_to_terminal)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/ui/animals_tab.py", line 113, in __init__
    self.load_animals()
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/ui/animals_tab.py", line 232, in load_animals
    item = QListWidget.QListWidgetItem(display_text)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: type object 'QListWidget' has no attribute 'QListWidgetItem'