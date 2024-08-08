from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QWidget, QCheckBox
from PyQt5.QtCore import Qt

class AdvancedSettingsSection(QGroupBox):
    def __init__(self, settings, print_to_terminal):
        super().__init__("Advanced Settings")
        self.settings = settings
        self.print_to_terminal = print_to_terminal

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.relay_checkboxes = {}
        self.trigger_entries = {}

        self.create_settings_ui()

    def create_settings_ui(self):
        self.clear_layout(self.layout)

        for relay_pair in self.settings['relay_pairs']:
            relay_pair_tuple = tuple(relay_pair)
            check_box = QCheckBox(f"Enable Relays {relay_pair[0]} & {relay_pair[1]}")
            check_box.setStyleSheet("QCheckBox { font-size: 14px; padding: 5px; }")
            check_box.setChecked(True)
            check_box.stateChanged.connect(lambda state, rp=relay_pair_tuple: self.toggle_relay_callback(rp, state))
            self.layout.addWidget(check_box)
            self.relay_checkboxes[relay_pair_tuple] = check_box

            entry_layout = QHBoxLayout()
            entry_layout.addWidget(QLabel("Triggers:"))
            trigger_entry = QLineEdit()
            trigger_entry.setStyleSheet("QLineEdit { font-size: 14px; padding: 5px; }")
            trigger_entry.setText("0")
            entry_layout.addWidget(trigger_entry)
            self.trigger_entries[relay_pair_tuple] = trigger_entry
            self.layout.addLayout(entry_layout)

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
        settings = {
            'selected_relays': [rp for rp, checkbox in self.relay_checkboxes.items() if checkbox.isChecked()],
            'num_triggers': {rp: int(self.trigger_entries[rp].text()) for rp in self.trigger_entries}
        }
        return settings

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def update_relay_hats(self, relay_pairs):
        self.settings['relay_pairs'] = relay_pairs
        self.create_settings_ui()
        self.print_to_terminal("Advanced settings updated with new relay hats.")
