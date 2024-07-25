import sys
import os
from PyQt5.QtWidgets import QApplication
from ui.gui import RodentRefreshmentGUI
from gpio.gpio_handler import RelayHandler
from notifications.notifications import NotificationHandler
from settings.config import load_settings
import threading
import time

def main():
    app = QApplication(sys.argv)
    settings = load_settings()

    relay_handler = RelayHandler(settings['relay_pairs'], settings['num_hats'])
    notification_handler = NotificationHandler(settings['slack_token'], settings['channel_id'])

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

    def program_loop():
        global running
        while running:
            current_hour = time.localtime().tm_hour
            if (settings['window_start'] <= current_hour < 24) or (0 <= current_hour < settings['window_end']) if settings['window_start'] > settings['window_end'] else (settings['window_start'] <= current_hour < settings['window_end']):
                current_time = time.time()
                if current_time % settings['interval'] < 1:
                    print(f"Triggering relays at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time))}")
                    relay_info = relay_handler.trigger_relays(settings['selected_relays'], settings['num_triggers'], settings['stagger'])
                    print(f"Relay info: {relay_info}")
                    message = (
                        f"The pumps have been successfully triggered as follows:\n"
                        f"{'; '.join(relay_info)}\n"
                        f"** Next trigger due in {settings['interval']} seconds.\n\n"
                        f"Current settings:\n"
                        f"- Interval: {settings['interval']} seconds\n"
                        f"- Stagger: {settings['stagger']} seconds\n"
                        f"- Water window: {settings['window_start']:02d}:00 - {settings['window_end']:02d}:00\n"
                        f"- Relays enabled: {', '.join(f'({rp[0]} & {rp[1]})' for rp in settings['selected_relays']) if settings['selected_relays'] else 'None'}"
                    )
                    notification_handler.send_slack_notification(message)
                    time.sleep(settings['interval'] - 1)

    def update_all_settings():
        new_settings = gui.get_settings()
        settings.update(new_settings)
        print("Settings updated")

    def change_relay_hats():
        num_hats, ok = QInputDialog.getInt(None, "Number of Relay Hats", "Enter the number of relay hats:", min=1, max=8)
        if not ok:
            return

        settings['num_hats'] = num_hats
        settings['relay_pairs'] = create_relay_pairs(num_hats)

        relay_handler.update_relay_hats(settings['relay_pairs'], num_hats)
        gui.advanced_settings.update_relay_checkboxes(settings['relay_pairs'])

    gui = RodentRefreshmentGUI(run_program, stop_program, update_all_settings, change_relay_hats, settings)
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
"""Traceback (most recent call last):
  File "/home/conelab/Documents/GitHub/rodRefReg/main.py", line 87, in <module>
    main()
  File "/home/conelab/Documents/GitHub/rodRefReg/main.py", line 74, in main
    gui = RodentRefreshmentGUI(run_program, stop_program, update_all_settings, change_relay_hats, settings)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/conelab/Documents/GitHub/rodRefReg/ui/gui.py", line 29, in __init__
    self.init_ui(style)
  File "/home/conelab/Documents/GitHub/rodRefReg/ui/gui.py", line 76, in init_ui
    self.advanced_settings = AdvancedSettingsSection(self.settings, self.update_all_settings, self.print_to_terminal)
                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/conelab/Documents/GitHub/rodRefReg/ui/advanced_settings.py", line 16, in __init__
    self.update_relay_checkboxes(self.settings['relay_pairs'])
  File "/home/conelab/Documents/GitHub/rodRefReg/ui/advanced_settings.py", line 35, in update_relay_checkboxes
    layout = self.layout().itemAt(0).widget().layout()
             ^^^^^^^^^^^^^^^^^^^^
AttributeError: 'NoneType' object has no attribute 'itemAt'
"""