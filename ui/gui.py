import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QMessageBox
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt

from .terminal_output import TerminalOutput
from .welcome_section import WelcomeSection
from .advanced_settings import AdvancedSettingsSection
from .suggest_settings import SuggestSettings
from .run_stop_section import RunStopSection
import math

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'settings'))
from config import load_settings

class RodentRefreshmentGUI(QWidget):
    def __init__(self, run_program, stop_program, update_all_settings, change_relay_hats, settings, style='idea3'):
        super().__init__()

        self.run_program = run_program
        self.stop_program = stop_program
        self.update_all_settings = update_all_settings
        self.change_relay_hats = change_relay_hats

        self.settings = settings
        self.selected_relays = self.settings['selected_relays']
        self.num_triggers = self.settings['num_triggers']

        self.init_ui(style)

    def init_ui(self, style):
        self.setWindowTitle("Rodent Refreshment Regulator")
        self.setMinimumSize(1200, 800)

        if style == 'idea3':
            self.setStyleSheet("""
                QWidget {
                    background-color: #ffffff;
                }
                QGroupBox {
                    background-color: #ffffff;
                    border: 1px solid #dcdcdc;
                    border-radius: 5px;
                    padding: 20px;
                }
                QPushButton {
                    background-color: #e0e0e0;
                    border: 1px solid #bdbdbd;
                    border-radius: 5px;
                    padding: 10px;
                }
                QPushButton:hover {
                    background-color: #bdbdbd;
                }
                QFrame {
                    background-color: #dcdcdc;
                    height: 1px;
                    margin: 10px 0;
                }
                QLabel {
                    color: #333333;
                    background-color: #ffffff;
                }
                QTextEdit {
                    background-color: #ffffff;
                    border: 1px solid #dcdcdc;
                }
            """)

        main_layout = QVBoxLayout()

        self.terminal_output = TerminalOutput()
        main_layout.addWidget(self.terminal_output)

        upper_layout = QHBoxLayout()

        left_layout = QVBoxLayout()

        welcome_section = WelcomeSection()
        left_layout.addWidget(welcome_section)

        self.advanced_settings = AdvancedSettingsSection(self.settings, self.update_all_settings, self.print_to_terminal)
        left_layout.addWidget(self.advanced_settings)

        left_content = QWidget()
        left_content.setLayout(left_layout)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setWidget(left_content)
        upper_layout.addWidget(left_scroll)

        right_layout = QVBoxLayout()
        suggest_settings_section = SuggestSettings(self.suggest_settings, self.push_settings, self.run_program, self.stop_program)
        right_layout.addWidget(suggest_settings_section)

        run_stop_section = RunStopSection(self.run_program, self.stop_program, self.change_relay_hats)
        right_layout.addWidget(run_stop_section)

        right_content = QWidget()
        right_content.setLayout(right_layout)

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setWidget(right_content)
        upper_layout.addWidget(right_scroll)

        main_layout.addLayout(upper_layout)
        self.setLayout(main_layout)

    def print_to_terminal(self, message):
        self.terminal_output.print_to_terminal(message)

    def toggle_relay(self, relay_pair, state):
        if state == Qt.Checked:
            if relay_pair not in self.selected_relays:
                self.selected_relays.append(relay_pair)
            self.print_to_terminal(f"Relay pair {relay_pair} enabled")
        else:
            if relay_pair in self.selected_relays:
                self.selected_relays.remove(relay_pair)
            self.print_to_terminal(f"Relay pair {relay_pair} disabled")

    def suggest_settings(self):
        values = self.findChild(SuggestSettings).get_entry_values()
        if values is None:
            return

        try:
            frequency = int(values["How often should each cage receive water? (Seconds):"])
            window_start = int(values["Water window start (hour, 24-hour format):"])
            window_end = int(values["Water window end (hour, 24-hour format):"])

            suggestion_text = (
                f"Suggested Settings:\n"
                f"- Interval: {frequency} seconds\n"
                f"- Stagger: {'1'} seconds (Assumed)\n"
                f"- Water Window: {window_start}:00 to {window_end}:00\n"
            )

            for relay_pair in self.settings['relay_pairs']:
                question = f"Water volume for relays {relay_pair[0]} & {relay_pair[1]} (uL):"
                if question in values:
                    volume_per_relay = int(values[question])
                    triggers = self.calculate_triggers(volume_per_relay)
                    suggestion_text += f"- Relays {relay_pair[0]} & {relay_pair[1]} should trigger {triggers} times to dispense {volume_per_relay} micro-liters each.\n"

            self.print_to_terminal(suggestion_text)
        except ValueError as e:
            self.print_to_terminal("Please enter valid numbers for all settings.")

    def calculate_triggers(self, volume_needed):
        return math.ceil(volume_needed / 10)

    def push_settings(self):
        try:
            settings = self.advanced_settings.get_settings()
            if settings:
                for relay_pair, checkbox in self.advanced_settings.relay_checkboxes.items():
                    volume_per_relay = settings['num_triggers'][relay_pair]
                    triggers = self.calculate_triggers(volume_per_relay)
                    self.advanced_settings.trigger_entries[relay_pair].setText(str(triggers))

                    if volume_per_relay == 0:
                        checkbox.setChecked(False)
                    else:
                        checkbox.setChecked(True)

                self.update_all_settings()
                self.print_to_terminal("Settings have been pushed to the control panel and updated.")
        except Exception as e:
            self.print_to_terminal(f"Error pushing settings: {e}")

    def get_settings(self):
        settings = self.advanced_settings.get_settings()
        return settings
