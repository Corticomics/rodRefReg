import sys
import os
from PyQt5.QtWidgets import QApplication, QInputDialog
from ui.gui import RodentRefreshmentGUI
from gpio.gpio_handler import RelayHandler
from notifications.notifications import NotificationHandler
from settings.config import load_settings, save_settings
import threading
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
    print(f"Running program with interval: {interval}, stagger: {stagger}, window_start: {window_start}, window_end: {window_end}")
    
    # Update settings
    settings['interval'] = interval
    settings['stagger'] = stagger
    settings['window_start'] = window_start
    settings['window_end'] = window_end
    
    # Update relay settings from AdvancedSettingsSection
    advanced_settings = gui.advanced_settings.get_settings()
    settings.update(advanced_settings)

    save_settings(settings)  # Save the settings
    
    global running
    running = True
    global stop_requested
    stop_requested = False
    threading.Thread(target=program_loop).start()
    print("Program Started")

def stop_program():
    global running
    global stop_requested
    stop_requested = True
    running = False
    relay_handler.set_all_relays(0)
    print("Program Stopped")

def change_relay_hats():
    num_hats, ok = QInputDialog.getInt(None, "Number of Relay Hats", "Enter the number of relay hats:", min=1, max=8)
    if not ok:
        return
    settings['num_hats'] = num_hats
    settings['relay_pairs'] = create_relay_pairs(num_hats)
    relay_handler.update_relay_hats(settings['relay_pairs'], num_hats)
    gui.advanced_settings.update_relay_hats(settings['relay_pairs'])

def program_loop():
    global running
    while running:
        if stop_requested:
            print("Immediate stop requested.")
            break
        current_time = time.time()
        if settings['window_start'] <= current_time <= settings['window_end']:
            if current_time % settings['interval'] < 1:
                print(f"Triggering relays at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time))}")
                selected_relays = [eval(k) for k in settings['selected_relays']]  # Convert string keys back to tuples
                relay_info = relay_handler.trigger_relays(selected_relays, settings['num_triggers'], settings['stagger'])
                if stop_requested:
                    print("Immediate stop requested during relay triggering.")
                    break
                print(f"Relay info: {relay_info}")
                message = (
                    f"The pumps have been successfully triggered as follows:\n"
                    f"{'; '.join(relay_info)}\n"
                    f"** Next trigger due in {settings['interval']} seconds.\n\n"
                    f"Current settings:\n"
                    f"- Interval: {settings['interval']} seconds\n"
                    f"- Stagger: {settings['stagger']} seconds\n"
                    f"- Water window: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(settings['window_start']))} - {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(settings['window_end']))}\n"
                    f"- Relays enabled: {', '.join(f'({rp[0]} & {rp[1]})' for rp in selected_relays) if selected_relays else 'None'}"
                )
                if notification_handler.is_internet_available():
                    notification_handler.send_slack_notification(message)
                else:
                    notification_handler.log_pump_trigger(message)
                time.sleep(settings['interval'] - 1)

def main():
    app = QApplication(sys.argv)
    
    num_hats, ok = QInputDialog.getInt(None, "Number of Relay Hats", "Enter the number of relay hats:", min=1, max=8)
    if not ok:
        sys.exit()
    
    global settings
    settings = load_settings()
    settings['num_hats'] = num_hats  # Update settings with the number of hats
    settings['relay_pairs'] = create_relay_pairs(num_hats)  # Create relay pairs based on the number of hats
    
    relay_handler = RelayHandler(settings['relay_pairs'], settings['num_hats'])
    notification_handler = NotificationHandler(settings['slack_token'], settings['channel_id'])

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

if __name__ == "__main__":
    main()
