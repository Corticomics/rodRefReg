# app/ui/drag_drop_area.py

from PyQt5.QtWidgets import QListWidget, QListWidgetItem
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDrag

class DragDropArea(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.selected_animals = []
        self.assigned_animals = {}  # Mapping relay pairs to animal IDs

    def add_animal(self, animal):
        item = QListWidgetItem(f"{animal.animal_id} - {animal.species}")
        item.setData(Qt.UserRole, animal)
        self.addItem(item)

    def clear_selection(self):
        self.clear()
        self.assigned_animals.clear()

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
            animal = self.parent().db_manager.get_animal_by_id(animal_id)
            if animal:
                # Determine where the animal is dropped
                target = event.source()
                relay_pair = self.parent().schedules_tab.relay_buttons.get(target, None)
                if relay_pair:
                    self.assigned_animals[relay_pair] = animal
                    self.parent().print_to_terminal(f"Assigned Animal ID {animal_id} to Relay Pair {relay_pair}")
                    event.acceptProposedAction()
        else:
            event.ignore()

    def startDrag(self, supportedActions):
        selected_items = self.selectedItems()
        if selected_items:
            drag = QDrag(self)
            mime_data = QMimeData()
            animal_id = selected_items[0].data(Qt.UserRole).animal_id
            mime_data.setData('application/x-animal', animal_id.encode('utf-8'))
            drag.setMimeData(mime_data)
            drag.exec_(Qt.MoveAction)