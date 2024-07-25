from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QWidget

class RunStopSection(QGroupBox):
    def __init__(self, run_program_callback, stop_program_callback, change_relay_hats_callback):
        super().__init__("Run/Stop Program")
        self.run_program_callback = run_program_callback
        self.stop_program_callback = stop_program_callback
        self.change_relay_hats_callback = change_relay_hats_callback

        layout = QVBoxLayout()

        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Interval (seconds):"))
        self.interval_entry = QLineEdit()
        self.interval_entry.setStyleSheet("QLineEdit { font-size: 14px; padding: 5px; }")
        interval_layout.addWidget(self.interval_entry)
        layout.addLayout(interval_layout)

        stagger_layout = QHBoxLayout()
        stagger_layout.addWidget(QLabel("Stagger (seconds):"))
        self.stagger_entry = QLineEdit()
        self.stagger_entry.setStyleSheet("QLineEdit { font-size: 14px; padding: 5px; }")
        stagger_layout.addWidget(self.stagger_entry)
        layout.addLayout(stagger_layout)

        window_start_layout = QHBoxLayout()
        window_start_layout.addWidget(QLabel("Water Window Start (24-hour format):"))
        self.window_start_entry = QLineEdit()
        self.window_start_entry.setStyleSheet("QLineEdit { font-size: 14px; padding: 5px; }")
        window_start_layout.addWidget(self.window_start_entry)
        layout.addLayout(window_start_layout)

        window_end_layout = QHBoxLayout()
        window_end_layout.addWidget(QLabel("Water Window End (24-hour format):"))
        self.window_end_entry = QLineEdit()
        self.window_end_entry.setStyleSheet("QLineEdit { font-size: 14px; padding: 5px; }")
        window_end_layout.addWidget(self.window_end_entry)
        layout.addLayout(window_end_layout)

        run_button = QPushButton("Run Program")
        run_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        run_button.clicked.connect(self.run_program)
        layout.addWidget(run_button)

        stop_button = QPushButton("Stop Program")
        stop_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        stop_button.clicked.connect(self.stop_program)
        layout.addWidget(stop_button)

        change_hats_button = QPushButton("Change Relay Hats")
        change_hats_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        change_hats_button.clicked.connect(self.change_relay_hats)
        layout.addWidget(change_hats_button)

        self.setLayout(layout)

    def run_program(self):
        interval = int(self.interval_entry.text())
        stagger = int(self.stagger_entry.text())
        window_start = int(self.window_start_entry.text())
        window_end = int(self.window_end_entry.text())
        self.run_program_callback(interval, stagger, window_start, window_end)

    def stop_program(self):
        self.stop_program_callback()

    def change_relay_hats(self):
        self.change_relay_hats_callback()
