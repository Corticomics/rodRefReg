from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QWidget
import math
class SuggestSettings(QGroupBox):
    def __init__(self, update_all_settings_callback, print_to_terminal_callback, run_program_callback):
        super().__init__("Answer These For Setting Suggestions")
        self.update_all_settings_callback = update_all_settings_callback
        self.print_to_terminal_callback = print_to_terminal_callback
        self.run_program_callback = run_program_callback

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
            question_label = QLabel(question)
            question_label.setStyleSheet("QLabel { font-size: 14px; padding: 5px; }")
            layout.addWidget(question_label)
            entry = QLineEdit()
            entry.setStyleSheet("QLineEdit { font-size: 14px; padding: 5px; }")
            layout.addWidget(entry)
            self.entries[question] = entry

        suggest_settings_button = QPushButton("Suggest Settings")
        suggest_settings_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        suggest_settings_button.clicked.connect(self.suggest_settings)
        layout.addWidget(suggest_settings_button)

        push_settings_button = QPushButton("Push Settings")
        push_settings_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        push_settings_button.clicked.connect(self.update_all_settings_callback)
        layout.addWidget(push_settings_button)

        scroll_content = QWidget()
        scroll_content.setLayout(layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_content)

        outer_layout = QVBoxLayout()
        outer_layout.addWidget(scroll_area)
        self.setLayout(outer_layout)

    def suggest_settings(self):
        values = self.get_entry_values()
        if values is None:
            return

        try:
            frequency = int(values["How often should each cage receive water? (Seconds):"])
            window_start = int(values["Water window start (hour, 24-hour format):"])
            window_end = int(values["Water window end (hour, 24-hour format):"])

            suggestion_text = (
                f"Suggested Settings:\n"
                f"- Interval: {frequency} seconds\n"
                f"- Stagger: {'1'} seconds (Assumed)\n"
                f"- Water Window: {window_start}:00 to {window_end}:00\n"
            )

            for question, entry in self.entries.items():
                if "Water volume for relays" in question:
                    volume_per_relay = int(entry.text())
                    triggers = self.calculate_triggers(volume_per_relay)
                    suggestion_text += f"- {question} should trigger {triggers} times to dispense {volume_per_relay} micro-liters each.\n"

            self.print_to_terminal_callback(suggestion_text)
        except ValueError as e:
            self.print_to_terminal_callback("Please enter valid numbers for all settings.")

    def get_entry_values(self):
        values = {}
        for question, entry in self.entries.items():
            values[question] = entry.text()
        return values

    def calculate_triggers(self, volume_needed):
        return math.ceil(volume_needed / 10)
