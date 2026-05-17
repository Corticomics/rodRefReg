"""Update notifications.

Two things live here:

1. The startup *update check* (Phase 1 of the update system) — on launch it
   asks GitHub whether a newer release exists and, if so, shows a dismissable
   banner on the main window. See docs/UPDATE_SYSTEM.md.

2. A legacy local "UI Improvements Applied" dialog driven by a ``ui_updated.json``
   file. This predates the update system; it is kept for backward
   compatibility and is a candidate for removal once unused.

main.py calls :meth:`UpdateNotifier.check_for_updates` (with the main window)
after the GUI is created.
"""

import os
import json

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QScrollArea, QWidget
)

from utils.updater import run_check


class UpdateNotifier:
    """Update notifications: GitHub release check + legacy local changelog."""

    @classmethod
    def check_for_updates(cls, gui=None):
        """Run update checks. Safe to call unconditionally.

        - Always runs the legacy local-changelog check.
        - When ``gui`` is given, also starts a background GitHub release
          check; if a newer version exists, ``gui`` shows an update banner.
          An offline device silently gets no banner.
        """
        cls._check_local_changelog()

        if gui is None:
            return
        try:
            run_check(gui, gui._on_update_check_result)
        except Exception:
            # An update check must never interfere with app startup.
            pass

    # ------------------------------------------------------------------
    # Legacy: local "UI Improvements Applied" dialog (pre-update-system).
    # ------------------------------------------------------------------
    @classmethod
    def _check_local_changelog(cls):
        """Show the legacy changelog dialog if ui_updated.json flags an update."""
        update_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'ui_updated.json'
        )
        if not os.path.exists(update_file):
            return

        try:
            with open(update_file, 'r') as f:
                update_data = json.load(f)

            if update_data.get('updated', False):
                cls.show_update_notification(update_data)

                # Reset the flag so the dialog shows only once.
                update_data['updated'] = False
                with open(update_file, 'w') as f:
                    json.dump(update_data, f, indent=4)
        except Exception as e:
            print(f"Error checking for UI updates: {e}")

    @staticmethod
    def show_update_notification(update_data):
        """Show a nicely formatted dialog with legacy update information."""
        dialog = QDialog()
        dialog.setWindowTitle("UI Improvements Applied")
        dialog.setMinimumWidth(400)
        dialog.setMinimumHeight(300)

        layout = QVBoxLayout()

        # Title
        title_label = QLabel("UI Improvements Applied")
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #1a73e8;
            margin-bottom: 10px;
        """)
        layout.addWidget(title_label)

        # Date
        date_label = QLabel(f"Updated on: {update_data.get('date', 'Unknown')}")
        date_label.setStyleSheet("font-style: italic; color: #5f6368;")
        layout.addWidget(date_label)

        # Create scrollable area for changes
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # Add change list
        changes_label = QLabel("Changes:")
        changes_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        scroll_layout.addWidget(changes_label)

        for change in update_data.get('changes', []):
            change_item = QLabel(f"• {change}")
            change_item.setWordWrap(True)
            scroll_layout.addWidget(change_item)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        # OK button
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(dialog.accept)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1658c5;
            }
        """)
        layout.addWidget(ok_button)

        dialog.setLayout(layout)
        dialog.exec_()
