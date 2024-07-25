from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QPushButton, QSizePolicy, QScrollArea
from PyQt5.QtCore import Qt

class WelcomeSection(QGroupBox):
    def __init__(self, toggle_callback):
        super().__init__("Rodent Refreshment Regulator Wizard")
        self.toggle_callback = toggle_callback
        self.is_hidden = False

        layout = QVBoxLayout()

        self.welcome_label = QLabel("Welcome to the Rodent Refreshment Regulator Wizard")
        self.welcome_label.setStyleSheet("font-size: 24px; color: green;")
        layout.addWidget(self.welcome_label)

        self.steps_label = QLabel("Steps:")
        self.steps_label.setStyleSheet("font-size: 18px; color: green; margin-top: 10px;")
        layout.addWidget(self.steps_label)

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

        self.subheaders_label = QLabel(subheaders_text)
        self.subheaders_label.setStyleSheet("font-size: 12px;")
        self.subheaders_label.setWordWrap(True)
        self.subheaders_label.setTextFormat(Qt.RichText)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.subheaders_label)

        layout.addWidget(scroll_area)

        self.toggle_button = QPushButton("Hide Welcome Message")
        self.toggle_button.clicked.connect(self.toggle_message)
        layout.addWidget(self.toggle_button)

        self.setLayout(layout)

    def toggle_message(self):
        self.is_hidden = not self.is_hidden
        self.welcome_label.setVisible(not self.is_hidden)
        self.steps_label.setVisible(not self.is_hidden)
        self.subheaders_label.setVisible(not self.is_hidden)
        self.toggle_button.setText("Show Welcome Message and Instructions" if self.is_hidden else "Hide Welcome Message")
        self.toggle_callback(self.is_hidden)
