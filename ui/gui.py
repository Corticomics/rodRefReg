import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QGridLayout, QPushButton
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

        self.welcome_section = WelcomeSection(self.toggle_welcome_message)
        main_layout.addWidget(self.welcome_section)

        middle_layout = QHBoxLayout()
        self.advanced_settings = AdvancedSettingsSection(self.settings, self.update_all_settings, self.print_to_terminal)
        middle_layout.addWidget(self.advanced_settings)

        self.suggest_settings = SuggestSettings(self.suggest_settings, self.push_settings)
        middle_layout.addWidget(self.suggest_settings)

        main_layout.addLayout(middle_layout)

        bottom_layout = QHBoxLayout()
        self.terminal_output = TerminalOutput()
        bottom_layout.addWidget(self.terminal_output)

        self.run_stop_section = RunStopSection(self.run_program, self.stop_program, self.change_relay_hats)
        bottom_layout.addWidget(self.run_stop_section)

        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)

    def print_to_terminal(self, message):
        self.terminal_output.print_to_terminal(message)

    def toggle_welcome_message(self):
        if self.welcome_section.scroll_area.isVisible():
            self.welcome_section.scroll_area.setVisible(False)
            self.welcome_section.toggle_button.setText("Show Welcome Message and Instructions")
        else:
            self.welcome_section.scroll_area.setVisible(True)
            self.welcome_section.toggle_button.setText("Hide Welcome Message")
        self.adjust_layout()

    def adjust_layout(self):
        self.adjustSize()

    def suggest_settings(self):
        values = self.suggest_settings.get_entry_values()
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
                self.update_all_settings()
                self.print_to_terminal("Settings have been pushed to the control panel and updated.")
        except Exception as e:
            self.print_to_terminal(f"Error pushing settings: {e}")

    def get_settings(self):
        settings = self.advanced_settings.get_settings()
        return settings

def main(run_program, stop_program, update_all_settings, change_relay_hats):
    app = QApplication(sys.argv)
    gui = RodentRefreshmentGUI(run_program, stop_program, update_all_settings, change_relay_hats)
    gui.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    def run_program(interval, stagger, window_start, window_end):
        print(f"Running program with interval: {interval}, stagger: {stagger}, window_start: {window_start}, window_end: {window_end}")
        settings['interval'] = interval
        settings['stagger'] = stagger
        settings['window_start'] = window_start
        settings['window_end'] = window_end
        global running
        running = True
        threading.Thread(target=program_loop).start()
        print("Program Started")

    def stop_program():
        global running
        running = False
        relay_handler.set_all_relays(0)
        print("Program Stopped")
        app.quit()

    def update_all_settings():
        new_settings = gui.get_settings()
        settings.update(new_settings)
        print("Settings updated")

    settings = load_settings()
    relay_handler = RelayHandler(settings['relay_pairs'], settings['num_hats'])
    notification_handler = NotificationHandler(settings['slack_token'], settings['channel_id'])

    main(run_program, stop_program, update_all_settings, change_relay_hats)
