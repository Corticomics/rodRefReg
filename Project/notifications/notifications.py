"""Slack notifications for RRR.

A delivery to live animals must never be disrupted by a Slack or network
failure. This module enforces that contract:

* the ``WebClient`` is constructed with an explicit short timeout so a
  stalled connection cannot block the relay-worker thread that calls in
  here from the schedule hot path;
* every failure mode (API rejection, connection refused, DNS failure,
  timeout, unexpected exception) is caught, recorded, and the message is
  appended to a local file (``pump_log.json``) so no trigger is ever
  lost;
* the most recent outcome is stored on ``self.last_status`` so the GUI's
  Slack indicator (Phase 3) can surface "ok" / "Slack token revoked" /
  "network unreachable" with actionable detail — instead of forcing the
  operator to read ``stdout`` to know what happened.

Phase 2 of the offline-resilience plan.
"""

import datetime
import json
import os

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from utils import paths

# Local fallback log: every relay trigger we couldn't tell Slack about is
# appended here so the operator can reconcile after the fact.
LOG_FILE = paths.pump_log_path()

# Bounded wall-clock budget for a single Slack call. Short on purpose: the
# relay worker calls in here from the hot path of schedule execution.
_SLACK_TIMEOUT_S = 10


class NotificationHandler:
    """Send delivery/error messages to Slack with a durable local fallback."""

    def __init__(self, slack_token, channel_id):
        # Explicit timeout protects the relay worker — see module docstring.
        self.client = WebClient(token=slack_token, timeout=_SLACK_TIMEOUT_S)
        self.channel_id = channel_id
        # Last delivery outcome, consumed by the Phase 3 GUI indicator.
        # Format: {"ok": bool, "detail": str, "timestamp": iso8601}.
        self.last_status = None

    def send_slack_notification(self, message):
        """Send ``message`` to Slack; on any failure, log it locally instead.

        Must never raise into the caller — the relay worker depends on it.
        """
        try:
            self.client.chat_postMessage(channel=self.channel_id, text=message)
        except SlackApiError as exc:
            err = "unknown"
            try:
                err = exc.response["error"]
            except Exception:
                pass
            print(f"{datetime.datetime.now()} - Slack API error: {err}")
            self._record_status(False, f"Slack rejected the message: {err}")
            self.log_pump_trigger(message)
        except Exception as exc:
            # Connection refused, DNS failure, timeout, urllib errors, etc.
            # Whatever the Slack SDK raised on a network failure, we treat
            # it as "Slack unreachable" and fall back to the local log.
            print(
                f"{datetime.datetime.now()} - Slack network failure: "
                f"{exc.__class__.__name__}: {exc}"
            )
            self._record_status(False, f"Network failure ({exc.__class__.__name__})")
            self.log_pump_trigger(message)
        else:
            self._record_status(True, "ok")

    def log_pump_trigger(self, relay_info):
        """Append a trigger to ``pump_log.json`` so it survives an outage."""
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "relay_info": relay_info,
        }
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, "w") as f:
                json.dump([], f)
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)
        logs.append(log_entry)
        with open(LOG_FILE, "w") as f:
            json.dump(logs, f, indent=4)
        print(f"Logged pump trigger: {log_entry}")

    def _record_status(self, ok, detail):
        """Update ``last_status`` for the GUI's Slack indicator."""
        self.last_status = {
            "ok": bool(ok),
            "detail": detail,
            "timestamp": datetime.datetime.now().isoformat(),
        }
