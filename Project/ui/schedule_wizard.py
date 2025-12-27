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
        
        try:
            if trainer_id:
                animals = self._database_handler.get_animals_by_trainer(trainer_id)
            else:
                animals = self._database_handler.get_all_animals()
            
            for animal in animals:
                # animal is an Animal object with properties
                animal_id = animal.animal_id
                lab_id = animal.lab_animal_id or animal_id
                name = animal.name or f"Animal {animal_id}"
                
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
    
    def is_valid(self) -> bool:
        """Check if at least one animal is selected."""
        return len(self._selected_animals) > 0


# ============================================================================
# STEP 3: CONFIGURE PARAMETERS
# ============================================================================

class Step3ConfigureParameters(QWidget):
    """Step 3: Configure schedule parameters (times, volumes, etc.)."""
    
    parameters_changed = pyqtSignal(dict)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._schedule_type: str = "staggered"
        self._parameters: Dict[str, Any] = {}
        self._init_ui()
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)
        
        # Step header
        header = self._create_header(
            icon="⚙",
            title="Configure Parameters",
            description="Set timing and volume parameters for your schedule"
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
        
        # Will be populated based on schedule type
        self._build_staggered_params()
    
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
    
    def set_schedule_type(self, schedule_type: str) -> None:
        """Set the schedule type and rebuild parameters."""
        self._schedule_type = schedule_type
        self._clear_params()
        
        if schedule_type == "staggered":
            self._build_staggered_params()
        else:
            self._build_instant_params()
    
    def _clear_params(self) -> None:
        """Clear existing parameter widgets."""
        while self._params_layout.count():
            item = self._params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._parameters = {}
    
    def _build_staggered_params(self) -> None:
        """Build parameter form for staggered delivery."""
        # Schedule Name
        name_group = QGroupBox("Schedule Name")
        name_layout = QFormLayout(name_group)
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Enter a name for this schedule")
        self._name_input.textChanged.connect(lambda v: self._update_param("name", v))
        name_layout.addRow("Name:", self._name_input)
        self._params_layout.addWidget(name_group)
        
        # Time Window
        time_group = QGroupBox("Time Window")
        time_layout = QFormLayout(time_group)
        
        self._start_time = QDateTimeEdit()
        self._start_time.setDateTime(QDateTime.currentDateTime())
        self._start_time.setCalendarPopup(True)
        self._start_time.dateTimeChanged.connect(
            lambda dt: self._update_param("start_time", dt.toPyDateTime())
        )
        time_layout.addRow("Start Time:", self._start_time)
        
        self._end_time = QDateTimeEdit()
        self._end_time.setDateTime(QDateTime.currentDateTime().addSecs(3600 * 12))
        self._end_time.setCalendarPopup(True)
        self._end_time.dateTimeChanged.connect(
            lambda dt: self._update_param("end_time", dt.toPyDateTime())
        )
        time_layout.addRow("End Time:", self._end_time)
        
        self._params_layout.addWidget(time_group)
        
        # Volume Settings
        volume_group = QGroupBox("Volume Settings")
        volume_layout = QFormLayout(volume_group)
        
        self._volume_input = QDoubleSpinBox()
        self._volume_input.setRange(0.1, 50.0)
        self._volume_input.setValue(1.0)
        self._volume_input.setSuffix(" mL")
        self._volume_input.setDecimals(2)
        self._volume_input.valueChanged.connect(
            lambda v: self._update_param("water_volume", v)
        )
        volume_layout.addRow("Total Volume per Animal:", self._volume_input)
        
        self._params_layout.addWidget(volume_group)
        
        # Initialize default values
        self._parameters = {
            "name": "",
            "start_time": datetime.now(),
            "end_time": datetime.now() + timedelta(hours=12),
            "water_volume": 1.0,
        }
        
        self._params_layout.addStretch()
    
    def _build_instant_params(self) -> None:
        """Build parameter form for instant delivery."""
        # Schedule Name
        name_group = QGroupBox("Schedule Name")
        name_layout = QFormLayout(name_group)
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Enter a name for this schedule")
        self._name_input.textChanged.connect(lambda v: self._update_param("name", v))
        name_layout.addRow("Name:", self._name_input)
        self._params_layout.addWidget(name_group)
        
        # Delivery Time
        time_group = QGroupBox("Delivery Time")
        time_layout = QFormLayout(time_group)
        
        self._delivery_time = QDateTimeEdit()
        self._delivery_time.setDateTime(QDateTime.currentDateTime().addSecs(60))
        self._delivery_time.setCalendarPopup(True)
        self._delivery_time.dateTimeChanged.connect(
            lambda dt: self._update_param("delivery_time", dt.toPyDateTime())
        )
        time_layout.addRow("Delivery Time:", self._delivery_time)
        
        self._params_layout.addWidget(time_group)
        
        # Volume Settings
        volume_group = QGroupBox("Volume Settings")
        volume_layout = QFormLayout(volume_group)
        
        self._volume_input = QDoubleSpinBox()
        self._volume_input.setRange(0.1, 50.0)
        self._volume_input.setValue(1.0)
        self._volume_input.setSuffix(" mL")
        self._volume_input.setDecimals(2)
        self._volume_input.valueChanged.connect(
            lambda v: self._update_param("water_volume", v)
        )
        volume_layout.addRow("Volume:", self._volume_input)
        
        self._params_layout.addWidget(volume_group)
        
        # Initialize default values
        self._parameters = {
            "name": "",
            "delivery_time": datetime.now() + timedelta(minutes=1),
            "water_volume": 1.0,
        }
        
        self._params_layout.addStretch()
    
    def _update_param(self, key: str, value: Any) -> None:
        """Update a parameter value."""
        self._parameters[key] = value
        self.parameters_changed.emit(self._parameters)
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get all configured parameters."""
        return self._parameters
    
    def is_valid(self) -> bool:
        """Validate parameters."""
        name = self._parameters.get("name", "").strip()
        if not name:
            return False
        
        if self._schedule_type == "staggered":
            start = self._parameters.get("start_time")
            end = self._parameters.get("end_time")
            if start and end and start >= end:
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
        
        # Summary card
        summary_group = QGroupBox()
        self._summary_layout = QFormLayout(summary_group)
        self._summary_layout.setSpacing(12)
        layout.addWidget(summary_group, 1)
        
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
        """Update the summary display."""
        # Clear existing
        while self._summary_layout.count():
            item = self._summary_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Schedule Type
        schedule_type = self._config.get("schedule_type", "staggered")
        type_info = SCHEDULE_TYPES.get(schedule_type, {})
        self._add_summary_row("Schedule Type:", type_info.get("title", schedule_type))
        
        # Animals
        animals = self._config.get("animals", [])
        self._add_summary_row("Animals:", f"{len(animals)} selected")
        
        # Parameters
        params = self._config.get("parameters", {})
        
        if params.get("name"):
            self._add_summary_row("Name:", params["name"])
        
        if "start_time" in params:
            start = params["start_time"]
            if isinstance(start, datetime):
                self._add_summary_row("Start:", start.strftime("%Y-%m-%d %H:%M"))
        
        if "end_time" in params:
            end = params["end_time"]
            if isinstance(end, datetime):
                self._add_summary_row("End:", end.strftime("%Y-%m-%d %H:%M"))
        
        if "delivery_time" in params:
            delivery = params["delivery_time"]
            if isinstance(delivery, datetime):
                self._add_summary_row("Delivery:", delivery.strftime("%Y-%m-%d %H:%M"))
        
        if "water_volume" in params:
            self._add_summary_row("Volume:", f"{params['water_volume']:.2f} mL")
    
    def _add_summary_row(self, label: str, value: str) -> None:
        """Add a row to the summary."""
        label_widget = QLabel(label)
        label_widget.setStyleSheet("font-weight: 500; color: #4E5D6C;")
        
        value_widget = QLabel(value)
        value_widget.setStyleSheet("font-weight: 600; color: #1A1D1F;")
        value_widget.setAlignment(Qt.AlignRight)
        
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
            # Step 3: Configure params based on type
            schedule_type = self._step1.get_selected_type()
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
        """Create schedule in database using existing logic."""
        params = config["parameters"]
        schedule_type = config["schedule_type"]
        animals = config["animals"]
        
        trainer = self._login_system.get_current_trainer()
        trainer_id = trainer.get("trainer_id", 1) if trainer else 1
        is_super = trainer.get("role") == "super" if trainer else False
        
        # Build schedule data
        if schedule_type == "staggered":
            start_time = params.get("start_time", datetime.now())
            end_time = params.get("end_time", datetime.now() + timedelta(hours=12))
            
            schedule_id = self._database_handler.add_schedule(
                name=params["name"],
                water_volume=params.get("water_volume", 1.0),
                start_time=start_time.isoformat() if isinstance(start_time, datetime) else start_time,
                end_time=end_time.isoformat() if isinstance(end_time, datetime) else end_time,
                created_by=trainer_id,
                is_super_user=is_super,
                delivery_mode="staggered"
            )
        else:
            # Instant mode
            delivery_time = params.get("delivery_time", datetime.now())
            
            schedule_id = self._database_handler.add_schedule(
                name=params["name"],
                water_volume=params.get("water_volume", 1.0),
                start_time=delivery_time.isoformat() if isinstance(delivery_time, datetime) else delivery_time,
                end_time=delivery_time.isoformat() if isinstance(delivery_time, datetime) else delivery_time,
                created_by=trainer_id,
                is_super_user=is_super,
                delivery_mode="instant"
            )
        
        if schedule_id:
            # Add animal assignments
            for animal_id in animals:
                # Get relay unit for animal (cage = relay unit in solenoid mode)
                relay_unit_id = animal_id  # Simple 1:1 mapping for now
                self._database_handler.add_schedule_animal(
                    schedule_id=schedule_id,
                    animal_id=animal_id,
                    relay_unit_id=relay_unit_id,
                    desired_output=params.get("water_volume", 1.0)
                )
            
            print(f"[Wizard] Created schedule {schedule_id} with {len(animals)} animals")
        
        return schedule_id
    
    def reset(self) -> None:
        """Reset wizard to initial state."""
        self._wizard.reset()
        self._wizard.set_next_enabled(False)

