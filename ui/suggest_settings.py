# ui/suggest_settings.py
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QLineEdit, QPushButton

class SuggestSettings(QGroupBox):
    def __init__(self, suggest_settings_callback, push_settings_callback):
        super().__init__("Answer These For Setting Suggestions")

        self.suggest_settings_callback = suggest_settings_callback
        self.push_settings_callback = push_settings_callback

        layout = QVBoxLayout()

        self.entry_fields = {}
        self.entry_labels = [
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

        for label in self.entry_labels:
            label_widget = QLabel(label)
            label_widget.setWordWrap(True)
            layout.addWidget(label_widget)
            entry_widget = QLineEdit()
            layout.addWidget(entry_widget)
            self.entry_fields[label] = entry_widget

        suggest_button = QPushButton("Suggest Settings")
        suggest_button.clicked.connect(self.suggest_settings_callback)
        layout.addWidget(suggest_button)

        push_button = QPushButton("Push Settings")
        push_button.clicked.connect(self.push_settings_callback)
        layout.addWidget(push_button)

        self.setLayout(layout)

    def get_entry_values(self):
        values = {}
        for label, widget in self.entry_fields.items():
            values[label] = widget.text()
        return values