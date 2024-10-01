from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QProgressBar

class ProgressWindow(QWidget):
    def __init__(self, total_steps):
        super().__init__()
        self.setWindowTitle("Installation Progress")
        self.init_ui(total_steps)

    def init_ui(self, total_steps):
        layout = QVBoxLayout()

        self.progress_label = QLabel("Starting installation...")
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(total_steps)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    def update_progress(self, step, message):
        self.progress_bar.setValue(step)
        self.progress_label.setText(message)
        self.repaint()
