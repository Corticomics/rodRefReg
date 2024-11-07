from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QPushButton, QDialog
from .schedules_tab import SchedulesTab
from .animals_tab import AnimalsTab

class ProjectsSection(QWidget):
    def __init__(self, settings, print_to_terminal, database_handler):
        super().__init__()

        self.settings = settings
        self.print_to_terminal = print_to_terminal
        self.database_handler = database_handler

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Create a tab widget for schedules and animals
        self.tab_widget = QTabWidget()

        # Schedules tab
        self.schedules_tab = SchedulesTab(settings, print_to_terminal, database_handler)
        self.tab_widget.addTab(self.schedules_tab, "Schedules")

        # Animals tab
        self.animals_tab = AnimalsTab(settings, print_to_terminal, database_handler)
        self.tab_widget.addTab(self.animals_tab, "Animals")

        self.layout.addWidget(self.tab_widget)

        # Add a create schedule button that opens the create schedule dialog in SchedulesTab
        self.create_schedule_button = QPushButton("Create Schedule")
        self.create_schedule_button.clicked.connect(self.open_create_schedule)
        self.layout.addWidget(self.create_schedule_button)

    def open_create_schedule(self):
        # Open the Create Schedule dialog from SchedulesTab
        dialog = QDialog(self)
        dialog.setWindowTitle("Create Schedule")
        layout = QVBoxLayout(dialog)

        layout.addWidget(self.schedules_tab)
        dialog.setLayout(layout)
        dialog.exec_()