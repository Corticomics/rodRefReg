from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton

class SuggestSettings(QGroupBox):
    def __init__(self, suggest_settings_callback, push_settings_callback):
        super().__init__("Answer These For Setting Suggestions")
        self.suggest_settings_callback = suggest_settings_callback
        self.push_settings_callback = push_settings_callback

        layout = QVBoxLayout()

        self.entries = {}

        questions = [
            ("Water volume for relays 1 & 2 (uL):", "0"),
            ("Water volume for relays 3 & 4 (uL):", "0"),
            ("Water volume for relays 5 & 6 (uL):", "0"),
            ("Water volume for relays 7 & 8 (uL):", "0"),
            ("Water volume for relays 9 & 10 (uL):", "0"),
            ("Water volume for relays 11 & 12 (uL):", "0"),
            ("Water volume for relays 13 & 14 (uL):", "0"),
            ("Water volume for relays 15 & 16 (uL):", "0"),
            ("How often should each cage receive water? (Seconds):", "0"),
            ("Water window start (hour, 24-hour format):", "0"),
            ("Water window end (hour, 24-hour format):", "0")
        ]

        for question, default_value in questions:
            entry_layout = QHBoxLayout()
            entry_layout.addWidget(QLabel(question))
            entry = QLineEdit()
            entry.setText(default_value)
            entry_layout.addWidget(entry)
            self.entries[question] = entry
            layout.addLayout(entry_layout)

        suggest_button = QPushButton("Suggest Settings")
        suggest_button.clicked.connect(self.suggest_settings_callback)
        layout.addWidget(suggest_button)

        push_button = QPushButton("Push Settings")
        push_button.clicked.connect(self.push_settings_callback)
        layout.addWidget(push_button)

        self.setLayout(layout)

    def get_entry_values(self):
        values = {}
        for question, entry in self.entries.items():
            values[question] = entry.text()
        return values

    def update_relay_checkboxes(self, relay_pairs):
        pass
