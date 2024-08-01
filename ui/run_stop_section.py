from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTabWidget, QWidget
from .interval_settings import IntervalSettings

class RunStopSection(QGroupBox):
    def __init__(self, run_program_callback, stop_program_callback, change_relay_hats_callback, update_all_settings_callback):
        super().__init__("Run/Stop Program")
        self.run_program_callback = run_program_callback
        self.stop_program_callback = stop_program_callback
        self.change_relay_hats_callback = change_relay_hats_callback
        self.update_all_settings_callback = update_all_settings_callback

        layout = QVBoxLayout()

        self.tab_widget = QTabWidget()
        
        self.interval_settings = IntervalSettings({})
        self.tab_widget.addTab(self.interval_settings, "Calendar Mode")
        
        self.offline_settings_widget = QWidget()
        self.offline_layout = QVBoxLayout()
        self.offline_duration_entry = self.add_setting_input(self.offline_layout, "Duration (seconds):", 0)
        self.offline_settings_widget.setLayout(self.offline_layout)
        self.tab_widget.addTab(self.offline_settings_widget, "Offline Mode")
        
        layout.addWidget(self.tab_widget)

        self.run_button = QPushButton("Run Program")
        self.run_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        self.run_button.clicked.connect(self.run_program)
        layout.addWidget(self.run_button)

        self.stop_button = QPushButton("Stop Program")
        self.stop_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        self.stop_button.clicked.connect(self.stop_program)
        layout.addWidget(self.stop_button)

        self.change_relay_hats_button = QPushButton("Change Relay Hats")
        self.change_relay_hats_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        self.change_relay_hats_button.clicked.connect(self.change_relay_hats)
        layout.addWidget(self.change_relay_hats_button)
        
        self.update_settings_button = QPushButton("Update Settings")
        self.update_settings_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        self.update_settings_button.clicked.connect(self.update_all_settings_callback)
        layout.addWidget(self.update_settings_button)

        self.setLayout(layout)

    def add_setting_input(self, layout, label_text, default_value):
        layout.addWidget(QLabel(label_text))
        entry = QLineEdit()
        entry.setText(str(default_value))
       
        entry.setText(str(default_value))
        layout.addWidget(entry)
        return entry

    def run_program(self):
        if self.tab_widget.currentIndex() == 0:  # Calendar Mode
            settings = self.interval_settings.get_settings()
            interval = settings['interval']
            stagger = settings['stagger']
            window_start = settings['window_start']
            window_end = settings['window_end']
        else:  # Offline Mode
            interval = int(self.offline_duration_entry.text())
            stagger = 0
            window_start = time.time()
            window_end = window_start + interval

        self.run_program_callback(interval, stagger, window_start, window_end)

    def stop_program(self):
        self.stop_program_callback()

    def change_relay_hats(self):
        self.change_relay_hats_callback()
