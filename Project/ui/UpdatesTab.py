"""Settings -> Updates sub-tab.

Shows the installed version and lets the operator check for a newer release on
demand. Phase 1 of the update system is notify-only: this tab reports whether
an update exists and links to the release page; it does not install anything.
See docs/UPDATE_SYSTEM.md.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton, QTextEdit
)
from PyQt5.QtCore import QUrl, pyqtSlot
from PyQt5.QtGui import QDesktopServices

from version import __version__
from utils.updater import run_check


class UpdatesTab(QWidget):
    """A read-only update panel: installed version + 'Check for updates'."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._latest = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        box = QGroupBox("Software updates")
        box_layout = QVBoxLayout(box)

        self.current_label = QLabel(f"Installed version:  {__version__}")
        self.status_label = QLabel(
            "Press “Check for updates” to see whether a newer "
            "version is available."
        )
        self.status_label.setWordWrap(True)

        button_row = QHBoxLayout()
        self.check_button = QPushButton("Check for updates")
        self.check_button.clicked.connect(self.check)
        self.view_button = QPushButton("View release")
        self.view_button.setVisible(False)
        self.view_button.clicked.connect(self._open_release)
        button_row.addWidget(self.check_button)
        button_row.addWidget(self.view_button)
        button_row.addStretch()

        self.notes = QTextEdit()
        self.notes.setReadOnly(True)
        self.notes.setVisible(False)

        box_layout.addWidget(self.current_label)
        box_layout.addWidget(self.status_label)
        box_layout.addLayout(button_row)
        box_layout.addWidget(self.notes)

        layout.addWidget(box)
        layout.addStretch()

    def check(self):
        """Start a background check for a newer release."""
        self.check_button.setEnabled(False)
        self.status_label.setText("Checking…")
        try:
            run_check(self, self._on_result)
        except Exception:
            self._on_result(None)

    @pyqtSlot(object)
    def _on_result(self, info):
        """Receive the check result (on the GUI thread; see updater.run_check)."""
        self.check_button.setEnabled(True)

        if info is None:
            self.status_label.setText(
                "Couldn’t check for updates — no internet "
                "connection, or GitHub could not be reached."
            )
            self.view_button.setVisible(False)
            self.notes.setVisible(False)
            return

        self._latest = info
        if info.available:
            self.status_label.setText(
                f"Version {info.version} is available "
                f"(you have {__version__})."
            )
            self.view_button.setVisible(True)
            if info.notes:
                self.notes.setPlainText(info.notes)
                self.notes.setVisible(True)
        else:
            self.status_label.setText(
                f"You’re up to date (version {__version__})."
            )
            self.view_button.setVisible(False)
            self.notes.setVisible(False)

    def _open_release(self):
        if self._latest is not None:
            QDesktopServices.openUrl(QUrl(self._latest.url))
