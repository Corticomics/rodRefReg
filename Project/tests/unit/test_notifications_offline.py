"""Characterization tests: Slack notifications when the network is down.

Phase 1 of the offline-resilience work. These tests do **not** change
behaviour — they pin down what the code does *today* so Phase 2 can harden
the internals (explicit Slack timeout, broader failure handling) without
regressing the offline fallback that lab deployments rely on.

Why this matters: ``NotificationHandler.send_slack_notification`` runs on the
relay-worker hot path (``gpio/relay_worker.py``, ``schedule_controller.py``).
A delivery to live animals must never be disrupted by a Slack/network
failure.

Two of these tests are **strict xfail canaries**: they assert the *desired*
Phase 2 behaviour and currently fail. When Phase 2 lands, they flip to
passing and the strict marker forces removal of the ``xfail`` — so the canary
cannot rot.
"""

from __future__ import annotations

import json

import pytest

# Skip cleanly on a machine without the runtime deps (CI installs both).
pytest.importorskip("requests")
pytest.importorskip("slack_sdk")


@pytest.fixture
def handler(monkeypatch, tmp_path):
    """A ``NotificationHandler`` whose offline pump log points at a tmp file.

    Returns ``(handler, log_path)``. No real Slack token, no network.
    """
    import notifications.notifications as notif

    log_path = tmp_path / "pump_log.json"
    monkeypatch.setattr(notif, "LOG_FILE", str(log_path))
    return notif.NotificationHandler("xoxb-not-a-real-token", "C0000000"), log_path


def _slack_api_error(error_code: str):
    """Build a ``SlackApiError`` the way the Slack SDK does for an API reply."""
    from slack_sdk.errors import SlackApiError

    return SlackApiError(f"slack returned {error_code}", {"error": error_code})


# ---------------------------------------------------------------------------
# Current behaviour — locked in
# ---------------------------------------------------------------------------

def test_slack_api_error_falls_back_to_local_log(handler, monkeypatch):
    """An API-level failure (e.g. revoked token) logs the message locally."""
    handler_obj, log_path = handler

    def _raise(*_a, **_k):
        raise _slack_api_error("token_revoked")

    monkeypatch.setattr(handler_obj.client, "chat_postMessage", _raise)
    handler_obj.send_slack_notification("relay unit 3 triggered")

    assert log_path.exists(), "pump trigger must be logged when Slack fails"
    entries = json.loads(log_path.read_text())
    assert len(entries) == 1
    assert entries[0]["relay_info"] == "relay unit 3 triggered"
    assert "timestamp" in entries[0]


def test_slack_api_error_does_not_propagate(handler, monkeypatch):
    """A Slack API failure must never raise into the relay worker."""
    handler_obj, _ = handler
    monkeypatch.setattr(
        handler_obj.client, "chat_postMessage",
        lambda *_a, **_k: (_ for _ in ()).throw(_slack_api_error("not_authed")),
    )
    # Must return normally — no exception reaches the caller.
    handler_obj.send_slack_notification("delivery complete")


def test_repeated_failures_accumulate_in_the_log(handler, monkeypatch):
    """Each failed notification appends; the local log is the durable record."""
    handler_obj, log_path = handler
    monkeypatch.setattr(
        handler_obj.client, "chat_postMessage",
        lambda *_a, **_k: (_ for _ in ()).throw(_slack_api_error("channel_not_found")),
    )
    for i in range(3):
        handler_obj.send_slack_notification(f"trigger {i}")

    entries = json.loads(log_path.read_text())
    assert [e["relay_info"] for e in entries] == ["trigger 0", "trigger 1", "trigger 2"]


# ---------------------------------------------------------------------------
# Strict xfail canaries — assert the Phase 2 target behaviour
# ---------------------------------------------------------------------------

def test_network_level_failure_also_falls_back(handler, monkeypatch):
    """Offline Slack calls fail with connection errors, not SlackApiError.

    Phase 2 broadened the failure handler to catch ``Exception`` so any
    network-level failure (the real offline symptom) is logged locally —
    a connection error must never raise into the relay worker.
    """
    handler_obj, log_path = handler

    def _raise(*_a, **_k):
        raise ConnectionError("network is unreachable")

    monkeypatch.setattr(handler_obj.client, "chat_postMessage", _raise)
    handler_obj.send_slack_notification("trigger during outage")  # must not raise

    assert log_path.exists()
    assert json.loads(log_path.read_text())[0]["relay_info"] == "trigger during outage"


def test_webclient_is_constructed_with_an_explicit_timeout(handler):
    """The Slack client must carry a bounded timeout to protect the hot path.

    Phase 2 sets an explicit ``timeout=10`` on the ``WebClient``; a stalled
    connection cannot block the relay-worker thread.
    """
    handler_obj, _ = handler
    timeout = getattr(handler_obj.client, "timeout", None)
    assert isinstance(timeout, (int, float)) and timeout <= 15


# ---------------------------------------------------------------------------
# last_status — Phase 2 recorder consumed by the GUI Slack indicator
# ---------------------------------------------------------------------------

def test_last_status_is_none_before_any_send(handler):
    handler_obj, _ = handler
    assert handler_obj.last_status is None


def test_last_status_records_success(handler, monkeypatch):
    handler_obj, _ = handler
    monkeypatch.setattr(handler_obj.client, "chat_postMessage",
                        lambda *_a, **_k: {"ok": True})
    handler_obj.send_slack_notification("delivery complete")

    status = handler_obj.last_status
    assert status is not None
    assert status["ok"] is True
    assert "timestamp" in status


def test_last_status_records_api_failure_with_error_code(handler, monkeypatch):
    handler_obj, _ = handler
    monkeypatch.setattr(
        handler_obj.client, "chat_postMessage",
        lambda *_a, **_k: (_ for _ in ()).throw(_slack_api_error("token_revoked")),
    )
    handler_obj.send_slack_notification("msg")

    status = handler_obj.last_status
    assert status["ok"] is False
    assert "token_revoked" in status["detail"]


def test_last_status_records_network_failure(handler, monkeypatch):
    handler_obj, _ = handler

    def _raise(*_a, **_k):
        raise ConnectionError("offline")

    monkeypatch.setattr(handler_obj.client, "chat_postMessage", _raise)
    handler_obj.send_slack_notification("msg")

    status = handler_obj.last_status
    assert status["ok"] is False
    assert "ConnectionError" in status["detail"] or "Network" in status["detail"]
