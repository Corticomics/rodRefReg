"""Tests for the Phase 3 update-failure classifier.

The classifier picks the dialog title/icon shown by ``UpdatesTab`` when
an apply fails. It is intentionally Qt-free; the ``UpdatesTab`` widget
maps the returned code to a ``QMessageBox`` constant at render time.
"""

from __future__ import annotations

from utils.update_failure import INTERNET, VERIFY, GENERIC, classify_failure


def test_no_internet_message_is_classified_as_internet():
    assert classify_failure(
        "Could not download the update (download failed: "
        "ConnectionError(...)). Updates require an internet connection."
    ) == INTERNET


def test_checksum_unreachable_message_is_classified_as_verify():
    assert classify_failure(
        "Could not verify the update — the checksum file is unreachable."
    ) == VERIFY


def test_checksum_mismatch_message_is_classified_as_verify():
    assert classify_failure(
        "Download verification failed (checksum mismatch)."
    ) == VERIFY


def test_busy_schedule_message_is_classified_as_generic():
    assert classify_failure(
        "A delivery schedule is running. Stop it before installing an update."
    ) == GENERIC


def test_empty_message_is_classified_as_generic():
    assert classify_failure("") == GENERIC
    assert classify_failure(None) == GENERIC
