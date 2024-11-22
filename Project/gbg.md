RRR_Automated_Watering_System/
├── controllers/
│   └── projects_controller.py    # Manages business logic for projects.
├── gpio/
│   └── relay_handler.py          # Handles GPIO relay operations.
├── models/
│   ├── animal.py                 # Defines the Animal data model.
│   ├── database_handler.py       # Handles database interactions.
│   ├── login_system.py           # Manages user authentication and sessions.
│   ├── relay_unit.py             # Defines the RelayUnit data model.
│   └── schedule.py               # Defines the Schedule data model.
├── notification/
│   └── notification_handler.py   # Handles sending notifications.
├── ui/
│   ├── advanced_settings_section.py  # UI for advanced relay trigger settings.
│   ├── animals_tab.py                # UI tab for managing animals.
│   ├── create_schedule_dialog.py     # Dialog for creating new schedules.
│   ├── drag_drop_container.py        # Custom drag-and-drop container widget.
│   ├── edit_animal_dialog.py         # Dialog for editing animal information.
│   ├── gui.py                        # Main GUI class for the application.
│   ├── interval_settings.py          # UI for interval and window settings.
│   ├── login_dialog.py               # Dialog for user login.
│   ├── profile_dialog.py             # Dialog for displaying user profiles.
│   ├── projects_section.py           # UI section for projects, including tabs.
│   ├── relay_container.py            # UI widget for relay containers with drag-and-drop.
│   ├── run_stop_section.py           # UI section for running and stopping the program.
│   ├── schedule_creation_widget.py   # Widget for schedule creation.
│   ├── schedules_tab.py              # UI tab for managing schedules.
│   ├── slack_credentials_tab.py      # UI for entering Slack credentials.
│   ├── suggest_settings_section.py   # UI section for suggesting settings.
│   ├── SuggestSettingsTab.py       # UI tab for suggesting settings.
│   ├── terminal_output.py            # UI component for displaying system messages.
│   ├── UserTab.py                   # UI tab for user login and profile management.
│   └── welcome_section.py            # UI section for welcome messages and instructions.
├── utils/
│   ├── settings.py                   # Functions for loading and saving settings.
│   └── relay_utils.py                # Utility functions related to relays.
├── workers/
│   └── relay_worker.py               # Asynchronous worker for relay operations.
├── main.py                           # Main application entry point integrating all components.
├── requirements.txt                  # Project dependencies.
└── README.md                         # Project documentation.\


