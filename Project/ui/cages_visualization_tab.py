# ui/cages_visualization_tab.py
"""
Cages Visualization Tab - Visual representation of the physical relay HAT board.

Shows the actual 16-relay HAT layout so users can understand which physical
relay terminal corresponds to which cage. Designed for non-expert users who
need to wire valves to the correct relay terminals.

Physical Layout (SM16relind HAT):
- Left side (top to bottom): R1, R2, R3, R4, R5, R6, R7, R8
- Right side (top to bottom): R16 (master), R15, R14, R13, R12, R11, R10, R9
- LEDs at bottom indicate relay state (on/off)
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QGridLayout, QFrame, QPushButton, QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont
from typing import Optional, Dict, Any
import os


class RelayTerminalWidget(QFrame):
    """
    Represents a single relay terminal on the physical board.
    
    Shows the relay number, assigned cage name, and connection status.
    Styled to look like a physical terminal block.
    """
    
    clicked = pyqtSignal(int)  # Emits relay_id
    
    def __init__(self, relay_id: int, cage_data: Optional[Dict[str, Any]] = None, 
                 is_master: bool = False, parent=None):
        super().__init__(parent)
        self._relay_id = relay_id
        self._cage_data = cage_data
        self._is_master = is_master
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Build the terminal widget UI."""
        if self._is_master:
            self.setObjectName("MasterTerminal")
        else:
            self.setObjectName("RelayTerminal")
        
        self.setProperty("card", True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(56)
        self.setMaximumHeight(64)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # Relay number indicator (styled as terminal number)
        relay_label = QLabel(f"R{self._relay_id}")
        relay_label.setObjectName("RelayNumber")
        relay_label.setAlignment(Qt.AlignCenter)
        relay_label.setFixedWidth(44)
        layout.addWidget(relay_label)
        
        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setObjectName("TerminalSeparator")
        layout.addWidget(separator)
        
        # Assignment info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        if self._is_master:
            # Master relay - special display
            name_label = QLabel("MASTER SOLENOID")
            name_label.setObjectName("MasterLabel")
            info_layout.addWidget(name_label)
            
            desc_label = QLabel("Main water supply valve")
            desc_label.setObjectName("TerminalDescription")
            info_layout.addWidget(desc_label)
        elif self._cage_data:
            # Regular cage assignment
            cage_id = self._cage_data.get('cage_id', 0)
            cage_name = self._cage_data.get('name', f'Cage {cage_id}')
            
            name_label = QLabel(cage_name)
            name_label.setObjectName("CageNameLabel")
            if len(cage_name) > 20:
                name_label.setText(cage_name[:18] + "...")
                name_label.setToolTip(cage_name)
            info_layout.addWidget(name_label)
            
            # Cage ID subtitle
            cage_label = QLabel(f"Cage {cage_id}")
            cage_label.setObjectName("TerminalDescription")
            info_layout.addWidget(cage_label)
        else:
            # Unassigned relay
            name_label = QLabel("Not assigned")
            name_label.setObjectName("UnassignedLabel")
            info_layout.addWidget(name_label)
        
        layout.addLayout(info_layout, 1)
        
        # Status indicator dot
        status_dot = QLabel("●")
        if self._is_master:
            status_dot.setObjectName("MasterStatusDot")
        else:
            status_dot.setObjectName("StatusDot")
        status_dot.setAlignment(Qt.AlignCenter)
        layout.addWidget(status_dot)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._relay_id)
        super().mousePressEvent(event)
    
    @property
    def relay_id(self) -> int:
        return self._relay_id


class CagesVisualizationTab(QWidget):
    """
    Tab displaying the physical relay HAT board layout.
    
    Mirrors the actual hardware layout so users can:
    - See which relay terminal to wire each cage valve to
    - Understand the relationship between cage IDs and relay numbers
    - Identify the master solenoid location
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
        """Initialize the visualization layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)
        
        # ─────────────────────────────────────────────────────────────
        # Header Card
        # ─────────────────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("Card")
        header.setProperty("card", True)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)
        header_layout.setSpacing(12)
        
        # Title row
        title_row = QHBoxLayout()
        title_row.setSpacing(16)
        
        title = QLabel("Relay Board Layout")
        title.setObjectName("Title")
        title_row.addWidget(title)
        
        title_row.addStretch()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._load_cage_data)
        refresh_btn.setMinimumWidth(100)
        title_row.addWidget(refresh_btn)
        
        header_layout.addLayout(title_row)
        
        # Description
        desc = QLabel(
            "This diagram shows the physical layout of the 16-relay HAT board. "
            "Each terminal corresponds to a valve connection. Wire your cage valves "
            "to the relay terminals as shown below."
        )
        desc.setObjectName("Subtitle")
        desc.setWordWrap(True)
        header_layout.addWidget(desc)
        
        main_layout.addWidget(header)
        
        # ─────────────────────────────────────────────────────────────
        # Board Visualization
        # ─────────────────────────────────────────────────────────────
        board_frame = QFrame()
        board_frame.setObjectName("BoardFrame")
        board_frame.setProperty("card", True)
        board_layout = QVBoxLayout(board_frame)
        board_layout.setContentsMargins(20, 20, 20, 20)
        board_layout.setSpacing(16)
        
        # Board title
        board_title = QLabel("SM16relind 16-Relay HAT")
        board_title.setObjectName("BoardTitle")
        board_title.setAlignment(Qt.AlignCenter)
        board_layout.addWidget(board_title)
        
        # Two-column layout matching physical board
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(40)
        
        # ─── LEFT COLUMN: Relays 1-8 ───
        left_column = QVBoxLayout()
        left_column.setSpacing(8)
        
        left_header = QLabel("LEFT TERMINALS (R1-R8)")
        left_header.setObjectName("ColumnHeader")
        left_header.setAlignment(Qt.AlignCenter)
        left_column.addWidget(left_header)
        
        self._left_container = QVBoxLayout()
        self._left_container.setSpacing(4)
        left_column.addLayout(self._left_container)
        left_column.addStretch()
        
        columns_layout.addLayout(left_column, 1)
        
        # ─── CENTER: Board illustration ───
        center_column = QVBoxLayout()
        center_column.setSpacing(8)
        
        # Load board image if available
        image_path = os.path.join(
            os.path.dirname(__file__), 
            'src', 
            'Relay architecture no labels.png'
        )
        
        if os.path.exists(image_path):
            board_image = QLabel()
            pixmap = QPixmap(image_path)
            # Scale to reasonable size
            scaled = pixmap.scaledToHeight(380, Qt.SmoothTransformation)
            board_image.setPixmap(scaled)
            board_image.setAlignment(Qt.AlignCenter)
            board_image.setToolTip("Physical relay HAT board layout")
            center_column.addWidget(board_image)
        else:
            # Fallback placeholder
            placeholder = QLabel("[ Board Diagram ]")
            placeholder.setObjectName("Subtitle")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setMinimumSize(200, 300)
            center_column.addWidget(placeholder)
        
        center_column.addStretch()
        columns_layout.addLayout(center_column, 0)
        
        # ─── RIGHT COLUMN: Relays 9-16 ───
        right_column = QVBoxLayout()
        right_column.setSpacing(8)
        
        right_header = QLabel("RIGHT TERMINALS (R9-R16)")
        right_header.setObjectName("ColumnHeader")
        right_header.setAlignment(Qt.AlignCenter)
        right_column.addWidget(right_header)
        
        self._right_container = QVBoxLayout()
        self._right_container.setSpacing(4)
        right_column.addLayout(self._right_container)
        right_column.addStretch()
        
        columns_layout.addLayout(right_column, 1)
        
        board_layout.addLayout(columns_layout)
        
        # LED indicator row
        led_row = QHBoxLayout()
        led_row.setSpacing(4)
        led_row.addStretch()
        
        led_label = QLabel("Status LEDs:")
        led_label.setObjectName("Caption")
        led_row.addWidget(led_label)
        
        for i in range(1, 9):
            led = QLabel(f" {i} ")
            led.setObjectName("LEDIndicator")
            led.setAlignment(Qt.AlignCenter)
            led_row.addWidget(led)
        
        led_row.addStretch()
        board_layout.addLayout(led_row)
        
        main_layout.addWidget(board_frame, 1)
        
        # ─────────────────────────────────────────────────────────────
        # Legend / Help
        # ─────────────────────────────────────────────────────────────
        legend_frame = QFrame()
        legend_frame.setObjectName("Card")
        legend_frame.setProperty("card", True)
        legend_layout = QHBoxLayout(legend_frame)
        legend_layout.setContentsMargins(16, 12, 16, 12)
        legend_layout.setSpacing(32)
        
        # Status indicators legend
        legend_items = [
            ("●", "StatusDot", "Cage relay - connected to valve"),
            ("●", "MasterStatusDot", "Master solenoid - main water supply"),
        ]
        
        for symbol, obj_name, description in legend_items:
            item_layout = QHBoxLayout()
            item_layout.setSpacing(8)
            
            dot = QLabel(symbol)
            dot.setObjectName(obj_name)
            item_layout.addWidget(dot)
            
            text = QLabel(description)
            text.setObjectName("Caption")
            item_layout.addWidget(text)
            
            legend_layout.addLayout(item_layout)
        
        legend_layout.addStretch()
        
        # Status
        self._status_label = QLabel("")
        self._status_label.setObjectName("Caption")
        legend_layout.addWidget(self._status_label)
        
        main_layout.addWidget(legend_frame)
    
    def _load_cage_data(self) -> None:
        """Load cage assignments and populate the relay terminals."""
        # Clear existing widgets
        self._clear_layout(self._left_container)
        self._clear_layout(self._right_container)
        self._relay_widgets.clear()
        
        try:
            # Get cage data from database
            cages = self._database_handler.get_cages_for_dropdown(
                num_hats=self._num_hats,
                master_relay=self._master_relay
            )
            
            # Build lookup by relay_id
            cage_by_relay: Dict[int, Dict] = {}
            for cage in cages:
                relay_id = cage.get('relay_id', cage.get('cage_id'))
                cage_by_relay[relay_id] = cage
            
            # LEFT SIDE: Relays 1-8 (top to bottom on physical board)
            for relay_id in range(1, 9):
                cage_data = cage_by_relay.get(relay_id)
                widget = RelayTerminalWidget(
                    relay_id=relay_id,
                    cage_data=cage_data,
                    is_master=False
                )
                widget.clicked.connect(self._on_relay_clicked)
                self._left_container.addWidget(widget)
                self._relay_widgets[relay_id] = widget
            
            # RIGHT SIDE: Relays 16 down to 9 (matching physical layout)
            # R16 (master) at top, then R15, R14, ... R9
            for relay_id in range(16, 8, -1):
                is_master = (relay_id == self._master_relay)
                cage_data = cage_by_relay.get(relay_id) if not is_master else None
                
                widget = RelayTerminalWidget(
                    relay_id=relay_id,
                    cage_data=cage_data,
                    is_master=is_master
                )
                widget.clicked.connect(self._on_relay_clicked)
                self._right_container.addWidget(widget)
                self._relay_widgets[relay_id] = widget
            
            self._status_label.setText(f"Showing {len(cages)} cages across {self._num_hats} HAT(s)")
            self._print_to_terminal(f"[CagesTab] Loaded relay board visualization")
            
        except Exception as e:
            self._status_label.setText(f"Error: {str(e)}")
            self._print_to_terminal(f"[CagesTab] Error loading data: {e}")
    
    def _clear_layout(self, layout: QVBoxLayout) -> None:
        """Remove all widgets from a layout."""
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
