from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QPushButton, QSizeGrip, QScrollArea
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class WelcomeSection(QGroupBox):
    def __init__(self, toggle_callback):
        super().__init__("Rodent Refreshment Regulator Wizard")
        self.toggle_callback = toggle_callback
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.content_widget = QLabel()
        self.content_widget.setText(self.get_welcome_text())
        self.content_widget.setFont(QFont("Arial", 12))
        self.content_widget.setWordWrap(True)

        self.scroll_area.setWidget(self.content_widget)
        layout.addWidget(self.scroll_area)

        self.toggle_button = QPushButton("Hide Welcome Message")
        self.toggle_button.clicked.connect(self.toggle_welcome_message)
        layout.addWidget(self.toggle_button)

        self.setLayout(layout)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Rodent Refreshment Regulator Wizard")
        self.setGeometry(100, 100, 800, 600)  # Initial size and position
        self.size_grip = QSizeGrip(self)

    def get_welcome_text(self):
        return (
            "<div style='font-size: 14pt; font-weight: bold; color: green;'>Welcome to the Rodent Refreshment Regulator Wizard</div>"
            "<div style='font-size: 12pt; margin-top: 10px;'>Steps:</div>"
            "<ol style='font-size: 10pt; padding-left: 20px;'>"
            "<li>Answer the questions on the right side of the screen to suit your needs.</li>"
            "<li>Press the 'Suggest Settings' button to receive setting recommendations in the terminal below.</li>"
            "<li>Press the 'Push Settings' button to submit and save these setting recommendations.</li>"
            "<li>(OPTIONAL) Adjust settings manually in the 'Advanced Settings' menu below if desired.<br>"
            "<span style='color: red;'>* Remember to save these changes using the 'Update Settings' button at the bottom of the Advanced Settings menu.</span></li>"
            "<li>See the notes section below for additional information, and run the program when ready.</li>"
            "</ol>"
            "<div style='font-size: 12pt; margin-top: 20px;'>Notes:</div>"
            "<ul style='font-size: 10pt; padding-left: 20px;'>"
            "<li>Questions pertaining to water volume are for EACH relay.</li>"
            "<li>Water volume suggestions will always round UP based on the volume increments that your pumps are capable of outputting per trigger.<br>"
            "<span style='color: blue;'>* The amount of water released defaults to 10uL/trigger.</span></li>"
            "<li>Closing this window will stop the program. Please leave this window open for it to continue running.</li>"
            "<li>An email can optionally be sent to you upon each successful pump trigger. See the ReadMe for setup instructions if desired.</li>"
            "<li>CTRL+C is set to force close the program if required.</li>"
            "<li>'Stagger' is the time that elapses between triggers of the same relay pair (if applicable). Changing this value is not recommended.<br>"
            "<span style='color: blue;'>* This parameter is set based on the maximum electrical output of a Raspberry Pi-4. Only change if your hardware needs differ.</span></li>"
            "</ul>"
        )

    def toggle_welcome_message(self):
        if self.isVisible():
            self.hide()
            self.toggle_button.setText("Show Welcome Message and Instructions")
            self.toggle_callback(True)
        else:
            self.show()
            self.toggle_button.setText("Hide Welcome Message")
            self.toggle_callback(False)
