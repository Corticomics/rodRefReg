# ui/animals_tab.py

import traceback
from datetime import datetime

from models.animal import Animal
from PyQt5.QtCore import QDateTime, Qt, pyqtProperty
from PyQt5.QtGui import QColor, QFont, QPen
from PyQt5.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStyle,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from utils.last_run_text import last_run_cell

from .edit_animal_dialog import EditAnimalDialog
from .style.theme import theme_colour

# Item data role marking a "Last schedule delivered amount" cell that is painted red.
LAST_RUN_ALERT_ROLE = Qt.UserRole + 1


class _LastRunDelegate(QStyledItemDelegate):
    """Paints a cell flagged with LAST_RUN_ALERT_ROLE as a filled red cell.

    The stylesheet pads every item, and the view lays a cell widget out inside
    that padding, so a red QLabel would fill only a thin band; an item's
    setBackground() is not painted under the stylesheet at all. Painting here
    fills the whole cell, selected or not. The colours are the tab's alertFill
    and alertText, which the theme stylesheets set. The text stays in the item,
    for the filter and the tooltip.
    """

    def __init__(self, tab):
        super().__init__(tab.animals_table)
        self._tab = tab

    def paint(self, painter, option, index):
        if not index.data(LAST_RUN_ALERT_ROLE):
            super().paint(painter, option, index)
            return
        painter.save()
        painter.fillRect(option.rect, self._tab.alertFill)
        if option.state & QStyle.State_Selected:
            # The table selects single cells, so a click here would otherwise show
            # nothing: a frame in the text colour marks it, and the cell stays red.
            painter.setPen(QPen(self._tab.alertText, 2))
            painter.drawRect(option.rect.adjusted(3, 3, -4, -4))
        font = QFont(option.font)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        painter.setPen(self._tab.alertText)
        rect = option.rect.adjusted(8, 0, -8, 0)
        # Cut short at the right, so the status word (Stopped...) always shows.
        text = painter.fontMetrics().elidedText(index.data(), Qt.ElideRight, rect.width())
        painter.drawText(rect, Qt.AlignCenter, text)
        painter.restore()


class AnimalsTab(QWidget):
    def __init__(self, settings, print_to_terminal, database_handler, login_system):
        super().__init__()
        # The red cell's colours, the theme's roles, until the theme stylesheet
        # sets them: the stylesheets style this widget by name (QWidget#AnimalsTab)
        # through qproperty-alertFill and qproperty-alertText.
        self._alert_fill = theme_colour("danger.alert")
        self._alert_text = theme_colour("danger.on-alert")
        self.setObjectName("AnimalsTab")
        self.settings = settings
        self.print_to_terminal = print_to_terminal or (lambda x: None)  # Fallback if not provided
        self.database_handler = database_handler
        self.login_system = login_system  # Store login_system for permission checks
        self.trainer_id = None  # Add this line back

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Section title - uses global QSS
        instruction_label = QLabel("Manage Animal Data")
        instruction_label.setObjectName("Title")
        self.layout.addWidget(instruction_label)

        # Filter section - uses global QSS
        filter_container = QWidget()
        filter_container.setObjectName("Card")
        filter_layout = QHBoxLayout(filter_container)

        filter_label = QLabel("Filter:")
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Search animals...")
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_input)
        self.layout.addWidget(filter_container)

        # Setup the table with modern styling
        self.animals_table = QTableWidget()
        self.animals_table.setColumnCount(len(self.COLUMN_WIDTHS))

        # Set headers with proper styling. A line break keeps a long header readable
        # in its column instead of cutting it off (the stylesheet capitalises headers).
        headers = [
            "Lab Animal\nID",
            "Name",
            "Sex",
            "Initial\nWeight (g)",
            "Last\nWeight",
            "Last Weighted",
            "Last Watering",
            "Last schedule\ndelivered amount",
        ]
        self.animals_table.setHorizontalHeaderLabels(headers)
        self.animals_table.horizontalHeaderItem(self.LAST_RUN_COLUMN).setToolTip(
            "Water each animal received in its last schedule run. "
            "Red: the run ended before the animal got its full amount."
        )
        self.animals_table.setItemDelegateForColumn(self.LAST_RUN_COLUMN, _LastRunDelegate(self))

        # Configure table properties with improved sizing
        # Use Fixed mode for all columns except the last one
        for i in range(len(self.COLUMN_WIDTHS)):
            self.animals_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Fixed)

        # Set specific column widths to ensure all information is visible
        self._apply_column_widths()

        # Make the last column stretch to fill available space
        self.animals_table.horizontalHeader().setStretchLastSection(True)

        # Set size policy to expand horizontally
        self.animals_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Set row height and hide vertical headers for cleaner look
        self.animals_table.verticalHeader().setDefaultSectionSize(40)  # Taller rows
        self.animals_table.verticalHeader().setVisible(False)  # Hide row numbers

        # Dynamic height based on content
        self.animals_table.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        self.animals_table.setMinimumHeight(150)  # More conservative minimum height
        self.animals_table.setMaximumHeight(400)  # Add maximum height to prevent excessive space

        # Enable horizontal scrolling if needed but make it fill container width
        self.animals_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.animals_table.setMinimumWidth(self.width())  # Make table full width of container

        # Table appearance - uses global QSS styles
        self.animals_table.setAlternatingRowColors(True)
        self.animals_table.setShowGrid(True)

        # Add table to layout with a title
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_label = QLabel("Animals")
        table_label.setObjectName("Subtitle")
        table_layout.addWidget(table_label)
        table_layout.addWidget(self.animals_table)
        self.layout.addWidget(table_container)

        # Action buttons with modern styling
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)

        add_button = QPushButton("Add Animal")
        edit_button = QPushButton("Edit")
        remove_button = QPushButton("Remove")

        for button in [add_button, edit_button, remove_button]:
            button.setMinimumWidth(100)
            button_layout.addWidget(button)

        button_layout.addStretch()
        self.layout.addWidget(button_container)

        # Connect signals
        add_button.clicked.connect(self.add_animal)
        edit_button.clicked.connect(self.edit_animal)
        remove_button.clicked.connect(self.remove_animal)
        self.filter_input.textChanged.connect(self.apply_filter)

        # Initial load
        self.load_animals()

    # Per-column widths (px), in header order; the last column (Last schedule
    # delivered amount) starts at its width and stretches to fill the rest. On
    # the Pi's 1920 x 1080 screen the tab is about 1114 px wide: every header
    # fits on one or two lines, "59 minutes ago" fits both time columns, and the
    # last column gets 252-262 px, room for "Incomplete · 0.800 / 0.991 mL"
    # (a longer red cell is cut short after its status word). Narrower screens
    # scroll sideways.
    COLUMN_WIDTHS = (120, 120, 90, 116, 92, 148, 148, 238)
    LAST_RUN_COLUMN = len(COLUMN_WIDTHS) - 1

    def _get_alert_fill(self):
        return self._alert_fill

    def _set_alert_fill(self, colour):
        self._alert_fill = QColor(colour)

    def _get_alert_text(self):
        return self._alert_text

    def _set_alert_text(self, colour):
        self._alert_text = QColor(colour)

    # Fill and text colour of a red "Last schedule delivered amount" cell. The
    # theme stylesheets set them; a theme switch sets them again and repaints.
    alertFill = pyqtProperty(QColor, _get_alert_fill, _set_alert_fill)
    alertText = pyqtProperty(QColor, _get_alert_text, _set_alert_text)

    def _apply_column_widths(self):
        """Re-assert the fixed column widths so the last column stretches to fill.

        Must run after every (re)populate. ``resizeColumnsToContents()`` used to
        run here instead, but it collapses every column to its content width —
        including the stretch column — leaving trailing whitespace on the right
        that only cleared on the next resize event (e.g. an app restart). Setting
        the fixed widths keeps ``setStretchLastSection(True)`` working on refresh.
        """
        for col, width in enumerate(self.COLUMN_WIDTHS):
            self.animals_table.setColumnWidth(col, width)

    def calculate_days_ago(self, timestamp_str):
        """Convert timestamp to 'X days ago' format"""
        if not timestamp_str:
            return "Never"
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            now = datetime.now()
            delta = now - timestamp

            if delta.days == 0:
                if delta.seconds < 3600:  # Less than an hour
                    minutes = delta.seconds // 60
                    return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
                else:
                    hours = delta.seconds // 3600
                    return f"{hours} hour{'s' if hours != 1 else ''} ago"
            elif delta.days == 1:
                return "Yesterday"
            else:
                return f"{delta.days} days ago"
        except (ValueError, TypeError):
            return "Invalid date"

    def _when(self, timestamp):
        """When a run started or ended, for its tooltip: '2 hours ago (2026-10-09 07:00)'.

        Only 'at 2026-10-09 07:00' when the stored time is ahead of the clock (the
        Pi has no real-time clock), and 'at an unknown time' when it cannot be read.
        """
        try:
            moment = datetime.fromisoformat(timestamp)
            at = moment.strftime('%Y-%m-%d %H:%M')
        except (TypeError, ValueError):
            return "at an unknown time"
        try:
            past = moment <= datetime.now()
        except TypeError:  # a time with a UTC offset; RRR stores local times without one
            past = False
        if not past:
            return f"at {at}"
        ago = self.calculate_days_ago(timestamp)
        return f"{ago[0].lower()}{ago[1:]} ({at})"

    def _selected_animal_id(self):
        """The animal_id of the row Edit and Remove would act on, or None."""
        item = self.animals_table.item(self.animals_table.currentRow(), 0)
        animal = item.data(Qt.UserRole) if item is not None else None
        return getattr(animal, 'animal_id', None)

    def populate_animal_table(self, animals):
        """Populate the animals_table widget with the given animals."""
        # The table also reloads on its own (a schedule ended, the tab was
        # selected): keep the operator's selection, which a reload clears.
        selected_id = self._selected_animal_id()
        selected_column = max(self.animals_table.currentColumn(), 0)
        self.animals_table.setRowCount(0)  # Clear existing rows

        for animal in animals:
            row_position = self.animals_table.rowCount()
            self.animals_table.insertRow(row_position)

            # Convert timestamps to "X days ago" format
            last_weighted_text = self.calculate_days_ago(animal.last_weighted)
            last_watering_text = self.calculate_days_ago(animal.last_watering)

            lab_animal_id_item = QTableWidgetItem(animal.lab_animal_id)
            name_item = QTableWidgetItem(animal.name)
            sex_item = QTableWidgetItem(animal.sex if animal.sex else "N/A")
            initial_weight_item = QTableWidgetItem(
                f"{animal.initial_weight:.1f}" if animal.initial_weight else "N/A"
            )
            last_weight_item = QTableWidgetItem(
                f"{animal.last_weight:.1f}" if animal.last_weight else "N/A"
            )
            last_weighted_item = QTableWidgetItem(last_weighted_text)
            last_watering_item = QTableWidgetItem(last_watering_text)
            # The animal's latest schedule run; the delegate paints the red ones.
            text, tooltip, alert = last_run_cell(animal.last_run, self._when)
            last_run_item = QTableWidgetItem(text)
            last_run_item.setToolTip(tooltip)
            last_run_item.setData(LAST_RUN_ALERT_ROLE, alert)
            last_run_item.setFlags(last_run_item.flags() & ~Qt.ItemIsEditable)

            # Set items in table
            self.animals_table.setItem(row_position, 0, lab_animal_id_item)
            self.animals_table.setItem(row_position, 1, name_item)
            self.animals_table.setItem(row_position, 2, sex_item)
            self.animals_table.setItem(row_position, 3, initial_weight_item)
            self.animals_table.setItem(row_position, 4, last_weight_item)
            self.animals_table.setItem(row_position, 5, last_weighted_item)
            self.animals_table.setItem(row_position, 6, last_watering_item)
            self.animals_table.setItem(row_position, self.LAST_RUN_COLUMN, last_run_item)

            # Center-align text for better readability
            for col in range(len(self.COLUMN_WIDTHS)):
                item = self.animals_table.item(row_position, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)

            # Store the original timestamp in the item's data for sorting
            last_weighted_item.setData(Qt.UserRole, animal.last_weighted or "")
            last_watering_item.setData(Qt.UserRole, animal.last_watering or "")

            lab_animal_id_item.setData(Qt.UserRole, animal)

            # Set fixed row height for better appearance
            self.animals_table.setRowHeight(row_position, 40)

        # Re-assert fixed column widths so the last column stretches to fill the
        # remaining width on every refresh (not just the initial load).
        self._apply_column_widths()

        # Keep the operator's filter, then their animal if the filter shows it.
        self.apply_filter(self.filter_input.text())
        if selected_id is not None:
            self._select_animal(selected_id, selected_column)

    def _select_animal(self, animal_id, column):
        """Make the row of animal ``animal_id`` current, unless the filter hides it."""
        for row in range(self.animals_table.rowCount()):
            animal = self.animals_table.item(row, 0).data(Qt.UserRole)
            if getattr(animal, 'animal_id', None) == animal_id:
                if not self.animals_table.isRowHidden(row):
                    self.animals_table.setCurrentCell(row, column)
                return

    def load_animals(self):
        """Load animals from the database, filtered by trainer_id if available."""
        try:
            current_trainer = self.login_system.get_current_trainer()
            if current_trainer:
                trainer_id = current_trainer['trainer_id']
                role = current_trainer['role']
                animals = self.database_handler.get_animals(trainer_id, role)
                if self.print_to_terminal:
                    self.print_to_terminal(
                        f"Loaded {len(animals)} animals for trainer ID {trainer_id}"
                    )
            else:
                animals = self.database_handler.get_all_animals()
                if self.print_to_terminal:
                    self.print_to_terminal(
                        f"Loaded {len(animals)} animals for all trainers (guest mode)"
                    )
            # Populate the UI with the animals table
            self.populate_animal_table(animals)
        except Exception as e:
            if self.print_to_terminal:
                self.print_to_terminal(f"Error loading animals: {str(e)}")
            traceback.print_exc()
            QMessageBox.critical(
                self, "Load Animals Error", f"An error occurred while loading animals:\n{e}"
            )

    def apply_filter(self, text):
        """Filter the animals in the table based on the input text."""
        for row in range(self.animals_table.rowCount()):
            match = False
            for column in range(self.animals_table.columnCount()):
                item = self.animals_table.item(row, column)
                if item is not None and text.lower() in item.text().lower():
                    match = True
                    break
            self.animals_table.setRowHidden(row, not match)

    def add_animal(self):
        """Open dialog to add a new animal with error handling."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Animal")
        layout = QVBoxLayout()
        form_layout = QFormLayout()

        lab_animal_id_input = QLineEdit()
        name_input = QLineEdit()
        initial_weight_input = QLineEdit()
        last_weight_input = QLineEdit()
        last_weighted_input = QDateTimeEdit()
        last_weighted_input.setCalendarPopup(True)
        last_weighted_input.setDateTime(QDateTime.currentDateTime())
        last_watering_input = QDateTimeEdit()
        last_watering_input.setCalendarPopup(True)
        last_watering_input.setDateTime(QDateTime.currentDateTime())

        # Add sex selection combo box
        sex_combo = QComboBox()
        sex_combo.addItems(["Select Sex", "male", "female"])
        sex_combo.setCurrentText("Select Sex")

        form_layout.addRow("Lab Animal ID:", lab_animal_id_input)
        form_layout.addRow("Name:", name_input)
        form_layout.addRow("Initial Weight (g):", initial_weight_input)
        form_layout.addRow("Last Weight (g):", last_weight_input)
        form_layout.addRow("Last Time Weighted:", last_weighted_input)
        form_layout.addRow("Last Watering:", last_watering_input)
        form_layout.addRow("Sex:", sex_combo)
        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.setLayout(layout)

        if dialog.exec_() == QDialog.Accepted:
            try:
                lab_animal_id = lab_animal_id_input.text().strip()
                name = name_input.text().strip()
                initial_weight_text = initial_weight_input.text().strip()
                last_weight_text = last_weight_input.text().strip()
                last_weighted = last_weighted_input.dateTime().toString("yyyy-MM-dd HH:mm")
                last_watering = last_watering_input.dateTime().toString("yyyy-MM-dd HH:mm")
                sex = sex_combo.currentText()
                if sex == "Select Sex":
                    sex = None

                # Validate inputs
                if not lab_animal_id or not name:
                    raise ValueError("Animal ID and name cannot be empty.")
                if not initial_weight_text:
                    raise ValueError("Initial weight cannot be empty.")
                initial_weight = float(initial_weight_text)
                last_weight = float(last_weight_text) if last_weight_text else None

                new_animal = Animal(
                    None,
                    lab_animal_id,
                    name,
                    initial_weight,
                    last_weight,
                    last_weighted,
                    last_watering,
                    sex,
                )
                current_trainer = self.login_system.get_current_trainer()
                trainer_id = current_trainer['trainer_id'] if current_trainer else None

                animal_id = self.database_handler.add_animal(new_animal, trainer_id=trainer_id)

                if animal_id:
                    self.print_to_terminal(f"Animal '{name}' added with ID: {lab_animal_id}.")
                    self.load_animals()
                    self.notify_schedules_tab()  # Notify schedules tab of the change
                else:
                    QMessageBox.warning(
                        self, "Add Error", "Failed to add animal. ID might already exist."
                    )

            except ValueError as ve:
                QMessageBox.warning(self, "Input Error", f"Invalid input: {ve}")
                self.print_to_terminal(f"Input Error: {ve}")
            except Exception as e:
                QMessageBox.critical(self, "Add Error", f"Unexpected error: {e}")
                self.print_to_terminal(f"Unexpected error during add operation: {e}")

    def remove_animal(self):
        """Remove selected animal from the database with error handling."""
        selected_row = self.animals_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an animal to remove.")
            return

        # Retrieve the Animal object from the selected row
        lab_animal_id_item = self.animals_table.item(selected_row, 0)
        animal = lab_animal_id_item.data(Qt.UserRole)

        confirm = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove '{animal.name}' (Lab ID: {animal.lab_animal_id})?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            try:
                self.database_handler.remove_animal(animal.lab_animal_id)
                self.print_to_terminal(
                    f"Removed animal '{animal.name}' with Lab ID {animal.lab_animal_id}."
                )
                self.load_animals()
            except Exception as e:
                QMessageBox.critical(self, "Remove Error", f"Error removing animal: {e}")
                self.print_to_terminal(f"Error removing animal '{animal.lab_animal_id}': {e}")

    def edit_animal(self):
        """Open dialog to edit the selected animal's information with error handling."""
        selected_row = self.animals_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an animal to edit.")
            return

        # Retrieve the Animal object from the selected row
        lab_animal_id_item = self.animals_table.item(selected_row, 0)
        animal = lab_animal_id_item.data(Qt.UserRole)

        # Pass `lab_animal_id` and other details to the EditAnimalDialog
        dialog = EditAnimalDialog(animal.animal_id, animal.to_dict(), self)

        try:
            if dialog.exec_() == QDialog.Accepted:
                updated_info = dialog.updated_info
                updated_animal = Animal(
                    animal_id=animal.animal_id,
                    lab_animal_id=animal.lab_animal_id,
                    name=updated_info['name'],
                    initial_weight=updated_info['initial_weight'],
                    last_weight=updated_info['last_weight'],
                    last_weighted=updated_info['last_weighted'],
                    last_watering=updated_info['last_watering'],
                    sex=updated_info['sex'],
                )

                # Update the animal in the database
                self.database_handler.update_animal(updated_animal)

                # Notify and refresh
                self.print_to_terminal(
                    f"Updated animal '{updated_animal.name}' (Lab ID: {updated_animal.lab_animal_id})."
                )
                self.load_animals()
                self.notify_schedules_tab()  # Notify schedules tab of the change
        except Exception as e:
            QMessageBox.critical(self, "Edit Error", f"Error updating animal: {e}")
            self.print_to_terminal(f"Unhandled exception in edit_animal: {e}")

    def notify_schedules_tab(self):
        """Notify the schedules tab that animals have been updated"""
        try:
            # Find the parent widget and access the schedules_tab
            parent = self.parent()
            while parent and not hasattr(parent, 'schedules_tab'):
                parent = parent.parent()

            if parent and hasattr(parent, 'schedules_tab'):
                parent.schedules_tab.refresh()
                self.print_to_terminal("Refreshed schedules tab after animal update")
        except Exception as e:
            self.print_to_terminal(f"Error refreshing schedules tab: {e}")
            traceback.print_exc()

    def resizeEvent(self, event):
        """Handle resize events to adjust table width to match container"""
        super().resizeEvent(event)
        # Update table width to match container width
        if hasattr(self, 'animals_table'):
            available_width = self.width() - 20  # Account for layout margins
            self.animals_table.setMinimumWidth(available_width)

            # Force update
            self.animals_table.updateGeometry()
