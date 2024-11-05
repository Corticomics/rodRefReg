# app/ui/RelayButton.py

from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import Qt

class RelayButton(QPushButton):
    def __init__(self, relay_pair, parent=None):
        super().__init__(parent)
        self.relay_pair = relay_pair
        self.setAcceptDrops(True)
        self.setText(f"Relay {relay_pair[0]} & {relay_pair[1]}")
        self.setStyleSheet("background-color: #e0e0e0;")

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/x-animal'):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat('application/x-animal'):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasFormat('application/x-animal'):
            animal_id = event.mimeData().data('application/x-animal').data().decode('utf-8')
            self.parent().handle_drop(animal_id, self.relay_pair)
            event.acceptProposedAction()
        else:
            event.ignore()