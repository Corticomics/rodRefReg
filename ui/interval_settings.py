from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QLineEdit, QDateTimeEdit
from PyQt5.QtCore import QDateTime

class IntervalSettings(QGroupBox):
    def __init__(self, settings):
        super().__init__("Interval and Window Settings")
        self.settings = settings

        layout = QVBoxLayout()

        self.interval_entry = self.add_setting_input(layout, "Interval (seconds):", self.settings.get('interval', 10))
        self.stagger_entry = self.add_setting_input(layout, "Stagger (seconds):", self.settings.get('stagger', 1))
        self.window_start_entry = QDateTimeEdit(QDateTime.currentDateTime())
        self.window_start_entry.setCalendarPopup(True)
        layout.addWidget(QLabel("Water Window Start:"))
        layout.addWidget(self.window_start_entry)
        
        self.window_end_entry = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.window_end_entry.setCalendarPopup(True)
        layout.addWidget(QLabel("Water Window End:"))
        layout.addWidget(self.window_end_entry)

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
            'window_start': int(self.window_start_entry.dateTime().toSecsSinceEpoch()),
            'window_end': int(self.window_end_entry.dateTime().toSecsSinceEpoch())
        }
