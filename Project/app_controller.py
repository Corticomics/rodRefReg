# Project/app_controller.py
import sys
from PyQt5.QtWidgets import QApplication, QInputDialog, QMessageBox
from PyQt5.QtCore import Qt, QThread
import logging

from gpio.gpio_handler import RelayHandler
from gpio.relay_worker import RelayWorker
from notifications.notifications import NotificationHandler
from settings.config import load_settings, save_settings, create_relay_pairs
from ui.gui import RodentRefreshmentGUI
from utils.stream_redirector import StreamRedirector

class AppController:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.settings = load_settings()
        self.relay_handler = None
        self.notification_handler = None
        self.worker = None
        self.thread = None
        self.gui = None
        self.redirector = None

    def setup(self):
        # Prompt user for the number of relay hats
        num_hats, ok = QInputDialog.getInt(None, "Number of Relay Hats", 
                                           "Enter the number of relay hats:", min=1, max=8)
        if not ok:
            sys.exit()

        # Update settings with the number of hats
        self.settings['num_hats'] = num_hats
        self.settings['relay_pairs'] = create_relay_pairs(num_hats)

        # Initialize RelayHandler
        self.relay_handler = RelayHandler(self.settings['relay_pairs'], num_hats)

        # Ensure all relays are deactivated during setup
        self.relay_handler.set_all_relays(0)

        # Initialize NotificationHandler
        self.notification_handler = NotificationHandler(self.settings.get('slack_token', ""), 
                                                          self.settings.get('channel_id', ""))

        # Initialize GUI
        self.gui = RodentRefreshmentGUI(self.run_program, self.stop_program, 
                                        self.change_relay_hats, self.settings)
        self.gui.show()

        # Initialize StreamRedirector
        self.redirector = StreamRedirector()
        self.redirector.message_signal.connect(self.gui.system_message_signal)
        sys.stdout = self.redirector
        sys.stderr = self.redirector

    def run_program(self, interval, stagger, window_start, window_end):
        try:
            logging.info(f"Running program with interval: {interval}, stagger: {stagger}, "
                         f"window_start: {window_start}, window_end: {window_end}")

            # Update settings based on advanced settings
            advanced_settings = self.gui.advanced_settings.get_settings()
            advanced_settings['num_triggers'] = {str(k): v for k, v in advanced_settings['num_triggers'].items()}
            self.settings.update(advanced_settings)

            # Initialize RelayWorker
            self.worker = RelayWorker(self.settings, self.relay_handler, self.notification_handler)

            # Start thread
            self.thread = QThread()
            self.worker.moveToThread(self.thread)

            # Connect signals
            self.thread.started.connect(self.worker.run_cycle)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.progress.connect(self.gui.print_to_terminal)

            self.thread.start()

            logging.info("Program Started")
        except Exception as e:
            logging.error(f"Error running program: {e}")
            self.gui.print_to_terminal(f"Error running program: {e}")

    def stop_program(self):
        try:
            if self.worker:
                self.worker.stop()

            if self.thread and self.thread.isRunning():
                self.thread.quit()
                self.thread.wait()

            # Cleanup
            self.cleanup()

            logging.info("Program Stopped")
        except Exception as e:
            logging.error(f"Error stopping program: {e}")
            self.gui.print_to_terminal(f"Error stopping program: {e}")

    def cleanup(self):
        try:
            logging.debug("Starting cleanup process")

            # Ensure all relays are deactivated
            if self.relay_handler:
                self.relay_handler.set_all_relays(0)
                logging.debug("All relays deactivated")

            # Stop and delete the thread
            if self.thread and self.thread.isRunning():
                self.thread.quit()
                self.thread.wait()
                logging.debug("Thread stopped")

            self.worker = None
            self.thread = None

            # Reset GUI buttons and state
            if self.gui:
                self.gui.run_stop_section.job_in_progress = False
                self.gui.run_stop_section.update_button_states()

            logging.debug("Cleanup completed. Program ready for the next job.")
        except Exception as e:
            logging.error(f"An unexpected error occurred during cleanup: {e}")
            self.gui.print_to_terminal(f"An unexpected error occurred during cleanup: {e}")

    def change_relay_hats(self):
        try:
            if self.gui.run_stop_section.job_in_progress:
                QMessageBox.warning(self.gui, "Job in Progress", "Cannot change relay hats while a job is running.")
                return

            # Prompt user for the number of relay hats
            num_hats, ok = QInputDialog.getInt(self.gui, "Number of Relay Hats", 
                                               "Enter the number of relay hats:", min=1, max=8)
            if not ok:
                return

            # Update settings
            self.settings['num_hats'] = num_hats
            self.settings['relay_pairs'] = create_relay_pairs(num_hats)

            # Update RelayHandler
            self.relay_handler.update_relay_hats(self.settings['relay_pairs'], num_hats)
            self.relay_handler.set_all_relays(0)
            logging.info(f"Relay hats updated to {num_hats} hats.")

            # Reinitialize AdvancedSettings UI
            self.gui.advanced_settings.update_relay_hats(self.settings['relay_pairs'])

            # Reset the UI to ensure no lingering data or state
            self.gui.run_stop_section.reset_ui()

            # Notify user
            self.gui.print_to_terminal(f"Relay hats updated to {num_hats} hats.")
        except Exception as e:
            logging.error(f"Error changing relay hats: {e}")
            QMessageBox.critical(self.gui, "Error", f"Failed to change relay hats: {e}")

    def execute(self):
        sys.exit(self.app.exec_())
