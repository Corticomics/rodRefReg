from PyQt5.QtWidgets import QLabel, QMenu, QAction, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

from ui.profile_dialog import ProfileDialog
from ui.login_dialog import LoginDialog

class UserIcon(QLabel):
    def __init__(self, main_window, db_handler, login_system):
        super().__init__()
        self.main_window = main_window
        self.db_handler = db_handler
        self.login_system = login_system
        self.trainer_id = None  # Holds the logged-in trainer ID
        
        self.setPixmap(QIcon("path_to_user_icon.png").pixmap(32, 32))  # Adjust icon path and size
        self.setAlignment(Qt.AlignRight)
        
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("User Options")
        
        self.create_menu()

    def create_menu(self):
        """Creates the user options menu."""
        self.menu = QMenu()

        # Login/Logout actions
        self.login_action = QAction("Log In", self)
        self.login_action.triggered.connect(self.show_login)
        self.menu.addAction(self.login_action)

        self.logout_action = QAction("Log Out", self)
        self.logout_action.triggered.connect(self.logout)
        self.menu.addAction(self.logout_action)
        self.logout_action.setVisible(False)  # Only show when logged in

        # Profile view
        self.profile_action = QAction("View Profile", self)
        self.profile_action.triggered.connect(self.view_profile)
        self.menu.addAction(self.profile_action)
        self.profile_action.setVisible(False)  # Only show when logged in

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.menu.exec_(self.mapToGlobal(event.pos()))

    def show_login(self):
        """Opens the login dialog and handles login."""
        dialog = LoginDialog(self.login_system)
        if dialog.exec_() == QDialog.Accepted:
            self.trainer_id = dialog.trainer_id
            self.main_window.load_animals_tab(self.trainer_id)
            self.update_menu_for_login()

    def update_menu_for_login(self):
        """Updates menu visibility based on login status."""
        self.login_action.setVisible(False)
        self.logout_action.setVisible(True)
        self.profile_action.setVisible(True)

    def view_profile(self):
        """Displays the profile of the logged-in trainer."""
        if self.trainer_id:
            dialog = ProfileDialog(self.trainer_id, self.db_handler)
            dialog.exec_()
        else:
            QMessageBox.warning(self, "No Profile", "Please log in first.")

    def logout(self):
        """Logs out the current user and updates the UI."""
        self.trainer_id = None
        self.main_window.clear_animals_tab()
        self.login_action.setVisible(True)
        self.logout_action.setVisible(False)
        self.profile_action.setVisible(False)
        QMessageBox.information(self, "Logged Out", "You have been logged out.")