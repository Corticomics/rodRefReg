# app/ui/DragDropArea.py

from PyQt5.QtWidgets import QListWidget, QListWidgetItem
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDrag

class DragDropArea(QListWidget):
    def __init__(self, db_manager, print_to_terminal, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.print_to_terminal = print_to_terminal
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.assigned_relays = {}

    def assign_relay(self, relay_pair, animal):
        self.assigned_relays[relay_pair] = animal
        self.add_animal(animal)

    def clear_assignments(self):
        self.assigned_relays.clear()
        self.clear()

    def get_assignments(self):
        return self.assigned_relays

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
            animal = self.db_manager.get_animal_by_id(animal_id)
            if animal:
                relay_pair = event.source().relay_pair  # RelayButton should have relay_pair attribute
                self.assign_relay(relay_pair, animal)
                self.print_to_terminal(f"Assigned Animal ID {animal_id} to Relay Pair {relay_pair}")
                event.acceptProposedAction()
        else:
            event.ignore()

    def add_animal(self, animal):
        item = QListWidgetItem(f"{animal.animal_id} - {animal.species}")
        self.addItem(item)

    def startDrag(self, supportedActions):
        selected_items = self.selectedItems()
        if selected_items:
            drag = QDrag(self)
            mime_data = QMimeData()
            animal_id = selected_items[0].text().split(' - ')[0]
            mime_data.setData('application/x-animal', animal_id.encode('utf-8'))
            drag.setMimeData(mime_data)
            drag.exec_(Qt.MoveAction)