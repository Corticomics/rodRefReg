# ui/available_animals_list.py

from PyQt5.QtWidgets import QListWidget, QListWidgetItem
from PyQt5.QtGui import QDrag
from PyQt5.QtCore import Qt, QMimeData, QByteArray, QDataStream, QIODevice

class AvailableAnimalsList(QListWidget):
    def __init__(self, database_handler, parent=None):
        """
        Initialize the AvailableAnimalsList widget.
        
        Args:
            database_handler (DatabaseHandler): Reference to the database handler
            parent (QWidget, optional): Parent widget
        """
        super().__init__(parent)  # Pass only parent to QListWidget
        self.database_handler = database_handler  # Store database_handler as an instance attribute
        self.setDragEnabled(True)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setDefaultDropAction(Qt.MoveAction)

    def startDrag(self, supportedActions):
        selected_items = self.selectedItems()
        if not selected_items:
            return
        item = selected_items[0]
        animal = item.data(Qt.UserRole)
        if not animal:
            return

        # Create mime data with the animal_id
        mime_data = QMimeData()
        data = QByteArray()
        stream = QDataStream(data, QIODevice.WriteOnly)
        stream.writeInt32(animal.animal_id)  # Serialize the animal_id
        mime_data.setData('application/x-animal-id', data)

        # Initiate the drag
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec_(Qt.MoveAction)

    def create_available_animal_item(self, animal):
        """Create a QListWidgetItem for the given animal."""
        item = QListWidgetItem(f"{animal.lab_animal_id} - {animal.name} - Last Watering: {animal.last_watering or 'N/A'}")
        item.setData(Qt.UserRole, animal)
        return item