import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import threading
import time
from gpio.mock_gpio_handler import MockRelayHandler
from notifications.notifications import NotificationHandler
from settings.config import load_settings
from ui.gui import RodentRefreshmentGUI

def test_script():
    settings = load_settings()

    relay_handler = MockRelayHandler(settings['relay_pairs'])
    notification_handler = NotificationHandler(settings['slack_token'], settings['channel_id'])

    def run_program():
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
                    relay_info = relay_handler.trigger_relays(settings['selected_relays'], settings['num_triggers'], settings['stagger'])
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
                    if notification_handler.is_internet_available():
                        notification_handler.send_slack_notification(message)
                    else:
                        notification_handler.log_pump_trigger(message)
                    time.sleep(settings['interval'] - 1)

    def update_all_settings():
        global INTERVAL, STAGGER, WINDOW_START, WINDOW_END, num_triggers, selected_relays
        INTERVAL, STAGGER, WINDOW_START, WINDOW_END, selected_relays, num_triggers = gui.get_settings()
        print("Settings updated")

    gui = RodentRefreshmentGUI(run_program, stop_program, update_all_settings)
    gui.run()

if __name__ == "__main__":
    test_script()
