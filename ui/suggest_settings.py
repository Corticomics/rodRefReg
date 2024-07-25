from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QWidget

class SuggestSettings(QGroupBox):
    def __init__(self, suggest_settings_callback, push_settings_callback):
        super().__init__("Answer These For Setting Suggestions")
        self.suggest_settings_callback = suggest_settings_callback
        self.push_settings_callback = push_settings_callback

        layout = QVBoxLayout()

        self.entry_widgets = {}

        labels_and_entries = [
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

        for label_text, default_value in labels_and_entries:
            entry_layout = QHBoxLayout()
            label = QLabel(label_text)
            label.setStyleSheet("QLabel { font-size: 14px; padding: 5px; }")
            entry_layout.addWidget(label)

            entry = QLineEdit()
            entry.setStyleSheet("QLineEdit { font-size: 14px; padding: 5px; }")
            entry.setText(default_value)
            entry_layout.addWidget(entry)

            layout.addLayout(entry_layout)
            self.entry_widgets[label_text] = entry

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
        return {label: entry.text() for label, entry in self.entry_widgets.items()}
