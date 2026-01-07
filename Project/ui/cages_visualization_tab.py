# ui/cages_visualization_tab.py
"""
Cages Visualization Tab - Visual representation of relay HAT cage layout.

Design Principles:
- Grid-based card layout matching physical relay HAT topology
- Material Design cards with status indicators
- Real-time cage name display from database
- Visual mapping of cage_id → relay_id
- Consistent with existing app QSS styling

Architecture:
- 16-relay HAT: R1-R15 for cages, R16 for master solenoid
- Card grid arranged to match physical board layout (4x4 or 3x5+master)
- Status badges showing calibration state, last use, etc.

Reference: Material Design Cards, existing ScheduleProgressTracker.MaterialCard
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QGridLayout, QFrame, QPushButton, QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt, pyqtSignal
from typing import Optional, Dict, Any, List


class CageCard(QFrame):
    """
    Individual cage visualization card.
    
    Features:
    - Cage ID and relay ID display
    - User-defined name display
    - Calibration status badge
    - Click to view details
    
    Styling: Uses QSS #MaterialCard for consistent appearance
    """
    
    clicked = pyqtSignal(int)  # Emits cage_id
    
    def __init__(self, cage_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self._cage_data = cage_data
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize card UI with cage information."""
        self.setObjectName("MaterialCard")
        self.setProperty("card", True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(140, 120)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        # Top row: Cage badge + Relay badge
        top_row = QHBoxLayout()
        top_row.setSpacing(6)
        
        # Cage ID badge (teal accent)
        cage_id = self._cage_data.get('cage_id', 0)
        cage_badge = QLabel(f"C{cage_id}")
        cage_badge.setObjectName("CageBadge")
        cage_badge.setAlignment(Qt.AlignCenter)
        cage_badge.setFixedSize(32, 24)
        top_row.addWidget(cage_badge)
        
        # Relay ID badge (subtle)
        relay_id = self._cage_data.get('relay_id', cage_id)
        relay_badge = QLabel(f"R{relay_id}")
        relay_badge.setObjectName("RelayBadge")
        relay_badge.setAlignment(Qt.AlignCenter)
        relay_badge.setFixedSize(32, 24)
        top_row.addWidget(relay_badge)
        
        top_row.addStretch()
        layout.addLayout(top_row)
        
        # Cage name (user-defined)
        name = self._cage_data.get('name', f"Cage {cage_id}")
        name_label = QLabel(name)
        name_label.setObjectName("CardTitle")
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        # Truncate if too long
        if len(name) > 18:
            name_label.setText(name[:15] + "...")
            name_label.setToolTip(name)
        layout.addWidget(name_label)
        
        # Status indicator (calibration status)
        status = self._get_calibration_status()
        status_label = QLabel(status)
        status_label.setObjectName("Caption")
        status_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(status_label)
        
        layout.addStretch()
    
    def _get_calibration_status(self) -> str:
        """Get calibration status text."""
        # Could be enhanced to show actual calibration data
        return "Ready"
    
    def mousePressEvent(self, event):
        """Handle click to emit cage_id."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._cage_data.get('cage_id', 0))
        super().mousePressEvent(event)
    
    @property
    def cage_id(self) -> int:
        return self._cage_data.get('cage_id', 0)
    
    def update_data(self, cage_data: Dict[str, Any]) -> None:
        """Update card with new cage data."""
        self._cage_data = cage_data
        # Could refresh UI here if needed


class MasterRelayCard(QFrame):
    """
    Special card for master solenoid relay (R16).
    
    Visual distinction from regular cage cards to indicate
    this relay controls the main water supply valve.
    """
    
    def __init__(self, relay_id: int = 16, parent=None):
        super().__init__(parent)
        self._relay_id = relay_id
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize master relay card with distinct styling."""
        self.setObjectName("MasterRelayCard")
        self.setProperty("card", True)
        self.setFixedSize(140, 120)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        # Top row: Relay badge
        top_row = QHBoxLayout()
        
        relay_badge = QLabel(f"R{self._relay_id}")
        relay_badge.setObjectName("MasterBadge")
        relay_badge.setAlignment(Qt.AlignCenter)
        relay_badge.setFixedSize(40, 24)
        top_row.addWidget(relay_badge)
        top_row.addStretch()
        
        layout.addLayout(top_row)
        
        # Master label
        title = QLabel("MASTER")
        title.setObjectName("CardTitle")
        title.setAlignment(Qt.AlignLeft)
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Main Valve")
        desc.setObjectName("Caption")
        layout.addWidget(desc)
        
        layout.addStretch()


class CagesVisualizationTab(QWidget):
    """
    Tab for visualizing cage/relay layout.
    
    Features:
    - Grid layout matching physical relay HAT board
    - Real-time cage name display
    - Calibration status indicators
    - Master relay highlighted
    - Refresh button for updates
    
    Args:
        database_handler: For cage name retrieval
        system_controller: For hardware configuration
    """
    
    cage_selected = pyqtSignal(int)  # Emits cage_id when card clicked
    
    def __init__(self, database_handler, system_controller=None, 
                 print_to_terminal=None, parent=None):
        super().__init__(parent)
        self._database_handler = database_handler
        self._system_controller = system_controller
        self._print_to_terminal = print_to_terminal or (lambda x: None)
        
        # Hardware config
        self._num_hats = 1
        self._master_relay = 16
        if system_controller and hasattr(system_controller, 'settings'):
            self._num_hats = int(system_controller.settings.get('num_hats', 1))
            self._master_relay = int(system_controller.settings.get('global_master_relay_id', 16))
        
        self._cage_cards: Dict[int, CageCard] = {}
        self._init_ui()
        self._load_cages()
    
    def _init_ui(self) -> None:
        """Initialize the visualization UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        
        # Header section
        header_container = QFrame()
        header_container.setObjectName("Card")
        header_container.setProperty("card", True)
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(8)
        
        # Title row
        title_row = QHBoxLayout()
        
        title = QLabel("Relay HAT Visualization")
        title.setObjectName("Title")
        title_row.addWidget(title)
        
        title_row.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("SecondaryButton")
        refresh_btn.clicked.connect(self._load_cages)
        refresh_btn.setFixedWidth(80)
        title_row.addWidget(refresh_btn)
        
        header_layout.addLayout(title_row)
        
        # Info text
        info_label = QLabel(
            f"Physical relay mapping for {self._num_hats} HAT(s). "
            f"Relay {self._master_relay} is the master solenoid."
        )
        info_label.setObjectName("Subtitle")
        info_label.setWordWrap(True)
        header_layout.addWidget(info_label)
        
        main_layout.addWidget(header_container)
        
        # Legend
        legend_container = QHBoxLayout()
        legend_container.setSpacing(24)
        
        # Cage legend
        cage_legend = QHBoxLayout()
        cage_sample = QLabel("C#")
        cage_sample.setObjectName("CageBadge")
        cage_sample.setFixedSize(28, 20)
        cage_sample.setAlignment(Qt.AlignCenter)
        cage_legend.addWidget(cage_sample)
        cage_legend.addWidget(QLabel("= Cage ID"))
        legend_container.addLayout(cage_legend)
        
        # Relay legend
        relay_legend = QHBoxLayout()
        relay_sample = QLabel("R#")
        relay_sample.setObjectName("RelayBadge")
        relay_sample.setFixedSize(28, 20)
        relay_sample.setAlignment(Qt.AlignCenter)
        relay_legend.addWidget(relay_sample)
        relay_legend.addWidget(QLabel("= Relay ID"))
        legend_container.addLayout(relay_legend)
        
        # Master legend
        master_legend = QHBoxLayout()
        master_sample = QLabel("M")
        master_sample.setObjectName("MasterBadge")
        master_sample.setFixedSize(28, 20)
        master_sample.setAlignment(Qt.AlignCenter)
        master_legend.addWidget(master_sample)
        master_legend.addWidget(QLabel("= Master Solenoid"))
        legend_container.addLayout(master_legend)
        
        legend_container.addStretch()
        main_layout.addLayout(legend_container)
        
        # Scroll area for cage grid
        scroll_area = QScrollArea()
        scroll_area.setObjectName("TrackerScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Grid container
        self._grid_container = QWidget()
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setSpacing(12)
        self._grid_layout.setContentsMargins(8, 8, 8, 8)
        
        scroll_area.setWidget(self._grid_container)
        main_layout.addWidget(scroll_area, 1)
        
        # Bottom info bar
        bottom_bar = QHBoxLayout()
        self._status_label = QLabel("")
        self._status_label.setObjectName("Caption")
        bottom_bar.addWidget(self._status_label)
        bottom_bar.addStretch()
        main_layout.addLayout(bottom_bar)
    
    def _load_cages(self) -> None:
        """Load cage data and populate grid."""
        # Clear existing cards
        for card in self._cage_cards.values():
            card.deleteLater()
        self._cage_cards.clear()
        
        # Clear grid layout
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        try:
            # Get cage data from database
            cages = self._database_handler.get_cages_for_dropdown(
                num_hats=self._num_hats,
                master_relay=self._master_relay
            )
            
            # Arrange in grid (4 columns to match HAT layout)
            num_columns = 4
            
            for idx, cage_data in enumerate(cages):
                row = idx // num_columns
                col = idx % num_columns
                
                card = CageCard(cage_data)
                card.clicked.connect(self._on_cage_clicked)
                
                self._grid_layout.addWidget(card, row, col)
                self._cage_cards[cage_data['cage_id']] = card
            
            # Add master relay card in the last position
            master_row = len(cages) // num_columns
            master_col = len(cages) % num_columns
            
            # If we're at the start of a new row, add master in previous row's last column
            # This gives a cleaner visual layout
            if master_col == 0 and master_row > 0:
                master_row -= 1
                master_col = num_columns
            
            master_card = MasterRelayCard(relay_id=self._master_relay)
            self._grid_layout.addWidget(master_card, master_row, master_col)
            
            self._status_label.setText(f"Loaded {len(cages)} cages + 1 master relay")
            self._print_to_terminal(f"[CagesTab] Loaded {len(cages)} cage visualizations")
            
        except Exception as e:
            self._status_label.setText(f"Error loading cages: {str(e)}")
            self._print_to_terminal(f"[CagesTab] Error: {e}")
    
    def _on_cage_clicked(self, cage_id: int) -> None:
        """Handle cage card click."""
        self._print_to_terminal(f"[CagesTab] Selected cage {cage_id}")
        self.cage_selected.emit(cage_id)
    
    def refresh(self) -> None:
        """Public method to refresh cage display."""
        self._load_cages()

