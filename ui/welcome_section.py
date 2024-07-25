# ui/welcome_section.py
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QScrollArea, QWidget, QPushButton, QHBoxLayout
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt

class WelcomeSection(QGroupBox):
    def __init__(self, toggle_welcome_message_callback):
        super().__init__("Rodent Refreshment Regulator Wizard")
        layout = QVBoxLayout()

        welcome_label = QLabel("Welcome to the Rodent Refreshment Regulator Wizard")
        welcome_label.setFont(QFont("Arial", 24, QFont.Bold))
        welcome_label.setStyleSheet("color: green;")
        layout.addWidget(welcome_label)

        steps_label = QLabel("Steps:")
        steps_label.setFont(QFont("Arial", 18, QFont.Bold))
        steps_label.setStyleSheet("color: green; margin-top: 10px;")
        layout.addWidget(steps_label)

        subheaders_text = (
            "<ol style='padding-left: 20px;'>"
            "<li style='margin-bottom: 10px;'>Answer the questions on the right side of the screen to suit your needs.</li>"
            "<li style='margin-bottom: 10px;'>Press the 'Suggest Settings' button to receive setting recommendations in the terminal below.</li>"
            "<li style='margin-bottom: 10px;'>Press the 'Push Settings' button to submit and save these setting recommendations.</li>"
            "<li style='margin-bottom: 10px;'>(OPTIONAL) Adjust settings manually in the 'Advanced Settings' menu below if desired.<br>"
            "<span style='margin-left: 20px; color: red;'>* Remember to save these changes using the 'Update Settings' button at the bottom of the Advanced Settings menu.</span></li>"
            "<li style='margin-bottom: 10px;'>See the notes section below for additional information, and run the program when ready.</li>"
            "</ol>"
            "<div style='margin-top: 20px;'>Notes:</div>"
            "<ul style='padding-left: 20px;'>"
            "<li style='margin-bottom: 10px;'>Questions pertaining to water volume are for EACH relay.</li>"
            "<li style='margin-bottom: 10px;'>Water volume suggestions will always round UP based on the volume increments that your pumps are capable of outputting per trigger.<br>"
            "<span style='margin-left: 20px; color: blue;'>* The amount of water released defaults to 10uL/trigger.</span></li>"
            "<li style='margin-bottom: 10px;'>Closing this window will stop the program. Please leave this window open for it to continue running.</li>"
            "<li style='margin-bottom: 10px;'>An email can optionally be sent to you upon each successful pump trigger. See the ReadMe for setup instructions if desired.</li>"
            "<li style='margin-bottom: 10px;'>CTRL+C is set to force close the program if required.</li>"
            "<li style='margin-bottom: 10px;'>'Stagger' is the time that elapses between triggers of the same relay pair (if applicable). Changing this value is not recommended.<br>"
            "<span style='margin-left: 20px; color: blue;'>* This parameter is set based on the maximum electrical output of a Raspberry Pi-4. Only change if your hardware needs differ.</span></li>"
            "</ul>"
        )

        subheaders_label = QLabel(subheaders_text)
        subheaders_label.setFont(QFont("Arial", 12))
        subheaders_label.setWordWrap(True)
        subheaders_label.setTextFormat(Qt.RichText)
        layout.addWidget(subheaders_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_content.setLayout(layout)
        self.scroll_area.setWidget(scroll_content)

        button_layout = QHBoxLayout()
        self.toggle_button = QPushButton("Hide Welcome Message")
        self.toggle_button.clicked.connect(toggle_welcome_message_callback)
        button_layout.addWidget(self.toggle_button)

        main_layout = QVBoxLayout()
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.scroll_area)
        self.setLayout(main_layout)