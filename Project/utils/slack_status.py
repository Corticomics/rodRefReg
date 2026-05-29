"""Format ``NotificationHandler.last_status`` into a user-facing message.

Powers the **Settings → General → Slack Integration** indicator added in
Phase 3 of the offline-resilience plan. Kept as pure functions so the
copy and the failure-to-hint mapping are unit-testable without bringing
up Qt.

The input is the ``last_status`` recorder from
``notifications.notifications.NotificationHandler`` (Phase 2):

    None                                          # before any send attempt
    {"ok": True,  "detail": "ok",            "timestamp": "2026-05-22T14:03:12"}
    {"ok": False, "detail": "Slack rejected the message: token_revoked",
                                              "timestamp": "..."}
    {"ok": False, "detail": "Network failure (ConnectionError)",
                                              "timestamp": "..."}

:func:`format_status` returns ``(icon, message)``; the GUI maps ``icon``
to its own glyph/colour.
"""

from __future__ import annotations

# Public icon vocabulary — kept short on purpose so the GUI's mapping
# (glyph, colour) is the single render-side decision.
_OK = "ok"
_WARN = "warn"
_UNKNOWN = "unknown"


def format_status(last_status: dict | None) -> tuple[str, str]:
    """Return ``(icon, message)`` for ``last_status``.

    ``icon`` is one of ``"ok"`` / ``"warn"`` / ``"unknown"``. ``message``
    is operator-readable and, on failure, includes actionable
    troubleshooting steps.
    """
    if last_status is None:
        return _UNKNOWN, (
            "Status unknown — no message has been sent yet. The status "
            "appears here after the first delivery notification or program "
            "error."
        )

    when = _short_time(last_status.get("timestamp"))
    if last_status.get("ok"):
        return _OK, f"Delivered at {when}."

    detail = (last_status.get("detail") or "").strip()
    hint = _troubleshooting(detail)
    return _WARN, f"Failed at {when}: {detail}\n{hint}"


def _short_time(iso: str | None) -> str:
    """Return the time portion of an ISO timestamp, or ``"unknown"``."""
    if not iso:
        return "unknown"
    try:
        # ISO 8601: YYYY-MM-DDTHH:MM:SS[.ffffff] — trim subseconds.
        return iso.split("T", 1)[1].split(".", 1)[0]
    except Exception:
        return iso


def _troubleshooting(detail: str) -> str:
    """Map a failure detail to operator-actionable instructions."""
    low = detail.lower()

    if any(
        code in low for code in ("token_revoked", "invalid_auth", "not_authed", "account_inactive")
    ):
        return (
            "Slack rejected the bot token. Re-create the Slack app/bot, "
            "paste a fresh token above, and click Save."
        )

    if any(code in low for code in ("channel_not_found", "is_archived", "not_in_channel")):
        return (
            "The channel ID does not exist, the channel is archived, or "
            "the bot is not a member. Check the Channel ID above and that "
            "the bot has been invited to that channel."
        )

    if "missing_scope" in low:
        return (
            "The bot is missing the chat:write scope. Update the Slack "
            "app's OAuth scopes, then reinstall it to your workspace."
        )

    if "ratelimited" in low or "rate_limited" in low:
        return (
            "Slack is rate-limiting this bot. Notifications resume "
            "automatically; the delivery has been logged locally."
        )

    if any(word in low for word in ("network", "connection", "timeout", "dns", "unreachable")):
        return (
            "Could not reach Slack — this device has no internet, or the "
            "Slack service is unreachable. Notifications resume "
            "automatically when the network is back; deliveries are logged "
            "locally in the meantime."
        )

    return (
        "Possible causes: revoked token, deleted or renamed channel, "
        "missing bot scope, or no internet. Check the values above and "
        "this device's network."
    )
