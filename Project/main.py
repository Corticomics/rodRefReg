import sys
import os
from PyQt5.QtWidgets import QApplication, QInputDialog
from PyQt5.QtCore import Qt, QThread, QObject, pyqtSignal
from gpio.relay_worker import RelayWorker
from ui.gui import RodentRefreshmentGUI
from gpio.gpio_handler import RelayHandler
from notifications.notifications import NotificationHandler
from settings.config import load_settings, save_settings
from controllers.projects_controller import ProjectsController
from models.database_handler import DatabaseHandler
from models.login_system import LoginSystem  # Import LoginSystem
import time

class StreamRedirector(QObject):
    message_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def write(self, message):
        if message.strip():  # Ignore empty messages
            self.message_signal.emit(message)

    def flush(self):
        pass

# Initialize thread and worker globally to reuse them
thread = QThread()
worker = None

def setup():
    global relay_handler, settings, gui, notification_handler, controller, database_handler, login_system

    # Initialize the Projects Controller and Database Handler
    controller = ProjectsController()
    database_handler = DatabaseHandler()

    # Initialize the login system with database handler and assume "Guest" mode if not logged in
    login_system = LoginSystem(database_handler)
    if not login_system.is_logged_in():
        login_system.set_guest_mode()  # Default to guest mode if no login

    # Load settings (if any) and initialize relays
    settings = load_settings()

    # Initialize relay handler and close all relays
    relay_handler = RelayHandler(settings.get('relay_pairs', []), settings.get('num_hats', 1))
    relay_handler.set_all_relays(0)  # Ensure all relays are closed during setup

    # Initialize Slack notification handler
    notification_handler = NotificationHandler(settings.get('slack_token', 'SLACKTOKEN'), settings.get('channel_id', 'ChannelId'))

    # Initialize GUI components, including login system and database handler
    gui = RodentRefreshmentGUI(run_program, stop_program, change_relay_hats, settings, database_handler=database_handler, login_system=login_system)

def run_program(interval, stagger, window_start, window_end):
    global thread, worker, notification_handler, controller  # Ensure global scope for controller

    try:
        print(f"Running program with interval: {interval}, stagger: {stagger}, window_start: {window_start}, window_end: {window_end}")

        # Reinitialize the thread and worker
        if thread is not None:
            thread.quit()
            thread.wait()
        thread = QThread()

        # Reinitialize NotificationHandler within the worker context
        worker_notification_handler = NotificationHandler(settings.get('slack_token', 'SLACKTOKEN'), settings.get('channel_id', 'ChannelId'))

        worker = RelayWorker(settings, relay_handler, worker_notification_handler)
        worker.moveToThread(thread)

        # Connect signals and slots
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(cleanup, Qt.QueuedConnection)  # Ensure cleanup runs in the main thread
        thread.finished.connect(thread.deleteLater)

        worker.progress.connect(lambda message: print(message))

        # Start the worker thread
        thread.started.connect(worker.run_cycle)  # This starts the run_cycle method when the thread starts
        thread.start()  # Start the QThread itself

        print("Program Started")
    except Exception as e:
        print(f"Error running program: {e}")

def cleanup():
    global thread, worker

    try:
        print("[DEBUG] Starting cleanup process")

        # Ensure all relays are deactivated
        try:
            relay_handler.set_all_relays(0)
            print("[DEBUG] All relays deactivated")
        except Exception as e:
            print(f"[ERROR] Error deactivating relays: {e}")

        # Check if the worker still exists before trying to disconnect signals
        if worker is not None:
            try:
                worker.finished.disconnect()
                worker.progress.disconnect()
            except TypeError as e:
                print(f"[DEBUG] Error disconnecting signals (may already be disconnected): {e}")
            except RuntimeError as e:
                print(f"[DEBUG] Worker was already deleted or disconnected: {e}")

            worker = None  # Clear the worker reference

        # Stop and clear the thread
        if thread is not None and thread.isRunning():
            try:
                thread.quit()  # Gracefully exit the thread loop
                thread.wait()  # Block until the thread has fully finished execution
            except Exception as e:
                print(f"[ERROR] Error stopping thread: {e}")

        thread = None  # Explicitly set thread to None for reinitialization
        gui.run_stop_section.reset_ui()  # Reset the run_stop_section

        print("[DEBUG] Cleanup completed. Program ready for the next job.")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred during cleanup: {e}")

def stop_program():
    global thread, worker
    try:
        if worker:
            worker.stop()  # Request the worker to stop
        else:
            print("Worker is None in stop_program")

        # Wait for the worker to finish
        if thread and thread.isRunning():
            thread.quit()
            thread.wait()

        cleanup()

        print("Program Stopped")
    except Exception as e:
        print(f"Error stopping program: {e}")

def change_relay_hats():
    global relay_handler, settings

    # Prompt user for the number of relay hats
    num_hats, ok = QInputDialog.getInt(None, "Number of Relay Hats", "Enter the number of relay hats:", min=1, max=8)
    if not ok:
        return

    # Update the settings with the new number of relay hats
    settings['num_hats'] = num_hats
    settings['relay_pairs'] = create_relay_pairs(num_hats)

    # Update relay handler with the new relay pairs
    relay_handler.update_relay_hats(settings['relay_pairs'], num_hats)

    # Reinitialize the Projects Section
    gui.projects_section.populate_relays()

    # Reset the UI to ensure no lingering data or state
    cleanup()

    # Print confirmation
    gui.print_to_terminal(f"Relay hats updated to {num_hats} hats.")

def create_relay_pairs(num_hats):
    relay_pairs = []
    for hat in range(num_hats):
        start_relay = hat * 16 + 1
        for i in range(0, 16, 2):
            relay_pairs.append((start_relay + i, start_relay + i + 1))
    return relay_pairs

def main():
    app = QApplication(sys.argv)

    # Call the setup function to initialize everything before starting
    setup()

    # Initialize StreamRedirector and connect its signal to the GUI
    redirector = StreamRedirector()
    redirector.message_signal.connect(gui.system_message_signal)

    # Redirect stdout and stderr to the StreamRedirector
    sys.stdout = redirector
    sys.stderr = redirector

    gui.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()