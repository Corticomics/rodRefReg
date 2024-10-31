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

# Directly import PyQt5 modules
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QMessageBox, QTextEdit, QProgressBar, QHBoxLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Rest of your installer code remains the same...


# Configure logging
logging.basicConfig(
    filename='installer.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def check_pyqt5_installed():
    try:
        import PyQt5
        return True
    except ImportError:
        return False

def install_pyqt5():
    logging.info("PyQt5 is not installed. Installing now...")
    try:
        # Update package list and install PyQt5
        subprocess.check_call(['pkexec', 'apt-get', 'update'])
        subprocess.check_call(['pkexec', 'apt-get', 'install', '-y', 'python3-pyqt5'])
        logging.info("PyQt5 installed successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to install PyQt5: {e}")
        print(f"Failed to install PyQt5: {e}")
        sys.exit(1)

# Check if PyQt5 is installed before importing it
if not check_pyqt5_installed():
    install_pyqt5()

# Now attempt to import PyQt5
try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
        QVBoxLayout, QMessageBox, QTextEdit, QProgressBar, QHBoxLayout
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal
except ImportError:
    logging.error("PyQt5 is still not available after installation. Exiting.")
    print("PyQt5 is still not available after installation. Exiting.")
    sys.exit(1)

class InstallerThread(QThread):
    progress_update = pyqtSignal(str)
    progress_increment = pyqtSignal(int)
    installation_complete = pyqtSignal(bool)

    def __init__(self, config_data):
        super().__init__()
        self.config_data = config_data
        self.total_steps = 6  # Update if the number of steps changes

    def run(self):
        try:
            # Step 1: Check and install system dependencies
            self.progress_update.emit("Checking and installing system dependencies...")
            self.check_and_install_system_packages()
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

    def is_package_installed(self, package_name):
        """Check if a system package is installed."""
        try:
            output = subprocess.check_output(['dpkg', '-s', package_name], stderr=subprocess.STDOUT)
            return 'Status: install ok installed' in output.decode()
        except subprocess.CalledProcessError:
            return False

    def check_and_install_system_packages(self):
        """Check and install required system packages."""
        packages = ['git', 'python3-pip', 'python3-venv']
        for package in packages:
            if not self.is_package_installed(package):
                self.progress_update.emit(f"Installing {package}...")
                logging.info(f"Installing {package}...")
                try:
                    subprocess.check_call(['pkexec', 'apt-get', 'install', '-y', package])
                except subprocess.CalledProcessError as e:
                    error_msg = f"Failed to install {package}: {e}"
                    logging.error(error_msg)
                    self.progress_update.emit(error_msg)
                    self.installation_complete.emit(False)
                    return

    def install_python_packages(self):
        """Install required Python packages."""
        packages = ['requests', 'slack_sdk']
        logging.info("Installing Python packages...")
        try:
            subprocess.check_call(['pip3', 'install'] + packages)
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to install Python packages: {e}"
            logging.error(error_msg)
            self.progress_update.emit(error_msg)
            self.installation_complete.emit(False)
            return

    def setup_application(self):
        """Clone or update the RRR application repository."""
        app_path = '/opt/rrr'
        repo_url = 'https://github.com/Corticomics/rodRefReg.git'

        if not self.is_package_installed('git'):
            error_msg = "git is not available after installation. Please check your system."
            logging.error(error_msg)
            self.progress_update.emit(error_msg)
            self.installation_complete.emit(False)
            return

        if not os.path.exists(app_path):
            cmd = ['pkexec', 'git', 'clone', repo_url, app_path]
            logging.info("Cloning the RRR application repository...")
            subprocess.check_call(cmd)
        else:
            cmd = ['pkexec', 'git', '-C', app_path, 'pull']
            logging.info("Updating the RRR application repository...")
            subprocess.check_call(cmd)

    def save_configuration(self):
        """Save user-provided configuration securely."""
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
        logging.info("Saving configuration to %s", config_path)
        with open(temp_config_file, 'w') as f:
            f.write(config_content)

        cmd = ['pkexec', sys.executable, 'installer_backend.py', 'create_config_file', temp_config_file, config_path]
        logging.info("Saving configuration via backend script...")
        try:
            subprocess.check_call(cmd)
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to save configuration: {e}"
            logging.error(error_msg)
            self.progress_update.emit(error_msg)
            self.installation_complete.emit(False)
            return

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
        self.progress_bar.setMaximum(6)  # Total number of steps
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
        print("Please run the installer as a normal user, not as root.")
        sys.exit(1)

    app = QApplication(sys.argv)
    installer = InstallerGUI()
    installer.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
