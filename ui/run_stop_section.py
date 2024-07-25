from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout

class RunStopSection(QGroupBox):
    def __init__(self, run_program_callback, stop_program_callback, change_relay_hats_callback):
        super().__init__("Run/Stop Program")

        self.run_program_callback = run_program_callback
        self.stop_program_callback = stop_program_callback
        self.change_relay_hats_callback = change_relay_hats_callback

        self.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
            }
            QLabel {
                font-size: 14px;
            }
            QPushButton {
                font-size: 14px;
                padding: 5px;
            }
            QLineEdit {
                font-size: 14px;
                padding: 5px;
            }
        """)

        layout = QVBoxLayout()

        self.interval_entry = self.add_setting_input(layout, "Interval (seconds):", "3600")
        self.stagger_entry = self.add_setting_input(layout, "Stagger (seconds):", "1")
        self.window_start_entry = self.add_setting_input(layout, "Water Window Start (24-hour format):", "8")
        self.window_end_entry = self.add_setting_input(layout, "Water Window End (24-hour format):", "20")

        button_layout = QHBoxLayout()

        run_button = QPushButton("Run Program")
        run_button.clicked.connect(self.run_program)
        button_layout.addWidget(run_button)

        stop_button = QPushButton("Stop Program")
        stop_button.clicked.connect(self.stop_program)
        button_layout.addWidget(stop_button)

        change_hats_button = QPushButton("Change Relay Hats")
        change_hats_button.clicked.connect(self.change_relay_hats_callback)
        button_layout.addWidget(change_hats_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def add_setting_input(self, layout, label_text, default_value):
        layout.addWidget(QLabel(label_text))
        entry = QLineEdit()
        entry.setText(default_value)
        layout.addWidget(entry)
        return entry

    def run_program(self):
        interval = int(self.interval_entry.text())
        stagger = int(self.stagger_entry.text())
        window_start = int(self.window_start_entry.text())
        window_end = int(self.window_end_entry.text())
        self.run_program_callback(interval, stagger, window_start, window_end)

    def stop_program(self):
        self.stop_program_callback()