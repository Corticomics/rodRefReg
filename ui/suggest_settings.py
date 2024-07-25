from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFormLayout
from PyQt5.QtCore import Qt

class SuggestSettings(QGroupBox):
    def __init__(self, suggest_settings_callback, push_settings_callback, run_program_callback, stop_program_callback):
        super().__init__("Answer These For Setting Suggestions")
        self.suggest_settings_callback = suggest_settings_callback
        self.push_settings_callback = push_settings_callback
        self.run_program_callback = run_program_callback
        self.stop_program_callback = stop_program_callback

        layout = QFormLayout()

        self.entries = {}
        questions = [
            "Water volume for relays 1 & 2 (uL):",
            "Water volume for relays 3 & 4 (uL):",
            "Water volume for relays 5 & 6 (uL):",
            "Water volume for relays 7 & 8 (uL):",
            "Water volume for relays 9 & 10 (uL):",
            "Water volume for relays 11 & 12 (uL):",
            "Water volume for relays 13 & 14 (uL):",
            "Water volume for relays 15 & 16 (uL):",
            "How often should each cage receive water? (Seconds):",
            "Water window start (hour, 24-hour format):",
            "Water window end (hour, 24-hour format):"
        ]

        for question in questions:
            label = QLabel(question)
            entry = QLineEdit()
            layout.addRow(label, entry)
            self.entries[question] = entry

        self.suggest_button = QPushButton("Suggest Settings")
        self.suggest_button.clicked.connect(self.suggest_settings_callback)
        layout.addRow(self.suggest_button)

        self.push_button = QPushButton("Push Settings")
        self.push_button.clicked.connect(self.push_settings_callback)
        layout.addRow(self.push_button)

        self.run_button = QPushButton("Run Program")
        self.run_button.clicked.connect(self.run_program_callback)
        layout.addRow(self.run_button)

        self.stop_button = QPushButton("Stop Program")
        self.stop_button.clicked.connect(self.stop_program_callback)
        layout.addRow(self.stop_button)

        self.setLayout(layout)

    def get_entry_values(self):
        values = {}
        for question, entry in self.entries.items():
            values[question] = entry.text()
        return values
