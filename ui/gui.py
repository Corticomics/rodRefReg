import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QPushButton, QFrame
from PyQt5.QtCore import Qt

from .terminal_output import TerminalOutput
from .welcome_section import WelcomeSection
from .advanced_settings import AdvancedSettingsSection
from .suggest_settings import SuggestSettings
from .run_stop_section import RunStopSection

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'settings'))
from config import load_settings

class RodentRefreshmentGUI(QWidget):
    def __init__(self, run_program, stop_program, update_all_settings, change_relay_hats, settings, style='bitlearns'):
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

        if style == 'bitlearns':
            self.setStyleSheet("""
                QWidget {
                    background-color: #f8f9fa;
                }
                QGroupBox {
                    background-color: #ffffff;
                    border: 1px solid #ced4da;
                    border-radius: 5px;
                    padding: 15px;
                }
                QPushButton {
                    background-color: #007bff;
                    border: 1px solid #007bff;
                    border-radius: 5px;
                    color: #ffffff;
                    padding: 10px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
                QFrame {
                    background-color: #ced4da;
                    height: 1px;
                    margin: 10px 0;
                }
                QLabel {
                    color: #343a40;
                    background-color: #ffffff;
                }
                QLineEdit {
                    background-color: #ffffff;
                    border: 1px solid #ced4da;
                    padding: 5px;
                    font-size: 14px;
                }
                QTextEdit {
                    background-color: #ffffff;
                    border: 1px solid #ced4da;
                }
            """)

        self.main_layout = QVBoxLayout()

        self.welcome_section = WelcomeSection()
        self.welcome_scroll_area = QScrollArea()
        self.welcome_scroll_area.setWidgetResizable(True)
        self.welcome_scroll_area.setWidget(self.welcome_section)
        self.welcome_scroll_area.setMinimumHeight(self.height() // 2)
        self.welcome_scroll_area.setMaximumHeight(self.height() // 2)
        self.main_layout.addWidget(self.welcome_scroll_area)

        self.toggle_welcome_button = QPushButton("Hide Welcome Message")
        self.toggle_welcome_button.clicked.connect(self.toggle_welcome_message)
        self.main_layout.addWidget(self.toggle_welcome_button)

        self.upper_layout = QHBoxLayout()

        self.left_layout = QVBoxLayout()

        self.terminal_output = TerminalOutput()
        self.left_layout.addWidget(self.terminal_output)

        self.advanced_settings = AdvancedSettingsSection(self.settings, self.print_to_terminal)
        self.left_layout.addWidget(self.advanced_settings)

        self.left_content = QWidget()
        self.left_content.setLayout(self.left_layout)

        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setWidget(self.left_content)
        self.upper_layout.addWidget(self.left_scroll)

        self.right_layout = QVBoxLayout()
        self.suggest_settings_section = SuggestSettings(self.suggest_settings, self.push_settings, self.run_program, self.stop_program)
        self.right_layout.addWidget(self.suggest_settings_section)

        self.run_stop_section = RunStopSection(self.run_program, self.stop_program, self.change_relay_hats, self.update_all_settings)
        self.right_layout.addWidget(self.run_stop_section)

        self.right_content = QWidget()
        self.right_content.setLayout(self.right_layout)

        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setWidget(self.right_content)
        self.upper_layout.addWidget(self.right_scroll)

        self.main_layout.addLayout(self.upper_layout)
        self.setLayout(self.main_layout)

    def print_to_terminal(self, message):
        self.terminal_output.print_to_terminal(message)

    def toggle_welcome_message(self):
        if self.welcome_scroll_area.isVisible():
            self.welcome_scroll_area.setVisible(False)
            self.toggle_welcome_button.setText("Show Welcome Message and Instructions")
        else:
            self.welcome_scroll_area.setVisible(True)
            self.toggle_welcome_button.setText("Hide Welcome Message")
        self.adjust_ui()

    def adjust_ui(self):
        if self.welcome_scroll_area.isVisible():
            self.welcome_scroll_area.setMaximumHeight(self.height() // 2)
            self.welcome_scroll_area.setMinimumHeight(self.height() // 2)
        else:
            self.welcome_scroll_area.setMaximumHeight(0)
            self.welcome_scroll_area.setMinimumHeight(0)

        self.left_scroll.setMaximumHeight(self.height() - self.welcome_scroll_area.maximumHeight() - self.toggle_welcome_button.height())
        self.right_scroll.setMaximumHeight(self.height() - self.welcome_scroll_area.maximumHeight() - self.toggle_welcome_button.height())

        self.left_scroll.setMinimumHeight(self.height() - self.welcome_scroll_area.minimumHeight() - self.toggle_welcome_button.height())
        self.right_scroll.setMinimumHeight(self.height() - self.welcome_scroll_area.minimumHeight() - self.toggle_welcome_button.height())

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

    def start_timer(self, interval):
        self.timer = QTimer()
        self.timer.timeout.connect(self.run_program_callback)
        self.timer.start(interval * 1000)  # Convert seconds to milliseconds

    def stop_timer(self):
        if hasattr(self, 'timer'):
            self.timer.stop()