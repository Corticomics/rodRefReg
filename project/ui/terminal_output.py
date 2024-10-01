from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QTextEdit

class TerminalOutput(QGroupBox):
    def __init__(self):
        super().__init__("System Messages")
        layout = QVBoxLayout()
        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        layout.addWidget(self.terminal_output)
        self.setLayout(layout)

    def print_to_terminal(self, message):
        self.terminal_output.append(message)
