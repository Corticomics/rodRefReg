# ui/available_animals_list.py

from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QLabel
from PyQt5.QtGui import QDrag, QPixmap, QPainter, QColor, QFont, QLinearGradient, QPen
from PyQt5.QtCore import Qt, QMimeData, QByteArray, QDataStream, QIODevice, QRect, QSize, QPoint

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
        
        # Set compact style for the list
        self.setStyleSheet("""
            QListWidget {
                border: 1px solid #e0e4e8;
                border-radius: 4px;
                padding: 1px;
                font-size: 11px;
                background-color: white;
            }
            QListWidget::item {
                padding: 2px;
                border-bottom: 1px solid #f0f0f0;
                min-height: 18px;
            }
            QListWidget::item:selected {
                background-color: #e8f0fe;
                color: #1a73e8;
            }
        """)
        
        # Reduce item spacing
        self.setSpacing(0)
        
        # Set uniform item sizes for better performance and consistency
        self.setUniformItemSizes(True)

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

        # Create a visual representation for the drag operation
        # Create a pixmap for the drag image
        text = f"{animal.lab_animal_id} - {animal.name}"
        
        # Create a nicer looking drag pixmap
        pixmap = QPixmap(300, 60)  # Fixed size for the drag image
        pixmap.fill(Qt.transparent)  # Start with transparent background
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw rounded rectangle background with gradient
        gradient = QLinearGradient(0, 0, 0, 60)
        gradient.setColorAt(0, QColor("#e8f0fe"))
        gradient.setColorAt(1, QColor("#c2d9fc"))
        
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor("#1a73e8"), 2))  # Blue border
        painter.drawRoundedRect(0, 0, pixmap.width(), pixmap.height(), 10, 10)
        
        # Draw the animal information
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        painter.setPen(QColor("#1a73e8"))  # Blue text
        painter.drawText(QRect(10, 5, pixmap.width() - 20, 25), Qt.AlignLeft | Qt.AlignVCenter, text)
        
        # Draw a "dragging" indicator
        painter.setFont(QFont("Arial", 9))
        painter.setPen(QColor("#5f6368"))  # Gray text
        painter.drawText(QRect(10, 30, pixmap.width() - 20, 25), Qt.AlignLeft | Qt.AlignVCenter, "Dragging to assign...")
        
        painter.end()

        # Initiate the drag with the visual representation
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))  # Center the pixmap on the cursor
        drag.exec_(Qt.MoveAction)

    def create_available_animal_item(self, animal):
        """Create a QListWidgetItem for the given animal."""
        # Show ID and short name (first 10 chars)
        short_name = animal.name[:10] + ".." if len(animal.name) > 10 else animal.name
        item = QListWidgetItem(f"{animal.lab_animal_id} | {short_name}")
        
        # Add the name as tooltip for when users hover
        item.setToolTip(f"ID: {animal.lab_animal_id}\nName: {animal.name}\nLast Watering: {animal.last_watering or 'N/A'}")
        
        item.setData(Qt.UserRole, animal)
        return item