#!/usr/bin/env python3
"""
installer_main.py

This script provides the main GUI installer for the Rodent Refreshment Regulator (RRR) application.
"""

import sys
import os
import subprocess
import logging
import re
from shutil import which
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QMessageBox, QTextEdit, QProgressBar, QHBoxLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Configure logging
logging.basicConfig(
    filename='installer.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class InstallerThread(QThread):
    progress_update = pyqtSignal(str)
    progress_increment = pyqtSignal(int)
    installation_complete = pyqtSignal(bool)

    def __init__(self, config_data):
        super().__init__()
        self.config_data = config_data
        self.total_steps = 5  # Update if the number of steps changes

    def run(self):
        try:
            # Step 1: Install system dependencies
            self.progress_update.emit("Installing system dependencies...")
            self.install_system_dependencies()
            self.progress_increment.emit(1)

            # Step 2: Install Python packages
            self.progress_update.emit("Installing Python packages...")
            self.install_python_packages()
            self.progress_increment.emit(1)

            # Step 3: Set up the application
            self.progress_update.emit("Setting up the application...")
            self.setup_application()
            self.progress_increment.emit(1)

            # Step 4: Save configuration
            self.progress_update.emit("Saving configuration...")
            self.save_configuration()
            self.progress_increment.emit(1)

            # Step 5: Finalize installation
            self.progress_update.emit("Finalizing installation...")
            self.finalize_installation()
            self.progress_increment.emit(1)

            self.progress_update.emit("Installation completed successfully.")
            self.installation_complete.emit(True)
        except subprocess.CalledProcessError as e:
            error_msg = f"Command '{' '.join(e.cmd)}' returned non-zero exit status {e.returncode}."
            logging.error(error_msg)
            self.progress_update.emit(f"Installation failed: {error_msg}")
            self.installation_complete.emit(False)
        except Exception as e:
            logging.exception("An unexpected error occurred during installation.")
            self.progress_update.emit(f"Installation failed: {str(e)}")
            self.installation_complete.emit(False)

    def check_tool_availability(self, tool_name):
        """Check if a tool is available in the system path."""
        if which(tool_name) is None:
            error_msg = f"Required tool '{tool_name}' is not available."
            logging.error(error_msg)
            self.progress_update.emit(error_msg)
            return False
        return True

    def install_system_dependencies(self):
        packages = ['git', 'python3-pip', 'python3-venv', 'python3-pyqt5']
        cmd = ['pkexec', sys.executable, 'installer_backend.py', 'install_system_dependencies'] + packages
        logging.info("Installing system dependencies via backend script...")
        subprocess.check_call(cmd)

    def install_python_packages(self):
        packages = ['requests', 'slack_sdk']
        cmd = ['pkexec', sys.executable, 'installer_backend.py', 'install_python_packages'] + packages
        logging.info("Installing Python packages via backend script...")
        subprocess.check_call(cmd)

    def setup_application(self):
        repo_url = 'https://github.com/Corticomics/rodRefReg.git'
        app_path = '/opt/rrr'
        cmd = ['pkexec', sys.executable, 'installer_backend.py', 'clone_repository', repo_url, app_path]
        logging.info("Setting up the application via backend script...")
        subprocess.check_call(cmd)

    def save_configuration(self):
        settings = {
            "slack_token": self.config_data['slack_token'],
            "channel_id": self.config_data['channel_id']
        }
        config_content = f"""
    slack_token = "{settings['slack_token']}"
    channel_id = "{settings['channel_id']}"
    """
        config_path = '/etc/rrr/settings.py'
        temp_config_file = 'settings_temp.py'
        with open(temp_config_file, 'w') as f:
            f.write(config_content)

        cmd = ['pkexec', sys.executable, 'installer_backend.py', 'create_config_file', temp_config_file, config_path]
        logging.info("Saving configuration via backend script...")
        subprocess.check_call(cmd)


    def finalize_installation(self):
        """Finalize installation steps."""
        logging.info("Finalizing installation...")
        # Placeholder for any final installation steps
        pass

class InstallerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rodent Refreshment Regulator Installer")
        self.config_data = {}
        self.init_ui()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Create layout
        main_layout = QVBoxLayout()

        # Slack Token
        slack_label = QLabel("Slack Token:")
        self.slack_input = QLineEdit()
        main_layout.addWidget(slack_label)
        main_layout.addWidget(self.slack_input)

        # Channel ID
        channel_label = QLabel("Channel ID:")
        self.channel_input = QLineEdit()
        main_layout.addWidget(channel_label)
        main_layout.addWidget(self.channel_input)

        # Install Button
        button_layout = QHBoxLayout()
        self.install_button = QPushButton("Install")
        self.install_button.clicked.connect(self.start_installation)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.close)
        button_layout.addWidget(self.install_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)

        # Progress Display
        self.progress_text = QTextEdit()
        self.progress_text.setReadOnly(True)
        self.progress_text.setFixedHeight(200)
        main_layout.addWidget(self.progress_text)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(5)  # Total number of steps
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        self.central_widget.setLayout(main_layout)

    def start_installation(self):
        # Disable the install and cancel buttons
        self.install_button.setEnabled(False)
        self.cancel_button.setEnabled(False)

        # Collect configuration data
        self.config_data['slack_token'] = self.slack_input.text().strip()
        self.config_data['channel_id'] = self.channel_input.text().strip()

        # Validate inputs
        if not self.validate_inputs():
            self.install_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            return

        # Clear the progress text and reset the progress bar
        self.progress_text.clear()
        self.progress_bar.setValue(0)

        # Start installation thread
        self.thread = InstallerThread(self.config_data)
        self.thread.progress_update.connect(self.update_progress)
        self.thread.progress_increment.connect(self.increment_progress_bar)
        self.thread.installation_complete.connect(self.installation_finished)
        self.thread.start()

    def validate_inputs(self):
        errors = []
        # Slack Token validation (example pattern)
        if not self.config_data['slack_token']:
            errors.append("Slack Token is required.")
        elif not re.match(r'^[a-zA-Z0-9\-]+$', self.config_data['slack_token']):
            errors.append("Slack Token contains invalid characters.")

        # Channel ID validation (example pattern)
        if not self.config_data['channel_id']:
            errors.append("Channel ID is required.")
        elif not re.match(r'^[A-Z0-9]+$', self.config_data['channel_id']):
            errors.append("Channel ID contains invalid characters.")

        if errors:
            QMessageBox.warning(self, "Input Error", "\n".join(errors))
            return False
        return True

    def update_progress(self, message):
        self.progress_text.append(message)
        QApplication.processEvents()

    def increment_progress_bar(self, value):
        self.progress_bar.setValue(self.progress_bar.value() + value)
        QApplication.processEvents()

    def installation_finished(self, success):
        if success:
            QMessageBox.information(self, "Installation Complete", "The RRR application has been installed successfully.")
            logging.info("Installation completed successfully.")
        else:
            QMessageBox.critical(self, "Installation Failed", "An error occurred during installation. Please check the installer log for details.")
            logging.error("Installation failed.")
        self.install_button.setEnabled(True)
        self.cancel_button.setEnabled(True)

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Exit Installer', 'Are you sure you want to exit?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

def main():
    # Check if running as root (we do not want to run the GUI as root)
    if os.geteuid() == 0:
        QMessageBox.critical(None, "Error", "Please run the installer as a normal user, not as root.")
        sys.exit(1)

    app = QApplication(sys.argv)
    installer = InstallerGUI()
    installer.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
