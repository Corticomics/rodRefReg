from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QWidget

class SuggestSettings(QGroupBox):
    def __init__(self, suggest_settings_callback, push_settings_callback, run_program_callback, stop_program_callback):
        super().__init__("Answer These For Setting Suggestions")
        self.suggest_settings_callback = suggest_settings_callback
        self.push_settings_callback = push_settings_callback
        self.run_program_callback = run_program_callback
        self.stop_program_callback = stop_program_callback

        layout = QVBoxLayout()

        self.entry_fields = {}

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
            entry_layout = QHBoxLayout()
            entry_layout.addWidget(QLabel(question))
            entry_field = QLineEdit()
            entry_field.setStyleSheet("QLineEdit { font-size: 14px; padding: 5px; }")
            entry_layout.addWidget(entry_field)
            self.entry_fields[question] = entry_field
            layout.addLayout(entry_layout)

        suggest_button = QPushButton("Suggest Settings")
        suggest_button.clicked.connect(self.suggest_settings_callback)
        layout.addWidget(suggest_button)

        push_button = QPushButton("Push Settings")
        push_button.clicked.connect(self.push_settings_callback)
        layout.addWidget(push_button)

        self.setLayout(layout)

    def get_entry_values(self):
        return {question: field.text() for question, field in self.entry_fields.items()}
