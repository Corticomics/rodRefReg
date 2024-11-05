# app/ui/gui.py

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QPushButton,
    QSplitter, QSizePolicy, QLabel
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDrag, QMimeData

from .terminal_output import TerminalOutput
from .welcome_section import WelcomeSection
from .suggest_settings import SuggestSettingsSection
from .run_stop_section import RunStopSection
from .SlackCredentialsTab import SlackCredentialsTab
from shared.notifications.notifications import NotificationHandler
from shared.models.database import DatabaseManager

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'settings'))
from shared.settings.config import load_settings, save_settings

class DraggableWidget(QLabel):
    def __init__(self, text):
        super().__init__(text)
        self.setFixedSize(120, 40)
        self.setStyleSheet("border: 1px solid #007bff; background-color: #e7f1ff;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.text())
            drag.setMimeData(mime_data)
            drag.exec_(Qt.MoveAction)

class DropArea(QWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.setStyleSheet("border: 1px dashed #0056b3; background-color: #f0f4f9;")

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        widget = DraggableWidget(event.mimeData().text())
        self.layout.addWidget(widget)

class RodentRefreshmentGUI(QWidget):
    system_message_signal = pyqtSignal(str)

    def __init__(self, run_program, stop_program, change_relay_hats, settings, db_manager, style='bitlearns'):
        super().__init__()

        self.run_program = run_program
        self.stop_program = stop_program
        self.change_relay_hats = change_relay_hats
        self.settings = settings
        self.db_manager = db_manager

        self.init_ui(style)

    def init_ui(self, style):
        self.setWindowTitle("Rodent Refreshment Regulator")
        self.setMinimumSize(1200, 800)

        if style == 'bitlearns':
            self.setStyleSheet("""
                QWidget {
                    background-color: #f8f9fa;
                    font-size: 14px;
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
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                    color: #666666;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
                QLabel {
                    color: #343a40;
                    background-color: #ffffff;
                }
                QLineEdit, QTextEdit {
                    background-color: #ffffff;
                    border: 1px solid #ced4da;
                    padding: 5px;
                }
            """)

        # Main Layout
        self.main_layout = QVBoxLayout()

        # Welcome Section
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

        # Left Layout
        self.left_layout = QVBoxLayout()
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.terminal_output = TerminalOutput()
        self.splitter.addWidget(self.terminal_output)

        # Drag and Drop Area - Replaces Advanced Settings
        self.drop_area = DropArea()
        self.splitter.addWidget(self.drop_area)
        self.left_layout.addWidget(self.splitter)

        self.left_content = QWidget()
        self.left_content.setLayout(self.left_layout)
        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setWidget(self.left_content)
        self.upper_layout.addWidget(self.left_scroll)

        # Right Layout
        self.right_layout = QVBoxLayout()
        self.run_stop_section = RunStopSection(self.run_program, self.stop_program, self.change_relay_hats, self.settings)

        # Suggest Settings Section
        self.suggest_settings_section = SuggestSettingsSection(
            db_manager=self.db_manager,
            settings=self.settings, 
            suggest_settings_callback=self.suggest_settings_callback, 
            push_settings_callback=self.push_settings_callback,
            save_slack_credentials_callback=self.save_slack_credentials_callback
        )

        self.right_layout.addWidget(self.suggest_settings_section)
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

    def suggest_settings_callback(self):
        """Callback for suggesting settings based on user input."""
        values = self.suggest_settings_section.suggest_tab.entries
        try:
            relay_pairs = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16)]
            relay_volumes = {}
            for relay_pair in relay_pairs:
                volume_input = values[f"relay_{relay_pair[0]}_{relay_pair[1]}"].text().strip()
                water_volume = float(volume_input) if volume_input else 0.0
                relay_volumes[relay_pair] = water_volume

            frequency_input = values["frequency"].text().strip()
            frequency = int(frequency_input) if frequency_input else 0
            duration_input = values["duration"].text().strip()
            duration = int(duration_input) if duration_input else 0

            start_datetime = values["start_datetime"].dateTime()
            total_sessions = frequency * duration
            interval_seconds = 86400 / frequency if frequency > 0 else 0

            self.suggested_settings = {
                "start_datetime": start_datetime,
                "duration": duration,
                "relay_volumes": relay_volumes,
                "frequency": frequency,
                "interval_seconds": interval_seconds,
                "total_sessions": total_sessions
            }

            suggestion_text = f"--- Suggested Settings ---\n"
            suggestion_text += f"Start Date & Time: {start_datetime.toString('yyyy-MM-dd HH:mm:ss')}\n"
            suggestion_text += f"Duration: {duration} day(s)\n"
            suggestion_text += f"Dispensing Frequency: {frequency} times per day\n"
            suggestion_text += f"Total Sessions: {total_sessions}\n"
            suggestion_text += f"Interval Between Sessions: {interval_seconds / 60:.2f} minutes\n"
            for relay_pair, volume in relay_volumes.items():
                suggestion_text += f"Water Volume for Relays {relay_pair[0]} & {relay_pair[1]}: {volume} mL\n"
            self.print_to_terminal(suggestion_text)

        except ValueError as ve:
            self.print_to_terminal(f"Input Error: {ve}")
        except Exception as e:
            self.print_to_terminal(f"An unexpected error occurred: {e}")

    def push_settings_callback(self):
        """Callback for pushing the suggested settings to the control panel."""
        try:
            if not hasattr(self, 'suggested_settings'):
                self.print_to_terminal("No suggested settings available. Please generate suggestions first.")
                return

            settings = self.suggested_settings
            self.run_stop_section.start_time_input.setDateTime(settings["start_datetime"])
            end_datetime = settings["start_datetime"].addDays(settings["duration"])
            self.run_stop_section.end_time_input.setDateTime(end_datetime)
            self.run_stop_section.interval_input.setText(str(int(settings["interval_seconds"])))
            self.run_stop_section.stagger_input.setText("5")

            num_triggers = {}
            for relay_pair, water_volume in settings["relay_volumes"].items():
                trigger_count = int((water_volume * 1000) / 500) if water_volume > 0 else 0
                num_triggers[relay_pair] = trigger_count

            # Assuming RunStopSection has an update_triggers method
            self.run_stop_section.update_triggers(num_triggers)

            self.print_to_terminal("Suggested settings have been applied successfully.")
        except Exception as e:
            self.print_to_terminal(f"Error applying suggested settings: {e}")

    def save_slack_credentials_callback(self):
        """Callback to save Slack credentials to the settings file."""
        try:
            self.settings['slack_token'] = self.suggest_settings_section.slack_tab.slack_token_input.text()
            self.settings['channel_id'] = self.suggest_settings_section.slack_tab.slack_channel_input.text()
            save_settings(self.settings)
            self.print_to_terminal("Slack credentials saved and notification handler reinitialized.")
        except Exception as e:
            self.print_to_terminal(f"Error saving Slack credentials: {e}")

def main(run_program, stop_program, change_relay_hats):
    app = QApplication(sys.argv)
    settings = load_settings()
    db_manager = DatabaseManager()  # Replace with actual initialization

    gui = RodentRefreshmentGUI(run_program, stop_program, change_relay_hats, settings, db_manager, style='bitlearns')
    gui.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()