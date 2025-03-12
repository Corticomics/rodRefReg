from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QScrollArea, QWidget
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class WelcomeSection(QGroupBox):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        # Title
        title = QLabel("Welcome to the Rodent Refreshment Regulator (RRR)")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title)

        # Updated welcome text
        subheaders_text = (
            "<ul style='margin-top: 10px;'>"
            "<li style='margin-bottom: 15px;'><strong>System Overview:</strong><br>"
            "RRR is designed for precise automated water delivery to laboratory rodents using "
            "Raspberry Pi-controlled pumps and relay systems.</li>"
            
            "<li style='margin-bottom: 15px;'><strong>Hardware Compatibility:</strong><br>"
            "Developed on Raspberry Pi 4B, compatible with newer versions. Uses Sequent Microsystems "
            "8-Layer Stackable Relay HATs and 50µL LeeCo precision pumps.</li>"
            
            "<li style='margin-bottom: 15px;'><strong>Water Delivery:</strong><br>"
            "Default pump trigger delivers 50µL of water. The system automatically calculates "
            "required triggers based on your specified volumes.</li>"
            
            "<li style='margin-bottom: 15px;'><strong>Safety Features:</strong><br>"
            "- Built-in volume limits based on animal weight<br>"
            "- Emergency stop functionality<br>"
            "- Automated error detection and logging</li>"
            
            "<li style='margin-bottom: 15px;'><strong>Important Notes:</strong><br>"
            "- Keep this window open while the system is running<br>"
            "- Use CTRL+C for emergency shutdown if needed<br>"
            "- Optional email/Slack notifications available</li>"
            
            "<li style='margin-bottom: 15px;'><strong>Getting Started:</strong><br>"
            "Please visit the Help tab for detailed setup instructions, hardware guides, "
            "and troubleshooting information.</li>"
            "</ul>"
        )

        subheaders_label = QLabel(subheaders_text)
        subheaders_label.setFont(QFont("Arial", 12))
        subheaders_label.setWordWrap(True)
        subheaders_label.setTextFormat(Qt.RichText)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.addWidget(subheaders_label)
        scroll_area.setWidget(content_widget)

        layout.addWidget(scroll_area)
        self.setLayout(layout)
