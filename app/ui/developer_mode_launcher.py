# app/gui/developer_mode_launcher.py

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt
import sys
import os

class DeveloperModeLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.launch_developer_mode()

    def init_ui(self):
        self.setWindowTitle("Developer Mode Launcher")
        self.setGeometry(100, 100, 300, 200)

    def launch_developer_mode(self):
        """
        Launch the Developer Mode application as a separate process.
        """
        try:
            # Determine the path to the developer_mode main.py
            current_dir = os.path.dirname(os.path.abspath(__file__))
            developer_mode_path = os.path.join(current_dir, '..', '..', 'developer_mode', 'main.py')

            if not os.path.exists(developer_mode_path):
                raise FileNotFoundError(f"Developer Mode main.py not found at {developer_mode_path}")

            # Launch Developer Mode using subprocess
            import subprocess
            subprocess.Popen([sys.executable, developer_mode_path])

            self.close()  # Close the launcher window after launching
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to launch Developer Mode: {e}")
            self.close()