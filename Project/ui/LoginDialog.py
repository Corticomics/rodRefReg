from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt

class LoginDialog(QDialog):
    def __init__(self, login_system):
        super().__init__()
        self.login_system = login_system
        self.trainer_id = None
        self.setWindowTitle("Log In")

        layout = QVBoxLayout(self)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        layout.addWidget(QLabel("Username"))
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(QLabel("Password"))
        layout.addWidget(self.password_input)

        self.login_button = QPushButton("Log In")
        self.login_button.clicked.connect(self.authenticate)
        layout.addWidget(self.login_button)

    def authenticate(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        trainer_id = self.login_system.login(username, password)
        if trainer_id:
            self.trainer_id = trainer_id
            self.accept()
        else:
            QMessageBox.warning(self, "Login Failed", "Incorrect username or password.")