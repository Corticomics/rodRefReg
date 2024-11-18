# In a new file or within schedules_tab.py
from PyQt5.QtWidgets import QListWidget
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from PyQt5.QtCore import Qt, QPropertyAnimation, QSize

class RelayContainer(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if self.count() == 0:
            self.setStyleSheet("QListWidget { background-color: #cceeff; }")
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("QListWidget { background-color: #f0f0f0; }")
        event.accept()



    def dropEvent(self, event: QDropEvent):
        if self.count() == 0:
            super().dropEvent(event)
            self.setStyleSheet("QListWidget { background-color: #f0f0f0; }")
            # Animate the item
            item = self.item(0)
            animation = QPropertyAnimation(item, b"size")
            animation.setDuration(500)
            animation.setStartValue(QSize(0, 0))
            animation.setEndValue(QSize(self.width(), self.height()))
            animation.start()
        else:
            event.ignore()