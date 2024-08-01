from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTabWidget, QWidget, QDateTimeEdit
from PyQt5.QtCore import Qt, QDateTime

class RunStopSection(QGroupBox):
    def __init__(self, run_program_callback, stop_program_callback, change_relay_hats_callback, update_all_settings_callback):
        super().__init__("Run/Stop Program")
        self.run_program_callback = run_program_callback
        self.stop_program_callback = stop_program_callback
        self.change_relay_hats_callback = change_relay_hats_callback
        self.update_all_settings_callback = update_all_settings_callback

        layout = QVBoxLayout()

        # Interval and stagger input fields
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Interval (seconds):"))
        self.interval_entry = QLineEdit()
        interval_layout.addWidget(self.interval_entry)
        layout.addLayout(interval_layout)

        stagger_layout = QHBoxLayout()
        stagger_layout.addWidget(QLabel("Stagger (seconds):"))
        self.stagger_entry = QLineEdit()
        stagger_layout.addWidget(self.stagger_entry)
        layout.addLayout(stagger_layout)

        # Tabs for Calendar and Offline options
        self.tab_widget = QTabWidget()
        
        # Calendar tab
        calendar_tab = QWidget()
        calendar_layout = QVBoxLayout()
        self.window_start_entry = QDateTimeEdit(QDateTime.currentDateTime())
        self.window_start_entry.setCalendarPopup(True)
        self.window_end_entry = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.window_end_entry.setCalendarPopup(True)
        calendar_layout.addWidget(QLabel("Water Window Start:"))
        calendar_layout.addWidget(self.window_start_entry)
        calendar_layout.addWidget(QLabel("Water Window End:"))
        calendar_layout.addWidget(self.window_end_entry)
        calendar_tab.setLayout(calendar_layout)
        self.tab_widget.addTab(calendar_tab, "Calendar")

        # Offline tab
        offline_tab = QWidget()
        offline_layout = QVBoxLayout()
        self.offline_duration_entry = QLineEdit()
        offline_layout.addWidget(QLabel("Duration (seconds):"))
        offline_layout.addWidget(self.offline_duration_entry)
        offline_tab.setLayout(offline_layout)
        self.tab_widget.addTab(offline_tab, "Offline")
        
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

    def run_program(self):
        interval = int(self.interval_entry.text())
        stagger = int(self.stagger_entry.text())
        if self.tab_widget.currentIndex() == 0:  # Calendar tab
            window_start = int(self.window_start_entry.dateTime().toSecsSinceEpoch())
            window_end = int(self.window_end_entry.dateTime().toSecsSinceEpoch())
        else:  # Offline tab
            window_start = int(time.time())
            window_end = window_start + int(self.offline_duration_entry.text())
        self.run_program_callback(interval, stagger, window_start, window_end)

    def stop_program(self):
        self.stop_program_callback()

    def change_relay_hats(self):
        self.change_relay_hats_callback()
