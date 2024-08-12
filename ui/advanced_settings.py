from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit
from PyQt5.QtCore import Qt

class AdvancedSettingsSection(QGroupBox):
    def __init__(self, settings, print_to_terminal):
        super().__init__("Advanced Settings")
        self.settings = settings
        self.print_to_terminal = print_to_terminal

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.trigger_entries = {}

        self.create_settings_ui()

    def create_settings_ui(self):
        self.clear_layout(self.layout)

        for relay_pair in self.settings['relay_pairs']:
            relay_pair_tuple = tuple(relay_pair)

            entry_layout = QHBoxLayout()
            entry_layout.addWidget(QLabel(f"Relays {relay_pair[0]} & {relay_pair[1]} Triggers:"))
            trigger_entry = QLineEdit()
            trigger_entry.setStyleSheet("QLineEdit { font-size: 14px; padding: 5px; }")
            trigger_entry.setText("0")  # Default all relays to 0 triggers
            entry_layout.addWidget(trigger_entry)
            self.trigger_entries[relay_pair_tuple] = trigger_entry
            self.layout.addLayout(entry_layout)

    def get_settings(self):
        selected_relays = []
        num_triggers = {}

        for relay_pair, entry in self.trigger_entries.items():
            triggers = int(entry.text())
            if triggers > 0:
                selected_relays.append(relay_pair)
                num_triggers[relay_pair] = triggers  # Store as tuple, not string

        settings = {
            'selected_relays': selected_relays,
            'num_triggers': num_triggers
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
