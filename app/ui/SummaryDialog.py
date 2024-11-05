# app/ui/SummaryDialog.py

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt

class SummaryDialog(QDialog):
    def __init__(self, summary_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Assignment Summary")
        self.setMinimumSize(400, 300)
        self.init_ui(summary_text)

    def init_ui(self, summary_text):
        layout = QVBoxLayout()
        self.setLayout(layout)

        summary_label = QLabel(summary_text)
        summary_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)