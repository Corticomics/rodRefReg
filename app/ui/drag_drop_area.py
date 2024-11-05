# app/gui/drag_drop_area.py

from PyQt5.QtWidgets import QListWidget, QListWidgetItem
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDrag

class DragDropArea(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSelectionMode(QListWidget.MultiSelection)
        self.selected_animals = []

        self.parent_widget = parent  # Reference to the parent widget for accessing db_manager

    def add_animal(self, animal):
        item = QListWidgetItem(f"{animal.animal_id} - {animal.species} ({animal.body_weight}g)")
        item.setData(Qt.UserRole, animal)
        self.addItem(item)

    def clear(self):
        self.selected_animals = []
        super().clear()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            text = event.mimeData().text()
            # Assume the text format is "ID - Species"
            try:
                animal_id, species = text.split(' - ')
                animal_id = animal_id.strip()
                species = species.strip()
                # Fetch animal from database
                animal = self.parent_widget.db_manager.get_animal_by_id(animal_id)
                if animal:
                    self.selected_animals.append(animal)
                    self.add_animal(animal)
                    event.acceptProposedAction()
            except ValueError:
                pass  # Invalid format

    def startDrag(self, supportedActions):
        selected_items = self.selectedItems()
        if selected_items:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_text = "\n".join([item.text() for item in selected_items])
            mime_data.setText(mime_text)
            drag.setMimeData(mime_data)
            drag.exec_(Qt.MoveAction)