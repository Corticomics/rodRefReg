from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel

class ProfileDialog(QDialog):
    def __init__(self, trainer_id, db_handler):
        super().__init__()
        self.trainer_id = trainer_id
        self.db_handler = db_handler
        self.setWindowTitle("Trainer Profile")

        layout = QVBoxLayout()
        trainer_info = self.db_handler.get_trainer_info(trainer_id)
        
        layout.addWidget(QLabel(f"Trainer ID: {trainer_info['trainer_id']}"))
        layout.addWidget(QLabel(f"Name: {trainer_info['trainer_name']}"))
        layout.addWidget(QLabel(f"Email: {trainer_info['email']}"))
        self.setLayout(layout)