from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCalendarWidget, QDateTimeEdit, QTabWidget, QWidget

class RunStopSection(QGroupBox):
    def __init__(self, run_program_callback, stop_program_callback, change_relay_hats_callback):
        super().__init__("Run/Stop Program")
        self.run_program_callback = run_program_callback
        self.stop_program_callback = stop_program_callback
        self.change_relay_hats_callback = change_relay_hats_callback

        layout = QVBoxLayout()

        self.tab_widget = QTabWidget()
        self.online_tab = QWidget()
        self.offline_tab = QWidget()

        self.tab_widget.addTab(self.online_tab, "Online")
        self.tab_widget.addTab(self.offline_tab, "Offline")

        self.init_online_tab()
        self.init_offline_tab()

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
        self.update_settings_button.clicked.connect(self.update_settings)
        layout.addWidget(self.update_settings_button)

        self.setLayout(layout)

    def init_online_tab(self):
        layout = QVBoxLayout()

        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Interval (seconds):"))
        self.interval_entry_online = QLineEdit()
        interval_layout.addWidget(self.interval_entry_online)
        layout.addLayout(interval_layout)

        stagger_layout = QHBoxLayout()
        stagger_layout.addWidget(QLabel("Stagger (seconds):"))
        self.stagger_entry_online = QLineEdit()
        stagger_layout.addWidget(self.stagger_entry_online)
        layout.addLayout(stagger_layout)

        window_start_layout = QHBoxLayout()
        window_start_layout.addWidget(QLabel("Water Window Start:"))
        self.window_start_entry_online = QDateTimeEdit(calendarPopup=True)
        window_start_layout.addWidget(self.window_start_entry_online)
        layout.addLayout(window_start_layout)

        window_end_layout = QHBoxLayout()
        window_end_layout.addWidget(QLabel("Water Window End:"))
        self.window_end_entry_online = QDateTimeEdit(calendarPopup=True)
        window_end_layout.addWidget(self.window_end_entry_online)
        layout.addLayout(window_end_layout)

        self.online_tab.setLayout(layout)

    def init_offline_tab(self):
        layout = QVBoxLayout()

        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Interval (seconds):"))
        self.interval_entry_offline = QLineEdit()
        interval_layout.addWidget(self.interval_entry_offline)
        layout.addLayout(interval_layout)

        stagger_layout = QHBoxLayout()
        stagger_layout.addWidget(QLabel("Stagger (seconds):"))
        self.stagger_entry_offline = QLineEdit()
        stagger_layout.addWidget(self.stagger_entry_offline)
        layout.addLayout(stagger_layout)

        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Program Duration (seconds):"))
        self.duration_entry_offline = QLineEdit()
        duration_layout.addWidget(self.duration_entry_offline)
        layout.addLayout(duration_layout)

        self.offline_tab.setLayout(layout)

    def run_program(self):
        if self.tab_widget.currentIndex() == 0:  # Online tab
            interval = int(self.interval_entry_online.text())
            stagger = int(self.stagger_entry_online.text())
            window_start = self.window_start_entry_online.dateTime().toSecsSinceEpoch()
            window_end = self.window_end_entry_online.dateTime().toSecsSinceEpoch()
            self.run_program_callback(interval, stagger, window_start, window_end, mode='online')
        else:  # Offline tab
            interval = int(self.interval_entry_offline.text())
            stagger = int(self.stagger_entry_offline.text())
            duration = int(self.duration_entry_offline.text())
            window_start = time.time()
            window_end = window_start + duration
            self.run_program_callback(interval, stagger, window_start, window_end, mode='offline')

    def stop_program(self):
        self.stop_program_callback()

    def change_relay_hats(self):
        self.change_relay_hats_callback()

    def update_settings(self):
        self.update_all_settings_callback()
