conelab@raspberrypi:~/Documents/GitHub/new_rrr/RRR/Project $ sudo python3 main.py
QStandardPaths: XDG_RUNTIME_DIR not set, defaulting to '/tmp/runtime-root'
Tables created or confirmed to exist.
Tables created or confirmed to exist.
Initialized relay hat 0
Retrieved 0 animals from the database.
Traceback (most recent call last):
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/main.py", line 194, in <module>
    main()
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/main.py", line 180, in main
    setup()
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/main.py", line 49, in setup
    gui = RodentRefreshmentGUI(run_program, stop_program, change_relay_hats, settings, database_handler=database_handler)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/ui/gui.py", line 29, in __init__
    self.init_ui(style)
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/ui/gui.py", line 99, in init_ui
    self.projects_section = ProjectsSection(self.settings, self.print_to_terminal, self.database_handler)
                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/ui/projects_section.py", line 24, in __init__
    self.animals_tab = AnimalsTab(settings, print_to_terminal, database_handler)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/ui/animals_tab.py", line 105, in __init__
    edit_animal_button.clicked.connect(self.edit_animal)
                                       ^^^^^^^^^^^^^^^^
AttributeError: 'AnimalsTab' object has no attribute 'edit_animal'. Did you mean: 'add_animal'?
