import requests
import json
import datetime
import time
import threading
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os

LOG_FILE = "pump_log.json"

class NotificationHandler:
    def __init__(self, slack_token, channel_id):
        self.client = WebClient(token=slack_token)
        self.channel_id = channel_id

    def send_slack_notification(self, message):
        try:
            response = self.client.chat_postMessage(
                channel=self.channel_id,
                text=message
            )
            print(f"{datetime.datetime.now()} - Slack message sent successfully! Response: {response}")
        except SlackApiError as e:
            print(f"{datetime.datetime.now()} - Failed to send Slack message: {e.response['error']}")
            
            self.log_pump_trigger(message)

    def log_pump_trigger(self, relay_info):
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "relay_info": relay_info
        }

        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'w') as f:
                json.dump([], f)

        with open(LOG_FILE, 'r') as f:
            logs = json.load(f)

        logs.append(log_entry)

        with open(LOG_FILE, 'w') as f:
            json.dump(logs, f, indent=4)
        
        print(f"Logged pump trigger: {log_entry}")

    def is_internet_available(self):
        try:
            requests.get('http://google.com', timeout=5)
            return True
        except requests.ConnectionError:
            return False

    def retry_sending_logs(self):
        while True:
            if self.is_internet_available() and os.path.exists(LOG_FILE):
                with open(LOG_FILE, 'r') as f:
                    logs = json.load(f)

                for log in logs:
                    message = log["relay_info"]
                    try:
                        self.send_slack_notification(message)
                        logs.remove(log)
                    except SlackApiError:
                        break  # Stop retrying if sending fails

                with open(LOG_FILE, 'w') as f:
                    json.dump(logs, f, indent=4)

            time.sleep(60)  # Retry every minute

    def start_retry_thread(self):
        retry_thread = threading.Thread(target=self.retry_sending_logs)
        retry_thread.daemon = True  # Ensure thread exits when the main program does
        retry_thread.start()
