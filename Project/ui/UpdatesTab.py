"""Settings -> Updates sub-tab.

Shows the installed version, checks for newer releases, and — on an installed
(blue-green) device — installs them one click and rolls back. On a developer
clone the install/rollback controls stay hidden. See docs/UPDATE_SYSTEM.md §13.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QTextEdit, QMessageBox
)
from PyQt5.QtCore import QUrl, pyqtSlot
from PyQt5.QtGui import QDesktopServices

from version import __version__
from utils import paths, updater


class UpdatesTab(QWidget):
    """Update panel: installed version, check, one-click install, rollback."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._latest = None
        self._applying = False
        self._build_ui()
        self._refresh_revert_button()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        box = QGroupBox("Software updates")
        box_layout = QVBoxLayout(box)

        self.current_label = QLabel(f"Installed version:  {__version__}")
        self.status_label = QLabel(
            "Press “Check for updates” to see whether a newer version "
            "is available."
        )
        self.status_label.setWordWrap(True)

        button_row = QHBoxLayout()
        self.check_button = QPushButton("Check for updates")
        self.check_button.clicked.connect(self.check)
        self.update_button = QPushButton("Update now")
        self.update_button.setVisible(False)
        self.update_button.clicked.connect(self._on_update_now)
        self.view_button = QPushButton("View release")
        self.view_button.setVisible(False)
        self.view_button.clicked.connect(self._open_release)
        self.revert_button = QPushButton("Revert to previous version")
        self.revert_button.setVisible(False)
        self.revert_button.clicked.connect(self._on_revert)
        for widget in (self.check_button, self.update_button,
                       self.view_button, self.revert_button):
            button_row.addWidget(widget)
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

    def _refresh_revert_button(self):
        """Show 'Revert' only when a rollback target exists."""
        self.revert_button.setVisible(updater.has_previous_release())

    # --- check -------------------------------------------------------------
    def check(self):
        """Start a background check for a newer release."""
        self.check_button.setEnabled(False)
        self.status_label.setText("Checking…")
        try:
            updater.run_check(self, self._on_result)
        except Exception:
            self._on_result(None)

    @pyqtSlot(object)
    def _on_result(self, info):
        """Receive the check result (on the GUI thread; see updater.run_check)."""
        self.check_button.setEnabled(True)

        if info is None:
            self.status_label.setText(
                "Couldn’t check for updates — no internet connection, "
                "or GitHub could not be reached."
            )
            self.update_button.setVisible(False)
            self.view_button.setVisible(False)
            self.notes.setVisible(False)
            return

        self._latest = info
        if info.available:
            self.view_button.setVisible(True)
            can_apply = bool(paths.home_dir() and info.bundle_url)
            self.update_button.setVisible(can_apply)
            if can_apply:
                self.status_label.setText(
                    f"Version {info.version} is available "
                    f"(you have {__version__})."
                )
            else:
                self.status_label.setText(
                    f"Version {info.version} is available (you have "
                    f"{__version__}). Re-run the installer to update."
                )
            if info.notes:
                self.notes.setPlainText(info.notes)
                self.notes.setVisible(True)
        else:
            self.status_label.setText(f"You’re up to date (version {__version__}).")
            self.update_button.setVisible(False)
            self.view_button.setVisible(False)
            self.notes.setVisible(False)

    # --- apply -------------------------------------------------------------
    def _on_update_now(self):
        if self._applying or not self._latest:
            return
        if QMessageBox.question(
            self, "Install update",
            f"Install version {self._latest.version} now?\n\n"
            "The update is downloaded and verified, then takes effect when "
            "RRR restarts. A running delivery schedule will block it.",
        ) != QMessageBox.Yes:
            return

        self._applying = True
        self.update_button.setEnabled(False)
        self.check_button.setEnabled(False)
        self.status_label.setText("Starting update…")
        try:
            updater.run_apply(self, self._latest,
                              self._on_apply_progress, self._on_apply_done)
        except Exception as exc:
            self._on_apply_done(False, f"Update failed: {exc}")

    @pyqtSlot(str)
    def _on_apply_progress(self, message):
        self.status_label.setText(message)

    @pyqtSlot(bool, str)
    def _on_apply_done(self, ok, message):
        self._applying = False
        self.check_button.setEnabled(True)
        self.update_button.setEnabled(True)
        self.status_label.setText(message)
        self._refresh_revert_button()
        if ok:
            self.update_button.setVisible(False)
            self._offer_restart(message)
        else:
            title, icon = self._title_and_icon_for_failure(message)
            box = QMessageBox(icon, title, message, parent=self)
            box.exec_()

    @staticmethod
    def _title_and_icon_for_failure(message):
        """Pick a dialog title and icon for an apply-failure message.

        Phase 3 of the offline-resilience plan: a non-technical operator
        seeing "Update not installed" alongside a download error is
        confusing — the failure title now states the cause. The
        classification itself lives in :mod:`utils.update_failure` so it
        can be unit-tested without bringing up the GUI stack.
        """
        from utils.update_failure import classify_failure, INTERNET, VERIFY

        category = classify_failure(message)
        if category == INTERNET:
            return "Update needs internet", QMessageBox.Information
        if category == VERIFY:
            return "Update could not be verified", QMessageBox.Warning
        return "Update not installed", QMessageBox.Warning

    # --- revert ------------------------------------------------------------
    def _on_revert(self):
        if QMessageBox.question(
            self, "Revert to previous version",
            "Roll back to the previously installed version?\n\n"
            "It takes effect when RRR restarts.",
        ) != QMessageBox.Yes:
            return
        ok, message = updater.revert()
        if ok:
            self.status_label.setText(message)
            self._offer_restart(message)
        else:
            QMessageBox.warning(self, "Could not revert", message)

    # --- restart -----------------------------------------------------------
    def _offer_restart(self, message):
        box = QMessageBox(self)
        box.setWindowTitle("Restart required")
        box.setText(message)
        box.setInformativeText("Restart RRR now?")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        if box.exec_() == QMessageBox.Yes:
            restarted, detail = updater.restart_app()
            if not restarted:
                QMessageBox.information(self, "Restart", detail)

    def _open_release(self):
        if self._latest is not None:
            QDesktopServices.openUrl(QUrl(self._latest.url))
