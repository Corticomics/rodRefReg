import sys
import os
from PyQt5.QtWidgets import QApplication, QInputDialog
from PyQt5.QtCore import QTimer
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

def run_program(interval, stagger, window_start, window_end):
    try:
        print(f"Running program with interval: {interval}, stagger: {stagger}, window_start: {window_start}, window_end: {window_end}")
        
        # Ensure settings are properly structured
        advanced_settings = gui.advanced_settings.get_settings()
        # Ensure all keys are strings
        advanced_settings['num_triggers'] = {str(k): v for k, v in advanced_settings['num_triggers'].items()}
        settings.update(advanced_settings)

        # Set up QTimer to handle the relay triggering
        gui.timer = QTimer()
        gui.timer.timeout.connect(lambda: program_step(settings))
        gui.timer.start(interval * 1000)  # interval is in seconds, QTimer needs milliseconds

        print("Program Started")
    except Exception as e:
        print(f"Error running program2: {e}")

def stop_program():
    if hasattr(gui, 'timer'):
        gui.timer.stop()  # Stop the QTimer when the program is stopped
    relay_handler.set_all_relays(0)
    print("Program Stopped")

def program_step(settings):
    try:
        current_time = int(time.time())
        if settings['window_start'] <= current_time <= settings['window_end']:
            for relay_pair_str, triggers in settings['num_triggers'].items():
                relay_pair = eval(relay_pair_str)  # Convert the string back to a tuple
                relay_info = relay_handler.trigger_relays([relay_pair], triggers, settings['stagger'])
                print(f"Triggered {relay_pair} {triggers} times. Relay info: {relay_info}")
                # Add any logging or notifications here
    except Exception as e:
        print(f"An error occurred in program_step: {e}")
        stop_program()


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
