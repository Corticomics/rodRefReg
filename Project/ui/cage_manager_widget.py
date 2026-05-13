# ui/cage_manager_widget.py
"""
Cage Manager Widget - UI for editing cage names and descriptions.

Design Principles:
- Table-based editing for efficiency (all cages visible at once)
- Inline editing with immediate save feedback
- Visual indication of relay architecture alignment
- Searchable/filterable for large cage counts

Architecture:
- Uses QTableWidget for row-based editing
- Connects to database_handler for persistence
- Syncs with system_controller for hardware configuration

Reference: 
- PyQt5 QTableWidget Documentation
- Qt Model/View Programming Guide
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QLabel, QLineEdit, QGroupBox, QMessageBox,
    QFrame, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush


class CageManagerWidget(QWidget):
    """
    Widget for managing cage names and descriptions.
    
    Features:
    - View all cages in a table format
    - Edit cage names inline
    - Edit descriptions inline
    - Visual relay ID mapping
    - Search/filter functionality
    
    Signals:
        cage_updated(int, str): Emitted when a cage name is changed (cage_id, new_name)
        
    Args:
        database_handler: DatabaseHandler instance for persistence
        system_controller: SystemController for hardware config (optional)
    """
    
    cage_updated = pyqtSignal(int, str)  # cage_id, new_name
    
    def __init__(self, database_handler, system_controller=None, parent=None):
        super().__init__(parent)
        self._database_handler = database_handler
        self._system_controller = system_controller
        
        # Get hardware limits
        self._num_hats = 1
        self._master_relay = 16
        if system_controller and hasattr(system_controller, 'settings'):
            self._num_hats = int(system_controller.settings.get('num_hats', 1))
            self._master_relay = int(system_controller.settings.get('global_master_relay_id', 16))
        
        self._init_ui()
        self._load_cages()
    
    def _init_ui(self) -> None:
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Header with info
        header_container = QFrame()
        header_container.setObjectName("CageManagerHeader")
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(8)
        
        title = QLabel("Cage Names Configuration")
        title.setObjectName("SectionTitle")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #1F2937;")
        header_layout.addWidget(title)
        
        info_label = QLabel(
            f"Configure friendly names for your {15 * self._num_hats} cages. "
            f"Relay {self._master_relay} is reserved for the master solenoid."
        )
        info_label.setStyleSheet("color: #6B7280; font-size: 12px;")
        info_label.setWordWrap(True)
        header_layout.addWidget(info_label)
        
        layout.addWidget(header_container)
        
        # Search/filter bar
        search_container = QHBoxLayout()
        search_container.setContentsMargins(16, 0, 16, 0)
        
        search_label = QLabel("🔍 Filter:")
        search_label.setStyleSheet("color: #4B5563;")
        search_container.addWidget(search_label)
        
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Type to filter cages...")
        self._search_input.textChanged.connect(self._filter_cages)
        self._search_input.setMaximumWidth(300)
        search_container.addWidget(self._search_input)
        
        search_container.addStretch()
        
        # Reset button
        reset_btn = QPushButton("Reset All to Defaults")
        reset_btn.setObjectName("DangerButton")
        reset_btn.clicked.connect(self._reset_all_names)
        search_container.addWidget(reset_btn)
        
        layout.addLayout(search_container)
        
        # Table for cage editing
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Cage #", "Relay", "Name", "Description"])
        
        # Configure table appearance
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # Cage #
        header.setSectionResizeMode(1, QHeaderView.Fixed)  # Relay
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Name
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Description
        
        self._table.setColumnWidth(0, 70)
        self._table.setColumnWidth(1, 60)
        
        # Make Cage # and Relay columns read-only (handled in itemChanged)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        
        # Connect change handler
        self._table.itemChanged.connect(self._on_item_changed)
        
        # Styling
        self._table.setStyleSheet("""
            QTableWidget {
                gridline-color: #E5E7EB;
                background-color: #FFFFFF;
                alternate-background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #DBEAFE;
                color: #1E40AF;
            }
            QHeaderView::section {
                background-color: #F3F4F6;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #E5E7EB;
                font-weight: 600;
                color: #374151;
            }
        """)
        
        layout.addWidget(self._table, 1)
        
        # Bottom info bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(16, 0, 16, 8)
        
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #059669; font-size: 12px;")
        bottom_bar.addWidget(self._status_label)
        
        bottom_bar.addStretch()
        
        layout.addLayout(bottom_bar)
    
    def _load_cages(self) -> None:
        """Load cage data from database and populate table."""
        # Block signals during load to prevent spurious saves
        self._table.blockSignals(True)
        
        # Initialize defaults if needed
        self._database_handler.initialize_default_cage_names(
            self._num_hats, 
            self._master_relay
        )
        
        # Get all cages for dropdown
        cages = self._database_handler.get_cages_for_dropdown(
            self._num_hats,
            self._master_relay
        )
        
        self._table.setRowCount(len(cages))
        
        for row, cage_data in enumerate(cages):
            cage_id = cage_data['cage_id']
            relay_id = cage_data['relay_id']
            name = cage_data['name']
            description = cage_data.get('description', '')
            
            # Cage # (read-only)
            cage_item = QTableWidgetItem(str(cage_id))
            cage_item.setFlags(cage_item.flags() & ~Qt.ItemIsEditable)
            cage_item.setTextAlignment(Qt.AlignCenter)
            cage_item.setData(Qt.UserRole, cage_id)  # Store cage_id for later use
            cage_item.setBackground(QBrush(QColor("#F3F4F6")))
            self._table.setItem(row, 0, cage_item)
            
            # Relay (read-only)
            relay_item = QTableWidgetItem(f"R{relay_id}")
            relay_item.setFlags(relay_item.flags() & ~Qt.ItemIsEditable)
            relay_item.setTextAlignment(Qt.AlignCenter)
            relay_item.setData(Qt.UserRole, relay_id)  # Store relay_id
            relay_item.setBackground(QBrush(QColor("#F3F4F6")))
            self._table.setItem(row, 1, relay_item)
            
            # Name (editable)
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.UserRole, cage_id)  # Store cage_id
            self._table.setItem(row, 2, name_item)
            
            # Description (editable)
            desc_item = QTableWidgetItem(description)
            desc_item.setData(Qt.UserRole, cage_id)  # Store cage_id
            self._table.setItem(row, 3, desc_item)
        
        self._table.blockSignals(False)
        self._status_label.setText(f"Loaded {len(cages)} cages")
    
    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        """Handle cell edit and save to database."""
        column = item.column()
        
        # Only handle Name (col 2) and Description (col 3) edits
        if column not in [2, 3]:
            return
        
        row = item.row()
        
        # Get cage_id from the first column's UserRole data
        cage_item = self._table.item(row, 0)
        if not cage_item:
            return
        
        cage_id = cage_item.data(Qt.UserRole)
        relay_item = self._table.item(row, 1)
        relay_id = relay_item.data(Qt.UserRole) if relay_item else cage_id
        
        # Get current name and description
        name_item = self._table.item(row, 2)
        desc_item = self._table.item(row, 3)
        
        name = name_item.text().strip() if name_item else f"Cage {cage_id}"
        description = desc_item.text().strip() if desc_item else ""
        
        # If name is empty, use default
        if not name:
            name = f"Cage {cage_id}"
            # Update item without triggering signal
            self._table.blockSignals(True)
            name_item.setText(name)
            self._table.blockSignals(False)
        
        # Save to database
        success = self._database_handler.set_cage_name(
            cage_id=cage_id,
            relay_id=relay_id,
            name=name,
            description=description
        )
        
        if success:
            self._status_label.setText(f"✓ Saved: Cage {cage_id} → '{name}'")
            self._status_label.setStyleSheet("color: #059669; font-size: 12px;")
            self.cage_updated.emit(cage_id, name)
        else:
            self._status_label.setText(f"✗ Error saving Cage {cage_id}")
            self._status_label.setStyleSheet("color: #DC2626; font-size: 12px;")
    
    def _filter_cages(self, text: str) -> None:
        """Filter table rows based on search text."""
        search = text.lower().strip()
        
        for row in range(self._table.rowCount()):
            # Check if search matches cage #, name, or description
            cage_item = self._table.item(row, 0)
            name_item = self._table.item(row, 2)
            desc_item = self._table.item(row, 3)
            
            cage_text = cage_item.text().lower() if cage_item else ""
            name_text = name_item.text().lower() if name_item else ""
            desc_text = desc_item.text().lower() if desc_item else ""
            
            matches = (
                not search or
                search in cage_text or
                search in name_text or
                search in desc_text or
                search in f"cage {cage_text}"
            )
            
            self._table.setRowHidden(row, not matches)
    
    def _reset_all_names(self) -> None:
        """Reset all cage names to defaults after confirmation."""
        reply = QMessageBox.question(
            self,
            "Reset Cage Names",
            "This will reset ALL cage names to defaults (Cage 1, Cage 2, etc.).\n\n"
            "This action cannot be undone. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Delete all custom names
        for row in range(self._table.rowCount()):
            cage_item = self._table.item(row, 0)
            if cage_item:
                cage_id = cage_item.data(Qt.UserRole)
                self._database_handler.delete_cage_name(cage_id)
        
        # Reload (which will re-initialize defaults)
        self._load_cages()
        self._status_label.setText("All cage names reset to defaults")
    
    def refresh(self) -> None:
        """Refresh the cage list from database."""
        self._load_cages()

