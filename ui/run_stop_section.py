from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTabWidget, QWidget, QFormLayout, QDateTimeEdit
from PyQt5.QtCore import QDateTime
import time

class RunStopSection(QGroupBox):
    def __init__(self, run_program_callback, stop_program_callback, change_relay_hats_callback):
        super().__init__("Run/Stop Program")
        self.run_program_callback = run_program_callback
        self.stop_program_callback = stop_program_callback
        self.change_relay_hats_callback = change_relay_hats_callback

        layout = QVBoxLayout()

        # Interval, stagger input fields centralized
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

        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_calendar_tab(), "Calendar Mode")
        self.tab_widget.addTab(self.create_offline_tab(), "Offline Mode")
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

        self.setLayout(layout)

    def create_calendar_tab(self):
        calendar_tab = QWidget()
        form_layout = QFormLayout()

        self.window_start_entry = QDateTimeEdit(QDateTime.currentDateTime())
        self.window_start_entry.setCalendarPopup(True)
        form_layout.addRow(QLabel("Water Window Start:"), self.window_start_entry)
        
        self.window_end_entry = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.window_end_entry.setCalendarPopup(True)
        form_layout.addRow(QLabel("Water Window End:"), self.window_end_entry)

        calendar_tab.setLayout(form_layout)
        return calendar_tab

    def create_offline_tab(self):
        offline_tab = QWidget()
        form_layout = QFormLayout()

        self.offline_duration_entry = QLineEdit()
        form_layout.addRow(QLabel("Duration (seconds):"), self.offline_duration_entry
        offline_tab.setLayout(form_layout)
        return offline_tab

    def run_program(self):
        try:
            interval = int(self.interval_entry.text())
            stagger = int(self.stagger_entry.text())
            
            if self.tab_widget.currentIndex() == 0:  # Calendar Mode
                window_start = int(self.window_start_entry.dateTime().toSecsSinceEpoch())
                window_end = int(self.window_end_entry.dateTime().toSecsSinceEpoch())
            else:  # Offline Mode
                duration = int(self.offline_duration_entry.text())
                window_start = int(time.time())
                window_end = window_start + duration

            self.run_program_callback(interval, stagger, window_start, window_end)
        except Exception as e:
            print(f"Error running program: {e}")

    def stop_program(self):
        self.stop_program_callback()

    def change_relay_hats(self):
        self.change_relay_hats_callback()
