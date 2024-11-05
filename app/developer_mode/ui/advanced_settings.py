from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QFormLayout
from PyQt5.QtCore import Qt

class AdvancedSettingsSection(QGroupBox):
    def __init__(self, settings, print_to_terminal):
        super().__init__("Advanced Settings")
        self.settings = settings
        self.print_to_terminal = print_to_terminal

        self.layout = QFormLayout()
        self.setLayout(self.layout)

        self.trigger_entries = {}

        self.create_settings_ui()

    def create_settings_ui(self):
        # Clear the layout before repopulating
        self.clear_layout(self.layout)

        # Populate the UI with new relay settings
        for relay_pair in self.settings['relay_pairs']:
            relay_pair_tuple = tuple(relay_pair)

            label = QLabel(f"Relays {relay_pair[0]} & {relay_pair[1]} Triggers:")
            trigger_entry = QLineEdit()
            trigger_entry.setStyleSheet("QLineEdit { font-size: 14px; padding: 5px; }")
            trigger_entry.setText("0")  # Default all relays to 0 triggers
            self.trigger_entries[relay_pair_tuple] = trigger_entry

            # Add the label and entry widget directly to the form layout
            self.layout.addRow(label, trigger_entry)


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
            for relay_pair, trigger_value in num_triggers.items():
                if relay_pair in self.trigger_entries:
                    self.trigger_entries[relay_pair].setText(str(trigger_value))
                else:
                    print(f"Warning: Relay pair {relay_pair} not found in trigger entries.")
            print("Advanced settings triggers updated successfully.")
        except Exception as e:
            print(f"Error updating triggers in advanced settings: {e}")

