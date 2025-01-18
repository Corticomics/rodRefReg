from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QListWidget, QListWidgetItem
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDrag

class DragDropContainer(QGroupBox):
    def __init__(self, relay_pair):
        super().__init__()
        self.relay_pair = relay_pair
        self.setTitle(f"Relay {relay_pair[0]} & {relay_pair[1]}")
        self.layout = QVBoxLayout(self)

        # List for animals
        self.animal_list = QListWidget()
        self.animal_list.setAcceptDrops(True)
        self.animal_list.setDragEnabled(True)
        self.animal_list.setDragDropMode(QListWidget.InternalMove)
        self.animal_list.setDefaultDropAction(Qt.MoveAction)
        self.animal_list.dragEnterEvent = self.drag_enter_event
        self.animal_list.dropEvent = self.drop_event
        self.layout.addWidget(self.animal_list)

    def add_animal(self, animal_name, animal_id):
        item = QListWidgetItem(animal_name)
        item.setData(Qt.UserRole, animal_id)
        self.animal_list.addItem(item)

    def get_animal_ids(self):
        return [self.animal_list.item(i).data(Qt.UserRole) for i in range(self.animal_list.count())]

    def drag_enter_event(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def drop_event(self, event):
        if event.mimeData().hasText():
            source = event.source()
            if source and source != self.animal_list:
                # Move animal item to this container
                item = source.takeItem(source.currentRow())
                self.animal_list.addItem(item.clone())
                event.acceptProposedAction()