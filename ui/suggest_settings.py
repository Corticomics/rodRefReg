from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QWidget
from PyQt5.QtCore import Qt

class SuggestSettings(QGroupBox):
    def __init__(self, suggest_settings_callback, push_settings_callback):
        super().__init__("Answer These For Setting Suggestions")
        self.suggest_settings_callback = suggest_settings_callback
        self.push_settings_callback = push_settings_callback

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
            entry = QLineEdit()
            entry.setStyleSheet("QLineEdit { font-size: 14px; padding: 5px; }")
            entry_layout.addWidget(entry)
            self.entry_fields[question] = entry
            layout.addLayout(entry_layout)

        suggest_settings_button = QPushButton("Suggest Settings")
        suggest_settings_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        suggest_settings_button.clicked.connect(self.suggest_settings_callback)
        layout.addWidget(suggest_settings_button)

        push_settings_button = QPushButton("Push Settings")
        push_settings_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        push_settings_button.clicked.connect(self.push_settings_callback)
        layout.addWidget(push_settings_button)

        scroll_content = QWidget()
        scroll_content.setLayout(layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_content)

        outer_layout = QVBoxLayout()
        outer_layout.addWidget(scroll_area)
        self.setLayout(outer_layout)

    def get_entry_values(self):
        values = {}
        for question, entry in self.entry_fields.items():
            values[question] = entry.text()
        return values
