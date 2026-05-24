"""Tests for ``utils.slack_status`` — the Phase 3 indicator formatter.

Pure-logic unit tests; no Qt, no Slack SDK. Covers the icon classification
and the troubleshooting-hint mapping consumed by the GUI's Slack
indicator (Settings → General → Slack Integration).
"""

from __future__ import annotations

from utils.slack_status import format_status


# ---------------------------------------------------------------------------
# Three top-level icons: unknown / ok / warn
# ---------------------------------------------------------------------------

def test_none_is_unknown():
    icon, message = format_status(None)
    assert icon == "unknown"
    assert "no message has been sent yet" in message


def test_success_is_ok():
    icon, message = format_status(
        {"ok": True, "detail": "ok", "timestamp": "2026-05-22T14:03:12"}
    )
    assert icon == "ok"
    assert "14:03:12" in message
    assert "Delivered" in message


def test_failure_is_warn():
    icon, _ = format_status(
        {"ok": False, "detail": "boom", "timestamp": "2026-05-22T14:03:12"}
    )
    assert icon == "warn"


# ---------------------------------------------------------------------------
# Failure hints — actionable instructions per known Slack error code
# ---------------------------------------------------------------------------

def _hint_for(detail: str) -> str:
    _, message = format_status(
        {"ok": False, "detail": detail, "timestamp": "2026-05-22T14:03:12"}
    )
    return message


def test_token_revoked_hint_mentions_resetting_token():
    assert "fresh token" in _hint_for(
        "Slack rejected the message: token_revoked"
    )


def test_invalid_auth_hint_mentions_resetting_token():
    assert "fresh token" in _hint_for(
        "Slack rejected the message: invalid_auth"
    )


def test_not_authed_hint_mentions_resetting_token():
    assert "fresh token" in _hint_for(
        "Slack rejected the message: not_authed"
    )


def test_channel_not_found_hint_mentions_channel_id():
    hint = _hint_for("Slack rejected the message: channel_not_found")
    assert "Channel ID" in hint
    assert "invited" in hint


def test_archived_channel_hint_mentions_channel_id():
    assert "Channel ID" in _hint_for(
        "Slack rejected the message: is_archived"
    )


def test_missing_scope_hint_mentions_scope():
    assert "chat:write" in _hint_for(
        "Slack rejected the message: missing_scope"
    )


def test_rate_limited_hint_says_resumes_automatically():
    assert "rate-limit" in _hint_for(
        "Slack rejected the message: ratelimited"
    ).lower()


def test_network_failure_hint_explains_offline_fallback():
    hint = _hint_for("Network failure (ConnectionError)")
    assert "no internet" in hint.lower()
    assert "logged locally" in hint


def test_timeout_hint_explains_offline_fallback():
    assert "logged locally" in _hint_for("Network failure (Timeout)")


def test_unknown_failure_lists_general_causes():
    hint = _hint_for("Slack rejected the message: some_new_error_code")
    assert "Possible causes" in hint


# ---------------------------------------------------------------------------
# Timestamp parsing
# ---------------------------------------------------------------------------

def test_timestamp_is_trimmed_to_hh_mm_ss():
    _, message = format_status(
        {"ok": True, "detail": "ok",
         "timestamp": "2026-05-22T14:03:12.987654"}
    )
    assert "14:03:12" in message
    assert "987654" not in message


def test_missing_timestamp_says_unknown():
    _, message = format_status({"ok": True, "detail": "ok"})
    assert "unknown" in message


def test_malformed_timestamp_falls_back_to_raw_value():
    _, message = format_status(
        {"ok": True, "detail": "ok", "timestamp": "not-an-iso-timestamp"}
    )
    assert "not-an-iso-timestamp" in message
