from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QLineEdit

class IntervalSettings(QGroupBox):
    def __init__(self, settings):
        super().__init__("Interval and Window Settings")
        self.settings = settings

        layout = QVBoxLayout()

        self.interval_entry = self.add_setting_input(layout, "Interval (seconds):", self.settings['interval'])
        self.stagger_entry = self.add_setting_input(layout, "Stagger (seconds):", self.settings['stagger'])
        self.window_start_entry = self.add_setting_input(layout, "Water Window Start (24-hour format):", self.settings['window_start'])
        self.window_end_entry = self.add_setting_input(layout, "Water Window End (24-hour format):", self.settings['window_end'])

        self.setLayout(layout)

    def add_setting_input(self, layout, label_text, default_value):
        layout.addWidget(QLabel(label_text))
        entry = QLineEdit()
        entry.setText(str(default_value))
        layout.addWidget(entry)
        return entry

    def get_settings(self):
        return {
            'interval': int(self.interval_entry.text()),
            'stagger': int(self.stagger_entry.text()),
            'window_start': int(self.window_start_entry.text()),
            'window_end': int(self.window_end_entry.text()),
        }
