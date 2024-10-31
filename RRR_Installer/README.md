Rodent Refreshment Regulator Installer
======================================

Thank you for choosing the Rodent Refreshment Regulator (RRR) application.

Installation Instructions:

1. **Download the Installer**

   - Download the `RRR_Installer.zip` file from the provided link.

2. **Extract the Installer**

   - Right-click the `RRR_Installer.zip` file and select "Extract Here" or "Extract to RRR_Installer/".

3. **Run the Installer**

   - Open the extracted `RRR_Installer` folder.
   - Ensure that the `installer_main` file has execute permissions:
     ```bash
     chmod +x installer_main
     ```
   - Double-click on the `RRR Installer.desktop` file.
   - If prompted with a security warning, select "Trust and Launch".

4. **Follow the Installation Steps**

   - Enter your **Slack Token** and **Channel ID** when prompted.
   - Click **"Install"** to begin the installation.
   - The installer will guide you through the process, including installing any missing dependencies.
   - You may be prompted to enter your password to authorize administrative actions.

5. **After Installation**

   - Once the installation is complete, you will receive a confirmation message.
   - The RRR application is now installed and configured.
   - Instructions on how to start and use the application are provided below.

**Starting the RRR Application**

- To start the RRR application, you can:

  - Run the application from the terminal using the command:

    ```bash
    python3 /opt/rrr/main.py
    ```

  - Or set up a desktop shortcut or menu entry if desired.

**Troubleshooting**

- **Installer Does Not Start**

  - Ensure that the `installer_main` file has execute permissions.
    - Right-click the file, select "Properties," go to the "Permissions" tab, and check "Allow executing file as program".

- **Permission Errors**

  - If you receive errors related to permissions, ensure that you are not running the installer as root.
  - The installer should be run as a normal user; it will prompt for administrative permissions when needed.

- **Missing Dependencies**

  - The installer will check for and install required dependencies automatically.
  - Ensure that your Raspberry Pi is connected to the internet during installation.

- **Network Issues**

  - If network issues occur, retry the installation after checking your connection.

**Support**

For assistance, please contact support@example.com.

Thank you!

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

    try:
        # Use pkexec to create directory and move file
        subprocess.check_call(['pkexec', 'mkdir', '-p', '/etc/rrr'])
        subprocess.check_call(['pkexec', 'mv', temp_config_file, config_path])
        subprocess.check_call(['pkexec', 'chmod', '600', config_path])
        logging.info("Configuration saved successfully.")
    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to save configuration: {e}"
        logging.error(error_msg)
        self.progress_update.emit(error_msg)
        self.installation_complete.emit(False)
        return


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


def installation_finished(self, success):
    self.progress_bar.setValue(self.progress_bar.maximum())
    if success:
        # Create desktop shortcut
        self.create_desktop_shortcut()
        reply = QMessageBox.question(
            self,
            "Installation Complete",
            "The RRR application has been installed successfully.\nDo you want to launch the application now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            # Launch the application
            self.launch_application()
        logging.info("Installation completed successfully.")
    else:
        QMessageBox.critical(self, "Installation Failed", "An error occurred during installation. Please check the installer log for details.")
        logging.error("Installation failed.")
    self.install_button.setEnabled(True)
    self.cancel_button.setEnabled(True)


def launch_application(self):
    try:
        subprocess.Popen(['python3', '/opt/rrr/main.py'])
    except Exception as e:
        logging.error(f"Failed to launch the application: {e}")
        QMessageBox.critical(self, "Error", f"Failed to launch the application: {e}")


def create_desktop_shortcut(self):
    desktop_entry = f"""
[Desktop Entry]
Type=Application
Name=RRR Application
Comment=Rodent Refreshment Regulator
Exec=python3 /opt/rrr/main.py
Icon=/opt/rrr/resources/icon.png
Terminal=false
Categories=Utility;
"""
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'RRR Application.desktop')
    try:
        with open(desktop_path, 'w') as f:
            f.write(desktop_entry)
        os.chmod(desktop_path, 0o755)
        logging.info("Desktop shortcut created at %s", desktop_path)
    except Exception as e:
        logging.error(f"Failed to create desktop shortcut: {e}")
        QMessageBox.warning(self, "Error", f"Failed to create desktop shortcut: {e}")
