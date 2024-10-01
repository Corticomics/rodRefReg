import sys
from PyQt5.QtWidgets import QApplication
from ui.wizard_window import InstallerWindow
from utils.logger import setup_logging

def main():
    setup_logging()
    app = QApplication(sys.argv)
    installer = InstallerWindow()
    installer.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
