"""Update notification entry point.

Single responsibility: on launch, ask GitHub whether a newer release
exists. If so, the GUI shows a dismissable banner; an offline device
silently gets no banner. See docs/UPDATE_SYSTEM.md.

main.py calls :meth:`UpdateNotifier.check_for_updates` with the main
window after the GUI is created.

The pre-update-system "UI Improvements Applied" dialog driven by a
local ``ui_updated.json`` file was removed in v1.7.4 — confirmed
unused on the deployed fleet.
"""

from utils.updater import run_check


class UpdateNotifier:
    """Thin entry point for the GitHub release update check."""

    @classmethod
    def check_for_updates(cls, gui):
        """Start a background GitHub release check.

        If a newer version exists, ``gui`` shows an update banner via
        its ``_on_update_check_result`` callback. An offline device
        silently gets no banner. Update checks must never interfere
        with app startup, so all failures are swallowed.
        """
        try:
            run_check(gui, gui._on_update_check_result)
        except Exception:
            pass
