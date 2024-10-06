from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QMessageBox
from utils.dependency_checker import check_dependencies, install_dependencies
from utils.git_handler import clone_repository
from utils.environment import setup_virtualenv
from ui.config_window import ConfigWindow
from ui.progress_window import ProgressWindow

class InstallerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rodent Refreshment Regulator Installer")
        self.init_ui()
        self.total_steps = 4  # Adjust this if you add more steps
        self.current_step = 0
        self.progress_window = ProgressWindow(total_steps=self.total_steps)

    def init_ui(self):
        layout = QVBoxLayout()

        self.welcome_label = QLabel("Welcome to the Rodent Refreshment Regulator Installer")
        layout.addWidget(self.welcome_label)

        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.start_installation)
        layout.addWidget(self.next_button)

        self.setLayout(layout)

    def start_installation(self):
        self.progress_window.show()
        self.check_dependencies()

    def update_progress(self, message):
        self.current_step += 1
        self.progress_window.update_progress(self.current_step, message)

    def check_dependencies(self):
        self.update_progress("Checking for dependencies...")
        missing_deps = check_dependencies()
        if missing_deps:
            self.install_dependencies(missing_deps)
        else:
            self.clone_repo()

    def install_dependencies(self, dependencies):
        self.update_progress("Installing dependencies...")
        success = install_dependencies(dependencies)
        if success:
            self.clone_repo()
        else:
            self.show_error("Dependency installation failed")

    def clone_repo(self):
        self.update_progress("Cloning the repository...")
        if clone_repository():
            self.setup_virtualenv()
        else:
            self.show_error("Failed to clone repository")

    def setup_virtualenv(self):
        self.update_progress("Setting up the virtual environment...")
        if setup_virtualenv():
            self.show_config_window()
        else:
            self.show_error("Failed to set up the virtual environment")

    def show_config_window(self):
        self.update_progress("Installation completed. Proceeding to configuration.")
        self.config_window = ConfigWindow()
        self.config_window.show()
        self.progress_window.close()
        self.close()

    def show_error(self, message):
        self.progress_window.close()
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setText(message)
        error_dialog.setWindowTitle("Error")
        error_dialog.exec_()
