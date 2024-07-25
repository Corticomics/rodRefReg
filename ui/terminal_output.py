from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QTextEdit
import sys

class TerminalOutput(QGroupBox):
    def __init__(self):
        super().__init__("System Messages")
        layout = QVBoxLayout()
        
        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)
        layout.addWidget(self.output_box)
        
        self.setLayout(layout)
        
        sys.stdout = self
        sys.stderr = self

    def write(self, message):
        self.output_box.append(message)
    
    def flush(self):
        pass

    def print_to_terminal(self, message):
        self.write(message)
