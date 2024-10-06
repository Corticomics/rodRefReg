# ui/styles.py

def get_default_styles():
    return """
        QWidget {
            background-color: #f8f9fa;
            font-size: 14px;
        }
        QGroupBox {
            background-color: #ffffff;
            border: 1px solid #ced4da;
            border-radius: 5px;
            padding: 15px;
        }
        QPushButton {
            background-color: #007bff;
            border: 1px solid #007bff;
            border-radius: 5px;
            color: #ffffff;
            padding: 10px;
        }
        QPushButton:disabled {
            background-color: #cccccc;
            color: #666666;
        }
        QPushButton:hover {
            background-color: #0056b3;
        }
        QLabel {
            color: #343a40;
            background-color: #ffffff;
        }
        QLineEdit, QTextEdit {
            background-color: #ffffff;
            border: 1px solid #ced4da;
            padding: 5px;
        }
    """
