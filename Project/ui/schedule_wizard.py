"""
Schedule Creation Wizard - RSO-Inspired Step-by-Step Schedule Configuration

Design Principles:
- 4-step guided flow: Type → Animals → Parameters → Review
- Visual feedback and validation at each step
- Reuses existing Schedule model and database_handler
- Signal-based completion for loose coupling

Architecture:
- Step 1: Select Schedule Type (Staggered vs Instant)
- Step 2: Select Animals/Cages (multi-select from available)
- Step 3: Configure Parameters (times, volumes, windows)
- Step 4: Review & Save

Reference: RSO NewSessionWizard pattern
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QGridLayout, QGroupBox, QFormLayout, QLineEdit, QSpinBox,
    QDoubleSpinBox, QTimeEdit, QDateTimeEdit, QListWidget,
    QListWidgetItem, QCheckBox, QFrame, QSizePolicy, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTime, QDateTime

from .components.wizard import WizardContainer, WizardStep
from .components.interactive_card import InteractiveCard, SelectableCardGroup


# ============================================================================
# SCHEDULE TYPE DEFINITIONS
# ============================================================================

SCHEDULE_TYPES = {
    "staggered": {
        "title": "Staggered Delivery",
        "description": "Distribute water evenly across a time window. "
                      "The system automatically spaces out deliveries.",
        "icon": "⏱",
        "badge": "Recommended",
    },
    "instant": {
        "title": "Instant Delivery",
        "description": "Deliver water at specific times you define. "
                      "Full control over exact delivery moments.",
        "icon": "⚡",
        "badge": "",
    },
}


# ============================================================================
# STEP 1: SELECT SCHEDULE TYPE
# ============================================================================

class Step1SelectType(QWidget):
    """Step 1: Select delivery mode (Staggered vs Instant)."""
    
    selection_changed = pyqtSignal(str)  # Emits selected type key
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._selected_type: Optional[str] = None
        self._init_ui()
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)
        
        # Step header
        header = self._create_header(
            icon="⏱",
            title="Select Schedule Type",
            description="Choose how you want to deliver water to your animals"
        )
        layout.addWidget(header)
        
        # Schedule type cards
        self._card_group = SelectableCardGroup()
        
        cards_layout = QGridLayout()
        cards_layout.setSpacing(16)
        
        for i, (key, type_info) in enumerate(SCHEDULE_TYPES.items()):
            card = InteractiveCard(
                title=type_info["title"],
                description=type_info["description"],
                icon=type_info["icon"],
                badge=type_info["badge"],
            )
            self._card_group.add_card(key, card)
            cards_layout.addWidget(card, i // 2, i % 2)
        
        self._card_group.on_selection_changed(self._on_type_selected)
        
        layout.addLayout(cards_layout)
        layout.addStretch()
    
    def _create_header(self, icon: str, title: str, description: str) -> QWidget:
        """Create step header with icon, title, and description."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(16)
        
        # Icon
        icon_label = QLabel(icon)
        icon_label.setObjectName("StepIcon")
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        title_label = QLabel(title)
        title_label.setObjectName("StepTitle")
        text_layout.addWidget(title_label)
        
        desc_label = QLabel(description)
        desc_label.setObjectName("StepDescription")
        desc_label.setWordWrap(True)
        text_layout.addWidget(desc_label)
        
        layout.addLayout(text_layout, 1)
        
        return container
    
    def _on_type_selected(self, type_key: str) -> None:
        """Handle schedule type selection."""
        self._selected_type = type_key
        self.selection_changed.emit(type_key)
    
    def get_selected_type(self) -> Optional[str]:
        """Get the currently selected schedule type."""
        return self._selected_type
    
    def is_valid(self) -> bool:
        """Check if step has valid selection."""
        return self._selected_type is not None


# ============================================================================
# STEP 2: SELECT ANIMALS
# ============================================================================

class Step2SelectAnimals(QWidget):
    """Step 2: Select animals/cages for the schedule."""
    
    selection_changed = pyqtSignal(list)  # Emits list of selected animal IDs
    
    def __init__(self, database_handler, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._database_handler = database_handler
        self._selected_animals: List[int] = []
        self._animal_data: Dict[int, Dict[str, Any]] = {}  # Full animal data by ID
        self._init_ui()
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)
        
        # Step header
        header = self._create_header(
            icon="🐭",
            title="Select Animals",
            description="Choose which animals will receive water from this schedule"
        )
        layout.addWidget(header)
        
        # Animals list with checkboxes
        list_container = QGroupBox("Available Animals")
        list_layout = QVBoxLayout(list_container)
        
        self._animals_list = QListWidget()
        self._animals_list.setSelectionMode(QListWidget.MultiSelection)
        self._animals_list.itemSelectionChanged.connect(self._on_selection_changed)
        list_layout.addWidget(self._animals_list)
        
        # Select all / deselect all buttons
        btn_layout = QHBoxLayout()
        from PyQt5.QtWidgets import QPushButton
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all)
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self._deselect_all)
        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(deselect_all_btn)
        btn_layout.addStretch()
        list_layout.addLayout(btn_layout)
        
        layout.addWidget(list_container, 1)
    
    def _create_header(self, icon: str, title: str, description: str) -> QWidget:
        """Create step header with icon, title, and description."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(16)
        
        icon_label = QLabel(icon)
        icon_label.setObjectName("StepIcon")
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        title_label = QLabel(title)
        title_label.setObjectName("StepTitle")
        text_layout.addWidget(title_label)
        
        desc_label = QLabel(description)
        desc_label.setObjectName("StepDescription")
        desc_label.setWordWrap(True)
        text_layout.addWidget(desc_label)
        
        layout.addLayout(text_layout, 1)
        
        return container
    
    def load_animals(self, trainer_id: Optional[int] = None) -> None:
        """Load available animals from database."""
        self._animals_list.clear()
        self._animal_data = {}
        
        try:
            if trainer_id:
                animals = self._database_handler.get_animals_by_trainer(trainer_id)
            else:
                animals = self._database_handler.get_all_animals()
            
            for animal in animals:
                # animal is an Animal object with properties
                animal_id = animal.animal_id
                lab_id = animal.lab_animal_id or str(animal_id)
                name = animal.name or f"Animal {animal_id}"
                
                # Store full data for later retrieval
                self._animal_data[animal_id] = {
                    "id": animal_id,
                    "lab_id": lab_id,
                    "name": name,
                }
                
                item = QListWidgetItem(f"{lab_id} - {name}")
                item.setData(Qt.UserRole, animal_id)
                self._animals_list.addItem(item)
                
            print(f"[Step2] Loaded {len(animals)} animals for wizard")
        except Exception as e:
            print(f"[Step2] Error loading animals: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_selection_changed(self) -> None:
        """Handle animal selection change."""
        self._selected_animals = [
            item.data(Qt.UserRole) 
            for item in self._animals_list.selectedItems()
        ]
        self.selection_changed.emit(self._selected_animals)
    
    def _select_all(self) -> None:
        """Select all animals."""
        self._animals_list.selectAll()
    
    def _deselect_all(self) -> None:
        """Deselect all animals."""
        self._animals_list.clearSelection()
    
    def get_selected_animals(self) -> List[int]:
        """Get list of selected animal IDs."""
        return self._selected_animals
    
    def get_selected_animals_data(self) -> List[Dict[str, Any]]:
        """Get full data for selected animals (id, lab_id, name)."""
        return [
            self._animal_data[animal_id]
            for animal_id in self._selected_animals
            if animal_id in self._animal_data
        ]
    
    def is_valid(self) -> bool:
        """Check if at least one animal is selected."""
        return len(self._selected_animals) > 0


# ============================================================================
# STEP 3: CONFIGURE PARAMETERS
# ============================================================================

class Step3ConfigureParameters(QWidget):
    """Step 3: Configure schedule parameters with per-animal settings."""
    
    parameters_changed = pyqtSignal(dict)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._schedule_type: str = "staggered"
        self._parameters: Dict[str, Any] = {}
        self._selected_animals: List[Dict[str, Any]] = []  # [{id, lab_id, name}]
        self._animal_configs: Dict[int, Dict[str, Any]] = {}  # Per-animal settings
        self._animal_widgets: Dict[int, Dict[str, Any]] = {}  # Widget references
        self._init_ui()
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)
        
        # Step header
        header = self._create_header(
            icon="⚙",
            title="Configure Parameters",
            description="Set timing and volume for each animal"
        )
        layout.addWidget(header)
        
        # Scroll area for parameters
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        self._params_widget = QWidget()
        self._params_layout = QVBoxLayout(self._params_widget)
        self._params_layout.setSpacing(16)
        
        scroll.setWidget(self._params_widget)
        layout.addWidget(scroll, 1)
        
        # Will be populated when animals are set
        self._build_empty_state()
    
    def _create_header(self, icon: str, title: str, description: str) -> QWidget:
        """Create step header."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(16)
        
        icon_label = QLabel(icon)
        icon_label.setObjectName("StepIcon")
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        title_label = QLabel(title)
        title_label.setObjectName("StepTitle")
        text_layout.addWidget(title_label)
        
        desc_label = QLabel(description)
        desc_label.setObjectName("StepDescription")
        desc_label.setWordWrap(True)
        text_layout.addWidget(desc_label)
        
        layout.addLayout(text_layout, 1)
        
        return container
    
    def set_animals(self, animals: List[Dict[str, Any]]) -> None:
        """Set selected animals for per-animal configuration."""
        self._selected_animals = animals
        self._animal_configs = {}
        self._animal_widgets = {}
        
        # Initialize default config for each animal
        for animal in animals:
            animal_id = animal["id"]
            self._animal_configs[animal_id] = {
                "start_time": datetime.now(),
                "end_time": datetime.now() + timedelta(hours=12),
                "delivery_time": datetime.now() + timedelta(minutes=5),
                "volume": 1.0,
            }
    
    def set_schedule_type(self, schedule_type: str) -> None:
        """Set the schedule type and rebuild parameters."""
        self._schedule_type = schedule_type
        self._clear_params()
        
        if not self._selected_animals:
            self._build_empty_state()
        elif schedule_type == "staggered":
            self._build_staggered_params()
        else:
            self._build_instant_params()
    
    def _build_empty_state(self) -> None:
        """Show empty state when no animals selected."""
        label = QLabel("No animals selected. Please go back and select animals.")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #9CA3AF; font-size: 14px;")
        self._params_layout.addWidget(label)
        self._params_layout.addStretch()
    
    def _clear_params(self) -> None:
        """Clear existing parameter widgets."""
        while self._params_layout.count():
            item = self._params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._parameters = {}
        self._animal_widgets = {}
    
    def _build_staggered_params(self) -> None:
        """Build parameter form for staggered delivery with per-animal settings."""
        # Schedule Name
        name_group = QGroupBox("Schedule Name")
        name_layout = QFormLayout(name_group)
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Enter a name for this schedule")
        self._name_input.textChanged.connect(lambda v: self._update_param("name", v))
        name_layout.addRow("Name:", self._name_input)
        self._params_layout.addWidget(name_group)
        
        # Global Apply Section
        global_group = QGroupBox("Quick Apply to All Animals")
        global_layout = QHBoxLayout(global_group)
        
        from PyQt5.QtWidgets import QPushButton
        
        self._global_start = QDateTimeEdit()
        self._global_start.setDateTime(QDateTime.currentDateTime())
        self._global_start.setCalendarPopup(True)
        global_layout.addWidget(QLabel("Start:"))
        global_layout.addWidget(self._global_start)
        
        self._global_end = QDateTimeEdit()
        self._global_end.setDateTime(QDateTime.currentDateTime().addSecs(3600 * 12))
        self._global_end.setCalendarPopup(True)
        global_layout.addWidget(QLabel("End:"))
        global_layout.addWidget(self._global_end)
        
        self._global_volume = QDoubleSpinBox()
        self._global_volume.setRange(0.1, 50.0)
        self._global_volume.setValue(1.0)
        self._global_volume.setSuffix(" mL")
        global_layout.addWidget(QLabel("Volume:"))
        global_layout.addWidget(self._global_volume)
        
        apply_all_btn = QPushButton("Apply to All")
        apply_all_btn.clicked.connect(self._apply_to_all_staggered)
        global_layout.addWidget(apply_all_btn)
        
        self._params_layout.addWidget(global_group)
        
        # Per-Animal Settings
        animals_group = QGroupBox(f"Animal Settings ({len(self._selected_animals)} selected)")
        animals_layout = QVBoxLayout(animals_group)
        
        for animal in self._selected_animals:
            animal_id = animal["id"]
            animal_widget = self._create_staggered_animal_row(animal)
            animals_layout.addWidget(animal_widget)
        
        self._params_layout.addWidget(animals_group)
        
        # Initialize default values
        self._parameters = {
            "name": "",
        }
        
        self._params_layout.addStretch()
    
    def _create_staggered_animal_row(self, animal: Dict[str, Any]) -> QWidget:
        """Create a config row for one animal in staggered mode."""
        animal_id = animal["id"]
        config = self._animal_configs.get(animal_id, {})
        
        container = QFrame()
        container.setObjectName("AnimalConfigRow")
        container.setStyleSheet("""
            QFrame#AnimalConfigRow {
                background: #F8FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                padding: 8px;
                margin: 4px 0;
            }
        """)
        
        layout = QHBoxLayout(container)
        layout.setSpacing(12)
        
        # Animal label
        label = QLabel(f"<b>{animal.get('lab_id', animal_id)}</b> - {animal.get('name', 'Unknown')}")
        label.setMinimumWidth(150)
        layout.addWidget(label)
        
        # Start time
        start_dt = QDateTimeEdit()
        start_dt.setDateTime(QDateTime.currentDateTime())
        start_dt.setCalendarPopup(True)
        start_dt.setMinimumWidth(160)
        start_dt.dateTimeChanged.connect(
            lambda dt, aid=animal_id: self._update_animal_config(aid, "start_time", dt.toPyDateTime())
        )
        layout.addWidget(QLabel("Start:"))
        layout.addWidget(start_dt)
        
        # End time
        end_dt = QDateTimeEdit()
        end_dt.setDateTime(QDateTime.currentDateTime().addSecs(3600 * 12))
        end_dt.setCalendarPopup(True)
        end_dt.setMinimumWidth(160)
        end_dt.dateTimeChanged.connect(
            lambda dt, aid=animal_id: self._update_animal_config(aid, "end_time", dt.toPyDateTime())
        )
        layout.addWidget(QLabel("End:"))
        layout.addWidget(end_dt)
        
        # Volume
        volume_spin = QDoubleSpinBox()
        volume_spin.setRange(0.1, 50.0)
        volume_spin.setValue(config.get("volume", 1.0))
        volume_spin.setSuffix(" mL")
        volume_spin.setDecimals(2)
        volume_spin.valueChanged.connect(
            lambda v, aid=animal_id: self._update_animal_config(aid, "volume", v)
        )
        layout.addWidget(QLabel("Volume:"))
        layout.addWidget(volume_spin)
        
        layout.addStretch()
        
        # Store widget references for apply-all
        self._animal_widgets[animal_id] = {
            "start": start_dt,
            "end": end_dt,
            "volume": volume_spin,
        }
        
        return container
    
    def _apply_to_all_staggered(self) -> None:
        """Apply global settings to all animals."""
        start = self._global_start.dateTime().toPyDateTime()
        end = self._global_end.dateTime().toPyDateTime()
        volume = self._global_volume.value()
        
        for animal_id, widgets in self._animal_widgets.items():
            widgets["start"].setDateTime(QDateTime(start))
            widgets["end"].setDateTime(QDateTime(end))
            widgets["volume"].setValue(volume)
            
            self._animal_configs[animal_id] = {
                "start_time": start,
                "end_time": end,
                "volume": volume,
            }
    
    def _build_instant_params(self) -> None:
        """Build parameter form for instant delivery with per-animal settings."""
        # Schedule Name
        name_group = QGroupBox("Schedule Name")
        name_layout = QFormLayout(name_group)
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Enter a name for this schedule")
        self._name_input.textChanged.connect(lambda v: self._update_param("name", v))
        name_layout.addRow("Name:", self._name_input)
        self._params_layout.addWidget(name_group)
        
        # Global Apply Section
        from PyQt5.QtWidgets import QPushButton
        
        global_group = QGroupBox("Quick Apply to All Animals")
        global_layout = QHBoxLayout(global_group)
        
        self._global_delivery_time = QDateTimeEdit()
        self._global_delivery_time.setDateTime(QDateTime.currentDateTime().addSecs(300))
        self._global_delivery_time.setCalendarPopup(True)
        global_layout.addWidget(QLabel("Delivery Time:"))
        global_layout.addWidget(self._global_delivery_time)
        
        self._global_volume = QDoubleSpinBox()
        self._global_volume.setRange(0.1, 50.0)
        self._global_volume.setValue(1.0)
        self._global_volume.setSuffix(" mL")
        global_layout.addWidget(QLabel("Volume:"))
        global_layout.addWidget(self._global_volume)
        
        apply_all_btn = QPushButton("Apply to All")
        apply_all_btn.clicked.connect(self._apply_to_all_instant)
        global_layout.addWidget(apply_all_btn)
        
        self._params_layout.addWidget(global_group)
        
        # Per-Animal Settings
        animals_group = QGroupBox(f"Animal Settings ({len(self._selected_animals)} selected)")
        animals_layout = QVBoxLayout(animals_group)
        
        for animal in self._selected_animals:
            animal_widget = self._create_instant_animal_row(animal)
            animals_layout.addWidget(animal_widget)
        
        self._params_layout.addWidget(animals_group)
        
        # Initialize default values
        self._parameters = {
            "name": "",
        }
        
        self._params_layout.addStretch()
    
    def _create_instant_animal_row(self, animal: Dict[str, Any]) -> QWidget:
        """Create a config row for one animal in instant mode."""
        animal_id = animal["id"]
        config = self._animal_configs.get(animal_id, {})
        
        container = QFrame()
        container.setObjectName("AnimalConfigRow")
        container.setStyleSheet("""
            QFrame#AnimalConfigRow {
                background: #F8FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                padding: 8px;
                margin: 4px 0;
            }
        """)
        
        layout = QHBoxLayout(container)
        layout.setSpacing(12)
        
        # Animal label
        label = QLabel(f"<b>{animal.get('lab_id', animal_id)}</b> - {animal.get('name', 'Unknown')}")
        label.setMinimumWidth(150)
        layout.addWidget(label)
        
        # Delivery time
        delivery_dt = QDateTimeEdit()
        delivery_dt.setDateTime(QDateTime.currentDateTime().addSecs(300))
        delivery_dt.setCalendarPopup(True)
        delivery_dt.setMinimumWidth(160)
        delivery_dt.dateTimeChanged.connect(
            lambda dt, aid=animal_id: self._update_animal_config(aid, "delivery_time", dt.toPyDateTime())
        )
        layout.addWidget(QLabel("Delivery Time:"))
        layout.addWidget(delivery_dt)
        
        # Volume
        volume_spin = QDoubleSpinBox()
        volume_spin.setRange(0.1, 50.0)
        volume_spin.setValue(config.get("volume", 1.0))
        volume_spin.setSuffix(" mL")
        volume_spin.setDecimals(2)
        volume_spin.valueChanged.connect(
            lambda v, aid=animal_id: self._update_animal_config(aid, "volume", v)
        )
        layout.addWidget(QLabel("Volume:"))
        layout.addWidget(volume_spin)
        
        layout.addStretch()
        
        # Store widget references
        self._animal_widgets[animal_id] = {
            "delivery_time": delivery_dt,
            "volume": volume_spin,
        }
        
        return container
    
    def _apply_to_all_instant(self) -> None:
        """Apply global settings to all animals for instant mode."""
        delivery_time = self._global_delivery_time.dateTime().toPyDateTime()
        volume = self._global_volume.value()
        
        for animal_id, widgets in self._animal_widgets.items():
            widgets["delivery_time"].setDateTime(QDateTime(delivery_time))
            widgets["volume"].setValue(volume)
            
            self._animal_configs[animal_id] = {
                "delivery_time": delivery_time,
                "volume": volume,
            }
    
    def _update_animal_config(self, animal_id: int, key: str, value: Any) -> None:
        """Update a specific animal's configuration."""
        if animal_id not in self._animal_configs:
            self._animal_configs[animal_id] = {}
        self._animal_configs[animal_id][key] = value
        self.parameters_changed.emit(self.get_parameters())
    
    def _update_param(self, key: str, value: Any) -> None:
        """Update a parameter value."""
        self._parameters[key] = value
        self.parameters_changed.emit(self.get_parameters())
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get all configured parameters including per-animal configs."""
        return {
            **self._parameters,
            "animal_configs": self._animal_configs.copy(),
        }
    
    def get_animal_configs(self) -> Dict[int, Dict[str, Any]]:
        """Get per-animal configurations."""
        return self._animal_configs.copy()
    
    def is_valid(self) -> bool:
        """Validate parameters."""
        name = self._parameters.get("name", "").strip()
        if not name:
            return False
        
        # Validate we have animal configs
        if not self._animal_configs:
            return False
        
        # Validate each animal's config
        for animal_id, config in self._animal_configs.items():
            if self._schedule_type == "staggered":
                start = config.get("start_time")
                end = config.get("end_time")
                if start and end and start >= end:
                    return False
                volume = config.get("volume", 0)
                if volume <= 0:
                    return False
            else:  # instant
                delivery = config.get("delivery_time")
                if not delivery:
                    return False
                volume = config.get("volume", 0)
                if volume <= 0:
                    return False
        
        return True


# ============================================================================
# STEP 4: REVIEW & SAVE
# ============================================================================

class Step4Review(QWidget):
    """Step 4: Review configuration and save schedule."""
    
    save_without_running = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._config: Dict[str, Any] = {}
        self._init_ui()
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)
        
        # Step header
        header = self._create_header(
            icon="▶",
            title="Review & Save",
            description="Confirm your schedule settings before saving"
        )
        layout.addWidget(header)
        
        # Scrollable summary area for dynamic number of animals
        from PyQt5.QtWidgets import QScrollArea
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Summary card inside scroll area
        summary_group = QGroupBox()
        self._summary_layout = QFormLayout(summary_group)
        self._summary_layout.setSpacing(12)
        self._summary_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self._summary_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        scroll_area.setWidget(summary_group)
        layout.addWidget(scroll_area, 1)
        
        # Save without running option
        from PyQt5.QtWidgets import QPushButton
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch()
        
        save_only_btn = QPushButton("Save Without Running")
        save_only_btn.clicked.connect(self.save_without_running.emit)
        btn_layout.addWidget(save_only_btn)
        
        layout.addWidget(btn_container)
    
    def _create_header(self, icon: str, title: str, description: str) -> QWidget:
        """Create step header."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(16)
        
        icon_label = QLabel(icon)
        icon_label.setObjectName("StepIcon")
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        title_label = QLabel(title)
        title_label.setObjectName("StepTitle")
        text_layout.addWidget(title_label)
        
        desc_label = QLabel(description)
        desc_label.setObjectName("StepDescription")
        desc_label.setWordWrap(True)
        text_layout.addWidget(desc_label)
        
        layout.addLayout(text_layout, 1)
        
        return container
    
    def set_config(self, config: Dict[str, Any]) -> None:
        """Set the configuration to display."""
        self._config = config
        self._update_summary()
    
    def _update_summary(self) -> None:
        """Update the summary display with per-animal configurations."""
        # Clear existing
        while self._summary_layout.count():
            item = self._summary_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Schedule Type
        schedule_type = self._config.get("schedule_type", "staggered")
        type_info = SCHEDULE_TYPES.get(schedule_type, {})
        self._add_summary_row("Schedule Type:", type_info.get("title", schedule_type))
        
        # Parameters (name)
        params = self._config.get("parameters", {})
        
        if params.get("name"):
            self._add_summary_row("Name:", params["name"])
        
        # Per-Animal Configuration Table
        animal_configs = params.get("animal_configs", {})
        animals = self._config.get("animals", [])
        
        if animal_configs:
            self._add_summary_section("Animal Configurations")
            
            for animal_id, config in animal_configs.items():
                # Format animal row
                if schedule_type == "staggered":
                    start = config.get("start_time")
                    end = config.get("end_time")
                    volume = config.get("volume", 0)
                    
                    start_str = start.strftime("%m/%d %H:%M") if isinstance(start, datetime) else str(start)
                    end_str = end.strftime("%m/%d %H:%M") if isinstance(end, datetime) else str(end)
                    
                    value = f"{start_str} → {end_str}, {volume:.2f} mL"
                else:  # instant
                    delivery = config.get("delivery_time")
                    volume = config.get("volume", 0)
                    
                    delivery_str = delivery.strftime("%m/%d %H:%M") if isinstance(delivery, datetime) else str(delivery)
                    value = f"{delivery_str}, {volume:.2f} mL"
                
                self._add_summary_row(f"  Animal {animal_id}:", value)
        
        self._add_summary_row("Total Animals:", f"{len(animals)} selected")
    
    def _add_summary_section(self, title: str) -> None:
        """Add a section header to the summary with proper spacing."""
        # Add spacer for visual separation
        spacer = QLabel("")
        spacer.setFixedHeight(8)
        self._summary_layout.addRow(spacer)
        
        # Section header label - spans both columns via addRow with single widget
        section = QLabel(title)
        section.setStyleSheet("""
            font-size: 13px; 
            font-weight: 600;
            color: #0D9488; 
            padding-top: 4px;
            padding-bottom: 4px;
            border-bottom: 1px solid #E5E7EB;
        """)
        section.setWordWrap(False)
        self._summary_layout.addRow(section)
    
    def _add_summary_row(self, label: str, value: str) -> None:
        """Add a row to the summary."""
        label_widget = QLabel(label)
        label_widget.setStyleSheet("font-weight: 500; color: #4E5D6C; font-size: 13px;")
        
        value_widget = QLabel(value)
        value_widget.setStyleSheet("font-weight: 600; color: #1A1D1F; font-size: 13px;")
        value_widget.setAlignment(Qt.AlignRight)
        value_widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        self._summary_layout.addRow(label_widget, value_widget)
    
    def get_config(self) -> Dict[str, Any]:
        """Get the full configuration."""
        return self._config


# ============================================================================
# MAIN WIZARD
# ============================================================================

class ScheduleCreationWizard(QWidget):
    """
    Main schedule creation wizard using RSO-style 4-step pattern.
    
    Signals:
        schedule_created(dict): Emitted when schedule is successfully created
        cancelled(): Emitted when wizard is cancelled
    """
    
    schedule_created = pyqtSignal(dict)
    cancelled = pyqtSignal()
    
    def __init__(
        self, 
        database_handler,
        login_system,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._database_handler = database_handler
        self._login_system = login_system
        self._init_ui()
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Define wizard steps
        steps = [
            WizardStep(
                key="type",
                title="Select Type",
                description="Choose schedule type",
                icon="1",
            ),
            WizardStep(
                key="animals",
                title="Select Animals",
                description="Choose animals",
                icon="2",
            ),
            WizardStep(
                key="parameters",
                title="Configure",
                description="Set parameters",
                icon="3",
            ),
            WizardStep(
                key="review",
                title="Review & Save",
                description="Confirm settings",
                icon="4",
            ),
        ]
        
        # Create wizard container
        self._wizard = WizardContainer(steps)
        self._wizard.step_changed.connect(self._on_step_changed)
        self._wizard.completed.connect(self._on_complete)
        self._wizard.cancelled.connect(self.cancelled.emit)
        
        # Create step content widgets
        self._step1 = Step1SelectType()
        self._step1.selection_changed.connect(self._on_type_selected)
        
        self._step2 = Step2SelectAnimals(self._database_handler)
        self._step2.selection_changed.connect(self._on_animals_selected)
        
        self._step3 = Step3ConfigureParameters()
        
        self._step4 = Step4Review()
        self._step4.save_without_running.connect(self._save_without_running)
        
        # Add step contents to wizard
        self._wizard.add_step_content("type", self._step1)
        self._wizard.add_step_content("animals", self._step2)
        self._wizard.add_step_content("parameters", self._step3)
        self._wizard.add_step_content("review", self._step4)
        
        layout.addWidget(self._wizard)
        
        # Start at step 0
        self._wizard.set_current_step(0)
        self._wizard.set_next_enabled(False)  # Disabled until type selected
    
    def _on_step_changed(self, step_index: int) -> None:
        """Handle step changes to load data."""
        if step_index == 1:
            # Step 2: Load animals
            trainer = self._login_system.get_current_trainer()
            trainer_id = trainer.get("trainer_id") if trainer else None
            self._step2.load_animals(trainer_id)
            self._wizard.set_next_enabled(self._step2.is_valid())
        
        elif step_index == 2:
            # Step 3: Pass selected animals and schedule type
            schedule_type = self._step1.get_selected_type()
            selected_animals = self._step2.get_selected_animals_data()
            self._step3.set_animals(selected_animals)
            self._step3.set_schedule_type(schedule_type or "staggered")
            self._wizard.set_next_enabled(True)  # Will validate on next
        
        elif step_index == 3:
            # Step 4: Build review summary
            config = self._build_config()
            self._step4.set_config(config)
    
    def _on_type_selected(self, type_key: str) -> None:
        """Handle schedule type selection."""
        self._wizard.set_next_enabled(True)
    
    def _on_animals_selected(self, animals: List[int]) -> None:
        """Handle animal selection changes."""
        self._wizard.set_next_enabled(len(animals) > 0)
    
    def _build_config(self) -> Dict[str, Any]:
        """Build the complete configuration dict."""
        return {
            "schedule_type": self._step1.get_selected_type(),
            "animals": self._step2.get_selected_animals(),
            "parameters": self._step3.get_parameters(),
        }
    
    def _on_complete(self) -> None:
        """Handle wizard completion - create and run schedule."""
        config = self._build_config()
        
        # Validate
        params = config.get("parameters", {})
        if not params.get("name", "").strip():
            QMessageBox.warning(self, "Validation Error", 
                               "Please enter a schedule name.")
            self._wizard.set_current_step(2)
            return
        
        # Create schedule in database
        try:
            schedule = self._create_schedule(config)
            if schedule:
                self.schedule_created.emit(config)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create schedule: {e}")
    
    def _save_without_running(self) -> None:
        """Save schedule without immediately running it."""
        config = self._build_config()
        
        # Validate
        params = config.get("parameters", {})
        if not params.get("name", "").strip():
            QMessageBox.warning(self, "Validation Error", 
                               "Please enter a schedule name.")
            return
        
        try:
            schedule = self._create_schedule(config)
            if schedule:
                QMessageBox.information(self, "Success", 
                    f"Schedule '{params['name']}' saved successfully!")
                self.schedule_created.emit(config)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save schedule: {e}")
    
    def _create_schedule(self, config: Dict[str, Any]) -> Optional[int]:
        """Create schedule in database using existing Schedule model and correct methods."""
        from models.Schedule import Schedule
        
        params = config["parameters"]
        schedule_type = config["schedule_type"]
        animals = config["animals"]
        animal_configs = params.get("animal_configs", {})
        
        trainer = self._login_system.get_current_trainer()
        trainer_id = trainer.get("trainer_id", 1) if trainer else 1
        is_super = 1 if trainer and trainer.get("role") == "super" else 0
        
        # Calculate overall schedule window from per-animal configs
        all_starts = []
        all_ends = []
        total_volume = 0.0
        
        for animal_id, cfg in animal_configs.items():
            if schedule_type == "staggered":
                start = cfg.get("start_time", datetime.now())
                end = cfg.get("end_time", datetime.now() + timedelta(hours=12))
                all_starts.append(start)
                all_ends.append(end)
            else:
                delivery = cfg.get("delivery_time", datetime.now())
                all_starts.append(delivery)
                all_ends.append(delivery)
            total_volume += cfg.get("volume", 1.0)
        
        # Use earliest start and latest end as schedule bounds
        if all_starts:
            schedule_start = min(all_starts)
            schedule_end = max(all_ends)
        else:
            schedule_start = datetime.now()
            schedule_end = datetime.now() + timedelta(hours=12)
        
        # Create Schedule object
        schedule = Schedule(
            schedule_id=None,  # Will be set by database
            name=params.get("name", "Untitled Schedule"),
            water_volume=total_volume,
            start_time=schedule_start.isoformat() if isinstance(schedule_start, datetime) else schedule_start,
            end_time=schedule_end.isoformat() if isinstance(schedule_end, datetime) else schedule_end,
            created_by=trainer_id,
            is_super_user=is_super,
            delivery_mode=schedule_type,
        )
        
        # Add animals with their individual configs
        for animal_id in animals:
            animal_cfg = animal_configs.get(animal_id, {})
            volume = animal_cfg.get("volume", 1.0)
            relay_unit_id = animal_id  # 1:1 mapping in solenoid mode
            
            schedule.add_animal(animal_id, relay_unit_id, volume)
        
        # Save to database using the CORRECT method for each mode
        if schedule_type == "staggered":
            # Use add_staggered_schedule which inserts into schedule_desired_outputs
            # IMPORTANT: Capture the returned schedule_id (method doesn't set it on object)
            schedule_id = self._database_handler.add_staggered_schedule(schedule)
            print(f"[Wizard] Created staggered schedule {schedule_id} with {len(animals)} animals")
            print(f"[Wizard] desired_water_outputs: {schedule.desired_water_outputs}")
        else:
            # For instant mode, use add_schedule and then add instant deliveries
            self._database_handler.add_schedule(schedule)
            schedule_id = schedule.schedule_id  # add_schedule sets this on the object
            
            if schedule_id:
                for animal_id in animals:
                    animal_cfg = animal_configs.get(animal_id, {})
                    delivery_time = animal_cfg.get("delivery_time", datetime.now())
                    volume = animal_cfg.get("volume", 1.0)
                    
                    self._database_handler.add_schedule_instant(
                        schedule_id=schedule_id,
                        animal_id=animal_id,
                        delivery_time=delivery_time,
                        water_volume=volume
                    )
                print(f"[Wizard] Created instant schedule {schedule_id} with {len(animals)} animals")
        
        return schedule_id
    
    def reset(self) -> None:
        """Reset wizard to initial state."""
        self._wizard.reset()
        self._wizard.set_next_enabled(False)

