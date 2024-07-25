from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QCheckBox, QScrollArea, QWidget, QPushButton
from PyQt5.QtCore import Qt

class AdvancedSettingsSection(QGroupBox):
    def __init__(self, settings, update_all_settings_callback, print_to_terminal):
        super().__init__("Advanced Settings")
        self.settings = settings
        self.update_all_settings_callback = update_all_settings_callback
        self.print_to_terminal = print_to_terminal

        layout = QVBoxLayout()

        self.relay_checkboxes = {}
        self.trigger_entries = {}

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout()
        self.scroll_content.setLayout(self.scroll_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_content)

        self.update_relay_checkboxes(self.settings['relay_pairs'])

        self.update_settings_button = QPushButton("Update Settings")
        self.update_settings_button.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        self.update_settings_button.clicked.connect(self.update_all_settings_callback)
        self.scroll_layout.addWidget(self.update_settings_button)

        layout.addWidget(self.scroll_area)
        self.setLayout(layout)

    def update_relay_checkboxes(self, relay_pairs):
        # Clear the existing widgets
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.relay_checkboxes = {}
        self.trigger_entries = {}

        for relay_pair in relay_pairs:
            relay_pair_tuple = tuple(relay_pair)
            check_box = QCheckBox(f"Enable Relays {relay_pair[0]} & {relay_pair[1]}")
            check_box.setStyleSheet("QCheckBox { font-size: 14px; padding: 5px; }")
            check_box.setChecked(True)
            check_box.stateChanged.connect(lambda state, rp=relay_pair_tuple: self.toggle_relay_callback(rp, state))
            self.scroll_layout.addWidget(check_box)
            self.relay_checkboxes[relay_pair_tuple] = check_box

            entry_layout = QHBoxLayout()
            entry_layout.addWidget(QLabel("Triggers:"))
            trigger_entry = QLineEdit()
            trigger_entry.setStyleSheet("QLineEdit { font-size: 14px; padding: 5px; }")
            trigger_entry.setText("0")
            entry_layout.addWidget(trigger_entry)
            self.trigger_entries[relay_pair_tuple] = trigger_entry
            self.scroll_layout.addLayout(entry_layout)

    def toggle_relay_callback(self, relay_pair, state):
        if state == Qt.Checked:
            self.settings['selected_relays'].append(relay_pair)
        else:
            if relay_pair in self.settings['selected_relays']:
                self.settings['selected_relays'].remove(relay_pair)

    def get_settings(self):
        settings = {
            'selected_relays': [rp for rp, checkbox in self.relay_checkboxes.items() if checkbox.isChecked()],
            'num_triggers': {rp: int(self.trigger_entries[rp].text()) for rp in self.trigger_entries}
        }
        return settings

