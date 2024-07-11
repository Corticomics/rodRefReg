from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QWidget, QCheckBox, QSpinBox
from PyQt5.QtCore import Qt

class AdvancedSettingsSection(QGroupBox):
    def __init__(self, settings, update_all_settings_callback):
        super().__init__("Advanced Settings")
        self.settings = settings
        self.update_all_settings_callback = update_all_settings_callback

        layout = QVBoxLayout()

        # Number of relay hats input
        layout.addWidget(QLabel("Number of Relay Hats:"))
        self.num_hats_input = QSpinBox()
        self.num_hats_input.setRange(1, 8)
        self.num_hats_input.setValue(self.settings.get('num_hats', 1))
        layout.addWidget(self.num_hats_input)

        self.relay_checkboxes = {}
        self.trigger_entries = {}

        for relay_pair in self.settings['relay_pairs']:
            relay_pair_tuple = tuple(relay_pair)
            check_box = QCheckBox(f"Enable Relays {relay_pair[0]} & {relay_pair[1]}")
            check_box.setStyleSheet("QCheckBox { font-size: 14px; padding: 5px; }")
            check_box.setChecked(True)
            check_box.stateChanged.connect(lambda state, rp=relay_pair_tuple: self.toggle_relay_callback(rp, state))
            layout.addWidget(check_box)
            self.relay_checkboxes[relay_pair_tuple] = check_box

            entry_layout = QHBoxLayout()
            entry_layout.addWidget(QLabel("Triggers:"))
            trigger_entry = QLineEdit()
            trigger_entry.setStyleSheet("QLineEdit { font-size: 14px; padding: 5px; }")
            trigger_entry.setText("0")
            entry_layout.addWidget(trigger_entry)
            self.trigger_entries[relay_pair_tuple] = trigger_entry
            layout.addLayout(entry_layout)

        self.interval_entry = self.add_setting_input(layout, "Interval (seconds):", self.settings['interval'])
        self.stagger_entry = self.add_setting_input(layout, "Stagger (seconds):", self.settings['stagger'])
        self.window_start_entry = self.add_setting_input(layout, "Water Window Start (24-hour format):", self.settings['window_start'])
        self.window_end_entry = self.add_setting_input(layout, "Water Window End (24-hour format):", self.settings['window_end'])

        update_settings_button = QPushButton("Update Settings")
        update_settings_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        update_settings_button.clicked.connect(self.update_all_settings_callback)
        layout.addWidget(update_settings_button)

        scroll_content = QWidget()
        scroll_content.setLayout(layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_content)

        outer_layout = QVBoxLayout()
        outer_layout.addWidget(scroll_area)
        self.setLayout(outer_layout)

    def toggle_relay_callback(self, relay_pair, state):
        if state == Qt.Checked:
            self.settings['selected_relays'].append(relay_pair)
        else:
            if relay_pair in self.settings['selected_relays']:
                self.settings['selected_relays'].remove(relay_pair)

    def add_setting_input(self, layout, label_text, default_value):
        layout.addWidget(QLabel(label_text))
        entry = QLineEdit()
        entry.setStyleSheet("QLineEdit { font-size: 14px; padding: 5px; }")
        entry.setText(str(default_value))
        layout.addWidget(entry)
        return entry

    def get_settings(self):
        try:
            settings = {
                'num_hats': self.num_hats_input.value(),
                'interval': int(self.interval_entry.text()),
                'stagger': int(self.stagger_entry.text()),
                'window_start': int(self.window_start_entry.text()),
                'window_end': int(self.window_end_entry.text()),
                'selected_relays': [rp for rp, checkbox in self.relay_checkboxes.items() if checkbox.isChecked()],
                'num_triggers': {rp: int(self.trigger_entries[rp].text()) for rp in self.trigger_entries}
            }
        except ValueError as e:
            print("Invalid input:", e)
            settings = None
        return settings
