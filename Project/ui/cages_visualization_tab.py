# ui/cages_visualization_tab.py
"""
Cages Visualization Tab - Visual representation of the physical relay HAT board.

Shows the actual 16-relay HAT layout so users can understand which physical
relay terminal corresponds to which cage.

Physical Layout (SM16relind HAT):
- Left side (top to bottom): R1, R2, R3, R4, R5, R6, R7, R8
- Right side (top to bottom): R16 (master), R15, R14, R13, R12, R11, R10, R9
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QPushButton, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap
from typing import Optional, Dict, Any
import os


class RelayTerminalWidget(QFrame):
    """
    Represents a single relay terminal on the physical board.
    
    Design rationale:
    - Fixed height ensures consistent visual rhythm (per Material Design spacing guidelines)
    - Horizontal layout with clear hierarchy: ID → Name → Status
    - Color-coded border indicates relay type (cage vs master)
    
    Reference: Qt Documentation - QFrame Class
    https://doc.qt.io/qt-5/qframe.html
    "QFrame is used to create raised or sunken borders and as a container for other widgets"
    """
    
    clicked = pyqtSignal(int)
    
    def __init__(self, relay_id: int, cage_data: Optional[Dict[str, Any]] = None, 
                 is_master: bool = False, parent=None):
        super().__init__(parent)
        self._relay_id = relay_id
        self._cage_data = cage_data
        self._is_master = is_master
        self._init_ui()
    
    def _init_ui(self) -> None:
        """
        Build the terminal widget UI.
        
        Layout structure:
        [Relay#] | [Cage Name] [●]
        
        Sizing rationale:
        - fixedHeight(48): Provides adequate touch target (48dp per Material Design)
        - No maxHeight constraint: Allows proper text rendering without clipping
        
        Reference: Qt Documentation - Layout Management
        https://doc.qt.io/qt-5/layout.html
        "Widgets in a layout are children of the widget on which the layout is installed"
        """
        # Set object name for QSS styling
        # Reference: https://doc.qt.io/qt-5/stylesheet-syntax.html#selector-types
        # "The ID Selector matches the widget with the object name set via setObjectName()"
        self.setObjectName("MasterTerminal" if self._is_master else "RelayTerminal")
        
        self.setCursor(Qt.PointingHandCursor)
        
        # Fixed height for consistent visual rhythm
        # Reference: https://doc.qt.io/qt-5/qwidget.html#setFixedHeight
        # "Sets both the minimum and maximum heights to h"
        self.setFixedHeight(48)
        
        # Size policy: Expand horizontally, fixed vertically
        # Reference: https://doc.qt.io/qt-5/qsizepolicy.html#Policy-enum
        # "Preferred: sizeHint() is best, but widget can be shrunk/grown"
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        layout = QHBoxLayout(self)
        # Margins: adequate padding for readability
        # Reference: https://doc.qt.io/qt-5/qlayout.html#setContentsMargins
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)
        
        # ─── Relay Number Badge ───
        relay_label = QLabel(f"R{self._relay_id}")
        relay_label.setObjectName("RelayNumber")
        relay_label.setAlignment(Qt.AlignCenter)
        relay_label.setFixedWidth(36)
        layout.addWidget(relay_label)
        
        # ─── Cage Name (primary content) ───
        if self._is_master:
            name_label = QLabel("MASTER SOLENOID")
            name_label.setObjectName("MasterLabel")
        elif self._cage_data:
            cage_id = self._cage_data.get('cage_id', 0)
            cage_name = self._cage_data.get('name', f'Cage {cage_id}')
            
            # Only show custom names, or fallback to "Cage X"
            # Avoid redundant display like "Cage 1 / Cage 1"
            display_name = cage_name if cage_name != f'Cage {cage_id}' else f'Cage {cage_id}'
            
            name_label = QLabel(display_name)
            name_label.setObjectName("CageNameLabel")
            
            # Truncate with ellipsis for long names
            # Reference: https://doc.qt.io/qt-5/qwidget.html#toolTip-prop
            if len(display_name) > 24:
                name_label.setText(display_name[:22] + "…")
                name_label.setToolTip(display_name)
        else:
            name_label = QLabel("—")  # Em dash for unassigned
            name_label.setObjectName("UnassignedLabel")
        
        layout.addWidget(name_label, 1)  # stretch=1 to fill available space
        
        # ─── Status Indicator ───
        status_dot = QLabel("●")
        status_dot.setObjectName("MasterStatusDot" if self._is_master else "StatusDot")
        layout.addWidget(status_dot)
    
    def mousePressEvent(self, event):
        """
        Handle mouse click.
        
        Reference: https://doc.qt.io/qt-5/qwidget.html#mousePressEvent
        "This event handler is called when a mouse button is pressed"
        """
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._relay_id)
        super().mousePressEvent(event)
    
    @property
    def relay_id(self) -> int:
        return self._relay_id


class CagesVisualizationTab(QWidget):
    """
    Tab displaying the physical relay HAT board layout.
    
    Architecture:
    - Two-column terminal list flanking center board image
    - Each column matches physical terminal positions on the HAT
    - Visual indicators help non-experts understand wiring
    
    Reference: Qt Documentation - QWidget Class
    https://doc.qt.io/qt-5/qwidget.html
    """
    
    cage_selected = pyqtSignal(int)
    
    def __init__(self, database_handler, system_controller=None, 
                 print_to_terminal=None, parent=None):
        super().__init__(parent)
        self._database_handler = database_handler
        self._system_controller = system_controller
        self._print_to_terminal = print_to_terminal or (lambda x: None)
        
        # Hardware configuration
        self._num_hats = 1
        self._master_relay = 16
        if system_controller and hasattr(system_controller, 'settings'):
            self._num_hats = int(system_controller.settings.get('num_hats', 1))
            self._master_relay = int(system_controller.settings.get('global_master_relay_id', 16))
        
        self._relay_widgets: Dict[int, RelayTerminalWidget] = {}
        self._init_ui()
        self._load_cage_data()
    
    def _init_ui(self) -> None:
        """
        Initialize the visualization layout.
        
        Layout hierarchy:
        - Main VBox: [Header] [Board Area] [Legend]
        - Board Area HBox: [Left Terminals] [Image] [Right Terminals]
        
        Reference: https://doc.qt.io/qt-5/layout.html
        "Qt's layout classes manage the positions and sizes of widgets"
        """
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(16)
        
        # ═══════════════════════════════════════════════════════════════
        # HEADER ROW (minimal - just title and refresh)
        # ═══════════════════════════════════════════════════════════════
        header_row = QHBoxLayout()
        header_row.setSpacing(12)
        
        title = QLabel("Relay Board Layout")
        title.setObjectName("Title")
        header_row.addWidget(title)
        
        header_row.addStretch()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._load_cage_data)
        header_row.addWidget(refresh_btn)
        
        main_layout.addLayout(header_row)
        
        # ═══════════════════════════════════════════════════════════════
        # BOARD VISUALIZATION (main content)
        # ═══════════════════════════════════════════════════════════════
        board_frame = QFrame()
        board_frame.setObjectName("Card")
        board_frame.setProperty("card", True)
        
        board_layout = QVBoxLayout(board_frame)
        board_layout.setContentsMargins(16, 16, 16, 16)
        board_layout.setSpacing(12)
        
        # Board model label
        board_title = QLabel("SM16relind 16-Relay HAT")
        board_title.setObjectName("BoardTitle")
        board_title.setAlignment(Qt.AlignCenter)
        board_layout.addWidget(board_title)
        
        # ─── Three-Column Layout ───
        # Reference: https://doc.qt.io/qt-5/qboxlayout.html#addLayout
        # "stretch factor determines how much of the remaining space is given to this layout"
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(16)
        
        # LEFT COLUMN: R1-R8
        left_column = QVBoxLayout()
        left_column.setSpacing(6)
        
        left_header = QLabel("LEFT TERMINALS")
        left_header.setObjectName("ColumnHeader")
        left_header.setAlignment(Qt.AlignCenter)
        left_column.addWidget(left_header)
        
        self._left_container = QVBoxLayout()
        self._left_container.setSpacing(4)
        left_column.addLayout(self._left_container)
        left_column.addStretch()
        
        # stretch=2 gives more space to terminal columns than image
        columns_layout.addLayout(left_column, 2)
        
        # CENTER: Board Image
        center_column = QVBoxLayout()
        center_column.setAlignment(Qt.AlignCenter)
        
        image_path = os.path.join(
            os.path.dirname(__file__), 
            'src', 
            'Relay architecture no labels.png'
        )
        
        if os.path.exists(image_path):
            board_image = QLabel()
            pixmap = QPixmap(image_path)
            
            # Scale image to fit layout while maintaining aspect ratio
            # Reference: https://doc.qt.io/qt-5/qpixmap.html#scaled
            # "Returns a copy scaled to a rectangle with width w and height h"
            # Using KeepAspectRatio to prevent distortion
            scaled = pixmap.scaled(
                280, 450,  # Max dimensions
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            board_image.setPixmap(scaled)
            board_image.setAlignment(Qt.AlignCenter)
            board_image.setToolTip("Physical relay HAT board - wire valves to matching terminals")
            center_column.addWidget(board_image)
        else:
            placeholder = QLabel("[Board Image]")
            placeholder.setObjectName("Caption")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setMinimumSize(200, 300)
            center_column.addWidget(placeholder)
        
        # stretch=1 for image (less than terminal columns)
        columns_layout.addLayout(center_column, 1)
        
        # RIGHT COLUMN: R16-R9
        right_column = QVBoxLayout()
        right_column.setSpacing(6)
        
        right_header = QLabel("RIGHT TERMINALS")
        right_header.setObjectName("ColumnHeader")
        right_header.setAlignment(Qt.AlignCenter)
        right_column.addWidget(right_header)
        
        self._right_container = QVBoxLayout()
        self._right_container.setSpacing(4)
        right_column.addLayout(self._right_container)
        right_column.addStretch()
        
        columns_layout.addLayout(right_column, 2)
        
        board_layout.addLayout(columns_layout)
        
        # Stretch factor 1 allows board area to expand
        main_layout.addWidget(board_frame, 1)
        
        # ═══════════════════════════════════════════════════════════════
        # LEGEND BAR (bottom)
        # ═══════════════════════════════════════════════════════════════
        legend_layout = QHBoxLayout()
        legend_layout.setSpacing(24)
        
        # Cage indicator
        cage_legend = QHBoxLayout()
        cage_legend.setSpacing(6)
        cage_dot = QLabel("●")
        cage_dot.setObjectName("StatusDot")
        cage_legend.addWidget(cage_dot)
        cage_legend.addWidget(QLabel("Cage valve"))
        legend_layout.addLayout(cage_legend)
        
        # Master indicator
        master_legend = QHBoxLayout()
        master_legend.setSpacing(6)
        master_dot = QLabel("●")
        master_dot.setObjectName("MasterStatusDot")
        master_legend.addWidget(master_dot)
        master_legend.addWidget(QLabel("Master solenoid"))
        legend_layout.addLayout(master_legend)
        
        legend_layout.addStretch()
        
        # Status count
        self._status_label = QLabel("")
        self._status_label.setObjectName("Caption")
        legend_layout.addWidget(self._status_label)
        
        main_layout.addLayout(legend_layout)
    
    def _load_cage_data(self) -> None:
        """
        Load cage assignments and populate relay terminals.
        
        Reference: https://doc.qt.io/qt-5/qlayout.html#takeAt
        "Removes the layout item at index from the layout, and returns the item"
        """
        # Clear existing widgets
        self._clear_layout(self._left_container)
        self._clear_layout(self._right_container)
        self._relay_widgets.clear()
        
        try:
            cages = self._database_handler.get_cages_for_dropdown(
                num_hats=self._num_hats,
                master_relay=self._master_relay
            )
            
            # Build lookup by relay_id
            cage_by_relay: Dict[int, Dict] = {}
            for cage in cages:
                relay_id = cage.get('relay_id', cage.get('cage_id'))
                cage_by_relay[relay_id] = cage
            
            # LEFT: Relays 1-8
            for relay_id in range(1, 9):
                widget = RelayTerminalWidget(
                    relay_id=relay_id,
                    cage_data=cage_by_relay.get(relay_id),
                    is_master=False
                )
                widget.clicked.connect(self._on_relay_clicked)
                self._left_container.addWidget(widget)
                self._relay_widgets[relay_id] = widget
            
            # RIGHT: Relays 16 down to 9 (matching physical layout)
            for relay_id in range(16, 8, -1):
                is_master = (relay_id == self._master_relay)
                widget = RelayTerminalWidget(
                    relay_id=relay_id,
                    cage_data=cage_by_relay.get(relay_id) if not is_master else None,
                    is_master=is_master
                )
                widget.clicked.connect(self._on_relay_clicked)
                self._right_container.addWidget(widget)
                self._relay_widgets[relay_id] = widget
            
            self._status_label.setText(f"{len(cages)} cages · {self._num_hats} HAT")
            self._print_to_terminal(f"[CagesTab] Loaded relay visualization")
            
        except Exception as e:
            self._status_label.setText(f"Error: {str(e)}")
            self._print_to_terminal(f"[CagesTab] Error: {e}")
    
    def _clear_layout(self, layout: QVBoxLayout) -> None:
        """
        Remove all widgets from a layout.
        
        Reference: https://doc.qt.io/qt-5/qobject.html#deleteLater
        "Schedules this object for deletion"
        """
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _on_relay_clicked(self, relay_id: int) -> None:
        """Handle relay terminal click."""
        self._print_to_terminal(f"[CagesTab] Selected relay {relay_id}")
        self.cage_selected.emit(relay_id)
    
    def refresh(self) -> None:
        """Public method to refresh the display."""
        self._load_cage_data()
