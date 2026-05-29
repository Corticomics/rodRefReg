"""Classify an update-apply failure message into a UI category.

Phase 3 of the offline-resilience plan. The classifier is intentionally
free of Qt imports so it can be unit-tested without the GUI stack; the
``UpdatesTab`` widget maps the returned code to a ``QMessageBox`` title
and icon at render time.
"""

from __future__ import annotations

# Category codes — the GUI's single render-side decision is mapping these
# to a (title, icon) pair. The stable set keeps the contract small.
INTERNET = "internet"  # bundle could not be downloaded
VERIFY = "verify"  # checksum unfetchable or mismatched
GENERIC = "generic"  # everything else (busy schedule, disk full, ...)


def classify_failure(message: str | None) -> str:
    """Return one of ``INTERNET`` / ``VERIFY`` / ``GENERIC`` for ``message``.

    Driven by the failure-message vocabulary that ``utils.updater.apply_update``
    emits (Phase 2): "Could not download the update (...) Updates require an
    internet connection ..." → ``INTERNET``; anything with "verif"/"checksum"
    → ``VERIFY``; otherwise ``GENERIC``.
    """
    low = (message or "").lower()
    if "internet" in low or "could not download" in low:
        return INTERNET
    if "verify" in low or "checksum" in low:
        return VERIFY
    return GENERIC
