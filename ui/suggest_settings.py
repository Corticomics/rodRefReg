from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QWidget
from PyQt5.QtCore import Qt

class SuggestSettings(QGroupBox):
    def __init__(self, suggest_callback, push_callback):
        super().__init__("Answer These For Setting Suggestions")
        self.suggest_callback = suggest_callback
        self.push_callback = push_callback

        layout = QVBoxLayout()

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
            entry_layout = QHBoxLayout()
            label = QLabel(question)
            label.setStyleSheet("QLabel { font-size: 14px; padding: 5px; }")
            entry_layout.addWidget(label)
            entry = QLineEdit()
            entry.setStyleSheet("QLineEdit { font-size: 14px; padding: 5px; }")
            entry.setText("0")
            entry_layout.addWidget(entry)
            layout.addLayout(entry_layout)
            self.entries[question] = entry

        self.suggest_button = QPushButton("Suggest Settings")
        self.suggest_button.clicked.connect(self.suggest_callback)
        layout.addWidget(self.suggest_button)

        self.push_button = QPushButton("Push Settings")
        self.push_button.clicked.connect(self.push_callback)
        layout.addWidget(self.push_button)

        self.setLayout(layout)

    def get_entry_values(self):
        return {question: entry.text() for question, entry in self.entries.items()}
