from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QLineEdit
from PyQt5.QtCore import Qt

class RunStopSection(QGroupBox):
    def __init__(self, run_program_callback, stop_program_callback, change_relay_hats_callback):
        super().__init__("Run/Stop Program")
        self.run_program_callback = run_program_callback
        self.stop_program_callback = stop_program_callback
        self.change_relay_hats_callback = change_relay_hats_callback

        layout = QVBoxLayout()

        interval_layout = QHBoxLayout()
        interval_label = QLabel("Interval (seconds):")
        interval_label.setAlignment(Qt.AlignLeft)
        self.interval_entry = QLineEdit()
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_entry)

        stagger_layout = QHBoxLayout()
        stagger_label = QLabel("Stagger (seconds):")
        stagger_label.setAlignment(Qt.AlignLeft)
        self.stagger_entry = QLineEdit()
        stagger_layout.addWidget(stagger_label)
        stagger_layout.addWidget(self.stagger_entry)

        window_start_layout = QHBoxLayout()
        window_start_label = QLabel("Water Window Start (24-hour format):")
        window_start_label.setAlignment(Qt.AlignLeft)
        self.window_start_entry = QLineEdit()
        window_start_layout.addWidget(window_start_label)
        window_start_layout.addWidget(self.window_start_entry)

        window_end_layout = QHBoxLayout()
        window_end_label = QLabel("Water Window End (24-hour format):")
        window_end_label.setAlignment(Qt.AlignLeft)
        self.window_end_entry = QLineEdit()
        window_end_layout.addWidget(window_end_label)
        window_end_layout.addWidget(self.window_end_entry)

        layout.addLayout(interval_layout)
        layout.addLayout(stagger_layout)
        layout.addLayout(window_start_layout)
        layout.addLayout(window_end_layout)

        button_layout = QHBoxLayout()

        run_button = QPushButton("Run Program")
        run_button.clicked.connect(self.run_program)
        button_layout.addWidget(run_button)

        stop_button = QPushButton("Stop Program")
        stop_button.clicked.connect(self.stop_program)
        button_layout.addWidget(stop_button)

        change_hats_button = QPushButton("Change Relay Hats")
        change_hats_button.clicked.connect(self.change_relay_hats)
        button_layout.addWidget(change_hats_button)

        layout.addLayout(button_layout)
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
