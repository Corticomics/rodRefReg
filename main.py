import sys
import os
from PyQt5.QtWidgets import QApplication, QInputDialog
from PyQt5.QtCore import QTimer, QThread
from gpio.relay_worker import RelayWorker
from ui.gui import RodentRefreshmentGUI
from gpio.gpio_handler import RelayHandler
from notifications.notifications import NotificationHandler
from settings.config import load_settings, save_settings
import time

class StreamRedirector:
    def __init__(self, print_func):
        self.print_func = print_func

    def write(self, message):
        if message.strip():  # ignore empty messages
            self.print_func(message)

    def flush(self):
        pass

# Initialize thread and worker globally to reuse them
thread = QThread()
worker = None

def setup():
    global relay_handler, settings, gui, notification_handler

    # Prompt user for the number of relay hats
    num_hats, ok = QInputDialog.getInt(None, "Number of Relay Hats", "Enter the number of relay hats:", min=1, max=8)
    if not ok:
        sys.exit()

    # Load settings and initialize relays
    settings = load_settings()
    settings['num_hats'] = num_hats
    settings['relay_pairs'] = create_relay_pairs(num_hats)
    
    # Initialize relay handler and close all relays
    relay_handler = RelayHandler(settings['relay_pairs'], num_hats)
    relay_handler.set_all_relays(0)  # Ensure all relays are closed during setup

    # Initialize Slack notification handler
    notification_handler = NotificationHandler(settings['slack_token'], settings['channel_id'])

    # Initialize GUI components
    gui = RodentRefreshmentGUI(run_program, stop_program, change_relay_hats, settings)


def run_program(interval, stagger, window_start, window_end):
    global thread, worker  # Reuse these globally

    try:
        print(f"Running program with interval: {interval}, stagger: {stagger}, window_start: {window_start}, window_end: {window_end}")

        # Ensure settings are properly structured
        advanced_settings = gui.advanced_settings.get_settings()
        advanced_settings['num_triggers'] = {str(k): v for k, v in advanced_settings['num_triggers'].items()}
        settings.update(advanced_settings)

        # Reinitialize the thread and worker
        if thread is not None:
            thread.quit()
            thread.wait()
        thread = QThread()

        worker = RelayWorker(settings, relay_handler, notification_handler)
        worker.moveToThread(thread)

        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(cleanup)
        thread.finished.connect(thread.deleteLater)

        worker.progress.connect(lambda message: print(message))

        thread.start()

        # Set up QTimer to handle the relay triggering with proper intervals
        if not hasattr(gui, 'timer') or gui.timer is None:
            gui.timer = QTimer()
            gui.timer.timeout.connect(lambda: worker.run_cycle())  # Call run_cycle to handle one cycle
            gui.timer.start(interval * 1000)  # interval is in seconds, QTimer needs milliseconds

        print("Program Started")
    except Exception as e:
        print(f"Error running program1: {e}")




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
        gui.timer = None  # Clear the timer reference

        # Reset the GUI buttons and state
        gui.run_stop_section.job_in_progress = False
        gui.run_stop_section.update_button_states()

        print("[DEBUG] Cleanup completed. Program ready for the next job.")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred during cleanup: {e}")








def stop_program():
    global thread, worker
    try:
        if hasattr(gui, 'timer'):
            gui.timer.stop()  # Stop the QTimer when the program is stopped

        if worker:
            worker.stop()  # Request the worker to stop

        cleanup()

        print("Program Stopped")
    except Exception as e:
        print(f"Error stopping program: {e}")




def create_relay_pairs(num_hats):
    relay_pairs = []
    for hat in range(num_hats):
        start_relay = hat * 16 + 1
        for i in range(0, 16, 2):
            relay_pairs.append((start_relay + i, start_relay + i + 1))
    return relay_pairs

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
    
    # Reinitialize the advanced settings UI
    gui.reinitialize_advanced_settings()

    # Print confirmation
    gui.print_to_terminal(f"Relay hats updated to {num_hats} hats.")


def main():
    app = QApplication(sys.argv)
    
    # Call the setup function to initialize everything before starting
    setup()

    # Redirect stdout and stderr to the terminal output widget
    sys.stdout = StreamRedirector(gui.print_to_terminal)
    sys.stderr = StreamRedirector(gui.print_to_terminal)
    
    gui.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
