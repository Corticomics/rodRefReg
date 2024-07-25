from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget, QScrollArea

class SuggestSettings(QGroupBox):
    def __init__(self, suggest_settings_callback, push_settings_callback):
        super().__init__("Answer These For Setting Suggestions")
        self.suggest_settings_callback = suggest_settings_callback
        self.push_settings_callback = push_settings_callback

        layout = QVBoxLayout()

        self.entries = {}
        self.add_suggestion_input(layout, "Water volume for relays 1 & 2 (uL):", "0")
        self.add_suggestion_input(layout, "Water volume for relays 3 & 4 (uL):", "0")
        self.add_suggestion_input(layout, "Water volume for relays 5 & 6 (uL):", "0")
        self.add_suggestion_input(layout, "Water volume for relays 7 & 8 (uL):", "0")
        self.add_suggestion_input(layout, "Water volume for relays 9 & 10 (uL):", "0")
        self.add_suggestion_input(layout, "Water volume for relays 11 & 12 (uL):", "0")
        self.add_suggestion_input(layout, "Water volume for relays 13 & 14 (uL):", "0")
        self.add_suggestion_input(layout, "Water volume for relays 15 & 16 (uL):", "0")
        self.add_suggestion_input(layout, "How often should each cage receive water? (Seconds):", "0")
        self.add_suggestion_input(layout, "Water window start (hour, 24-hour format):", "0")
        self.add_suggestion_input(layout, "Water window end (hour, 24-hour format):", "0")

        suggest_settings_button = QPushButton("Suggest Settings")
        suggest_settings_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        suggest_settings_button.clicked.connect(self.suggest_settings_callback)
        layout.addWidget(suggest_settings_button)

        push_settings_button = QPushButton("Push Settings")
        push_settings_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        push_settings_button.clicked.connect(self.push_settings_callback)
        layout.addWidget(push_settings_button)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.addLayout(layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_content)

        outer_layout = QVBoxLayout()
        outer_layout.addWidget(self.scroll_area)
        self.setLayout(outer_layout)

    def add_suggestion_input(self, layout, label_text, default_value):
        h_layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setStyleSheet("QLabel { font-size: 14px; padding: 5px; }")
        h_layout.addWidget(label)
        entry = QLineEdit()
        entry.setStyleSheet("QLineEdit { font-size: 14px; padding: 5px; }")
        entry.setText(default_value)
        h_layout.addWidget(entry)
        self.entries[label_text] = entry
        layout.addLayout(h_layout)

    def get_entry_values(self):
        return {label_text: entry.text() for label_text, entry in self.entries.items()}
