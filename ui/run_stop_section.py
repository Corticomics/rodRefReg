from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QLineEdit, QPushButton

class RunStopSection(QGroupBox):
    def __init__(self, run_program_callback, stop_program_callback, change_relay_hats_callback):
        super().__init__("Run/Stop Program")

        self.run_program_callback = run_program_callback
        self.stop_program_callback = stop_program_callback
        self.change_relay_hats_callback = change_relay_hats_callback

        layout = QVBoxLayout()

        self.interval_entry = self.add_setting_input(layout, "Interval (seconds):", "3600")
        self.stagger_entry = self.add_setting_input(layout, "Stagger (seconds):", "1")
        self.window_start_entry = self.add_setting_input(layout, "Water Window Start (24-hour format):", "8")
        self.window_end_entry = self.add_setting_input(layout, "Water Window End (24-hour format):", "20")

        run_button = QPushButton("Run Program")
        run_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        run_button.clicked.connect(lambda: self.run_program_callback(
            int(self.interval_entry.text()), int(self.stagger_entry.text()),
            int(self.window_start_entry.text()), int(self.window_end_entry.text())
        ))
        layout.addWidget(run_button)

        stop_button = QPushButton("Stop Program")
        stop_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        stop_button.clicked.connect(self.stop_program_callback)
        layout.addWidget(stop_button)

        change_hats_button = QPushButton("Change Relay Hats")
        change_hats_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        change_hats_button.clicked.connect(self.change_relay_hats_callback)
        layout.addWidget(change_hats_button)

        self.setLayout(layout)

    def add_setting_input(self, layout, label_text, default_value):
        layout.addWidget(QLabel(label_text))
        entry = QLineEdit()
        entry.setStyleSheet("QLineEdit { font-size: 14px; padding: 5px; }")
        entry.setText(default_value)
        layout.addWidget(entry)
        return entry
