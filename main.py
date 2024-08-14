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

def run_program(interval, stagger, window_start, window_end):
    global thread, worker  # Reuse these globally
    try:
        print(f"Running program with interval: {interval}, stagger: {stagger}, window_start: {window_start}, window_end: {window_end}")

        # Ensure settings are properly structured
        advanced_settings = gui.advanced_settings.get_settings()
        # Ensure all keys are strings
        advanced_settings['num_triggers'] = {str(k): v for k, v in advanced_settings['num_triggers'].items()}
        settings.update(advanced_settings)

        if worker is None:
            # Create a worker object and move it to the thread
            worker = RelayWorker(settings, relay_handler)
            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            worker.finished.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            worker.progress.connect(lambda message: print(message))
            thread.start()

        # Set up QTimer to handle the relay triggering without creating new threads
        if not hasattr(gui, 'timer') or gui.timer is None:
            gui.timer = QTimer()
            gui.timer.timeout.connect(lambda: worker.run())  # Reuse the same worker
            gui.timer.start(interval * 1000)  # interval is in seconds, QTimer needs milliseconds

        print("Program Started")
    except Exception as e:
        print(f"Error running program: {e}")

def stop_program():
    global thread, worker
    try:
        if hasattr(gui, 'timer'):
            gui.timer.stop()  # Stop the QTimer when the program is stopped

        # Safely stop the worker and thread
        if worker:
            worker.stop()  # Request the worker to stop
        if thread and thread.isRunning():
            thread.quit()  # Gracefully exit the thread loop
            thread.wait()  # Block until the thread has fully finished execution

        # After stopping, clean up references to avoid dangling objects
        worker = None
        gui.timer = None
        
        relay_handler.set_all_relays(0)
        print("Program Stopped")
    except Exception as e:
        print(f"Error stopping program: {e}")

def main():
    app = QApplication(sys.argv)
    
    num_hats, ok = QInputDialog.getInt(None, "Number of Relay Hats", "Enter the number of relay hats:", min=1, max=8)
    if not ok:
        sys.exit()
    
    global settings
    settings = load_settings()
    settings['num_hats'] = num_hats  # Update settings with the number of hats
    settings['relay_pairs'] = create_relay_pairs(num_hats)  # Create relay pairs based on the number of hats
    
    global relay_handler
    relay_handler = RelayHandler(settings['relay_pairs'], settings['num_hats'])
    global notification_handler
    notification_handler = NotificationHandler(settings['slack_token'], settings['channel_id'])

    global gui
    gui = RodentRefreshmentGUI(run_program, stop_program, change_relay_hats, settings)

    # Redirect stdout and stderr to the terminal output widget
    sys.stdout = StreamRedirector(gui.print_to_terminal)
    sys.stderr = StreamRedirector(gui.print_to_terminal)
    
    gui.show()
    sys.exit(app.exec_())

def create_relay_pairs(num_hats):
    relay_pairs = []
    for hat in range(num_hats):
        start_relay = hat * 16 + 1
        for i in range(0, 16, 2):
            relay_pairs.append((start_relay + i, start_relay + i + 1))
    return relay_pairs

def change_relay_hats():
    num_hats, ok = QInputDialog.getInt(None, "Number of Relay Hats", "Enter the number of relay hats:", min=1, max=8)
    if not ok:
        return
    settings['num_hats'] = num_hats
    settings['relay_pairs'] = create_relay_pairs(num_hats)
    relay_handler.update_relay_hats(settings['relay_pairs'], num_hats)
    gui.advanced_settings.update_relay_hats(settings['relay_pairs'])

if __name__ == "__main__":
    main()