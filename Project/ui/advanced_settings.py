# ui/advanced_settings.py
from PyQt5.QtWidgets import QGroupBox, QFormLayout, QLabel, QLineEdit
from PyQt5.QtCore import Qt
import logging

class AdvancedSettingsSection(QGroupBox):
    def __init__(self, settings, print_to_terminal_callback):
        super().__init__("Advanced Settings")
        self.settings = settings
        self.print_to_terminal = print_to_terminal_callback

        self.layout = QFormLayout()
        self.setLayout(self.layout)

        self.trigger_entries = {}

        self.create_settings_ui()

    def create_settings_ui(self):
        self.clear_layout(self.layout)

        for relay_pair in self.settings['relay_pairs']:
            relay_pair_str = str(relay_pair)
            label = QLabel(f"Relays {relay_pair[0]} & {relay_pair[1]} Triggers:")
            trigger_entry = QLineEdit()
            trigger_entry.setStyleSheet("QLineEdit { font-size: 14px; padding: 5px; }")
            trigger_entry.setText("0")  # Default to 0 triggers
            self.layout.addRow(label, trigger_entry)
            self.trigger_entries[relay_pair_str] = trigger_entry

    def get_settings(self):
        selected_relays = []
        num_triggers = {}

        for relay_pair_str, entry in self.trigger_entries.items():
            try:
                triggers = int(entry.text())
                if triggers > 0:
                    relay_pair = eval(relay_pair_str)
                    selected_relays.append(relay_pair)
                    num_triggers[relay_pair_str] = triggers
            except ValueError:
                logging.error(f"Invalid trigger count for {relay_pair_str}: {entry.text()}")

        return {
            'selected_relays': selected_relays,
            'num_triggers': num_triggers
        }

    def clear_layout(self, layout):
        """Safely clear the layout by disconnecting and deleting all widgets."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        layout.update()  # Ensure the layout updates correctly after clearing

    def update_relay_hats(self, relay_pairs):
        try:
            # Update relay pairs in the settings
            self.settings['relay_pairs'] = relay_pairs

            # Clear and recreate the UI elements
            self.create_settings_ui()

            # Notify the terminal output about the update
            self.print_to_terminal("Advanced settings updated with new relay hats.")
        except Exception as e:
            # Handle any errors that may occur during the update
            self.print_to_terminal(f"Error updating relay hats: {e}")
    
    def update_triggers(self, num_triggers):
        """
        Update the trigger settings for the relays based on the loaded num_triggers.
        """
        try:
            for relay_pair_str, trigger_value in num_triggers.items():
                if relay_pair_str in self.trigger_entries:
                    self.trigger_entries[relay_pair_str].setText(str(trigger_value))
                else:
                    logging.warning(f"Relay pair {relay_pair_str} not found in trigger entries.")
            self.print_to_terminal("Advanced settings triggers updated successfully.")
        except Exception as e:
            logging.error(f"Error updating triggers in advanced settings: {e}")
            self.print_to_terminal(f"Error updating triggers in advanced settings: {e}")
