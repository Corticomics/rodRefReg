# ui/schedules_hub.py
"""
Schedules Hub - Central view for managing water delivery schedules.

Features:
- View all schedules in a grid layout (3-4 per row)
- Search bar to filter schedules
- Create new schedules via Wizard redirect
- Edit existing schedules in-place
- Delete schedules with confirmation
- Drag schedules to Run/Stop section for execution

Design Principles:
- Clean, modern UI following Material Design principles
- Single responsibility: view and manage schedules
- Schedule creation delegated to Wizard tab
- Consistent styling with app theme
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox, QMenu, QSizePolicy, QScrollArea,
    QLineEdit, QGridLayout, QDialog, QFormLayout, QGroupBox,
    QDateTimeEdit, QDoubleSpinBox, QDialogButtonBox, QSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData, QPoint, QDateTime
from PyQt5.QtGui import QDrag, QPixmap, QPainter, QColor, QFont, QLinearGradient, QPen

from models.Schedule import Schedule


# ============================================================================
# SCHEDULE EDIT DIALOG
# ============================================================================

class ScheduleEditDialog(QDialog):
    """
    Dialog for editing an existing schedule.
    
    Features:
    - Edit schedule name
    - Modify time window (start/end)
    - Adjust volume per animal
    - Review and save changes
    
    Design: Mimics the wizard Step 3/4 interface for consistency
    """
    
    def __init__(self, schedule: Schedule, database_handler, system_controller=None, parent=None):
        super().__init__(parent)
        self._schedule = schedule
        self._database_handler = database_handler
        self._system_controller = system_controller
        self._schedule_details = None
        self._animal_widgets = {}
        
        self.setWindowTitle(f"Edit Schedule: {schedule.name}")
        self.setMinimumSize(600, 500)
        self.setModal(True)
        
        self._load_schedule_details()
        self._init_ui()
    
    def _load_schedule_details(self) -> None:
        """Load full schedule details from database."""
        try:
            details = self._database_handler.get_schedule_details(self._schedule.schedule_id)
            if details:
                self._schedule_details = details[0]
            else:
                self._schedule_details = {}
        except Exception as e:
            print(f"[EditDialog] Error loading details: {e}")
            self._schedule_details = {}
    
    def _init_ui(self) -> None:
        """Build the edit dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel(f"✏️ Editing: {self._schedule.name}")
        header.setStyleSheet("font-size: 16px; font-weight: 600; color: #1a1a1a;")
        layout.addWidget(header)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)
        
        # ═══════════════════════════════════════════════════════════════
        # BASIC INFO
        # ═══════════════════════════════════════════════════════════════
        basic_group = QGroupBox("Schedule Information")
        basic_layout = QFormLayout(basic_group)
        basic_layout.setSpacing(12)
        
        # Name
        self._name_input = QLineEdit(self._schedule.name or "")
        self._name_input.setMinimumHeight(36)
        basic_layout.addRow("Name:", self._name_input)
        
        # Mode (read-only)
        mode = self._schedule_details.get('delivery_mode', 'staggered') if self._schedule_details else 'staggered'
        mode_label = QLabel(mode.capitalize())
        mode_label.setStyleSheet("font-weight: 500; color: #0D9488;")
        basic_layout.addRow("Mode:", mode_label)
        
        content_layout.addWidget(basic_group)
        
        # ═══════════════════════════════════════════════════════════════
        # TIME WINDOW
        # ═══════════════════════════════════════════════════════════════
        time_group = QGroupBox("Time Window")
        time_layout = QFormLayout(time_group)
        time_layout.setSpacing(12)
        
        # Parse existing times
        try:
            if isinstance(self._schedule.start_time, str):
                start_dt = datetime.fromisoformat(self._schedule.start_time)
            else:
                start_dt = self._schedule.start_time or datetime.now()
        except:
            start_dt = datetime.now()
        
        try:
            if isinstance(self._schedule.end_time, str):
                end_dt = datetime.fromisoformat(self._schedule.end_time)
            else:
                end_dt = self._schedule.end_time or (datetime.now() + timedelta(hours=12))
        except:
            end_dt = datetime.now() + timedelta(hours=12)
        
        self._start_input = QDateTimeEdit()
        self._start_input.setDateTime(QDateTime(start_dt))
        self._start_input.setCalendarPopup(True)
        self._start_input.setMinimumHeight(36)
        time_layout.addRow("Start:", self._start_input)
        
        self._end_input = QDateTimeEdit()
        self._end_input.setDateTime(QDateTime(end_dt))
        self._end_input.setCalendarPopup(True)
        self._end_input.setMinimumHeight(36)
        time_layout.addRow("End:", self._end_input)
        
        content_layout.addWidget(time_group)
        
        # ═══════════════════════════════════════════════════════════════
        # ANIMAL VOLUMES
        # ═══════════════════════════════════════════════════════════════
        animals_group = QGroupBox("Animal Volumes")
        animals_layout = QVBoxLayout(animals_group)
        
        desired_outputs = self._schedule_details.get('desired_water_outputs', {}) if self._schedule_details else {}
        animal_ids = self._schedule_details.get('animal_ids', []) if self._schedule_details else []
        
        if animal_ids:
            for animal_id in animal_ids:
                row = QHBoxLayout()
                
                # Get animal info
                try:
                    animal = self._database_handler.get_animal_by_id(animal_id)
                    animal_name = f"{animal.lab_animal_id} - {animal.name}" if animal else f"Animal {animal_id}"
                except:
                    animal_name = f"Animal {animal_id}"
                
                label = QLabel(animal_name)
                label.setMinimumWidth(150)
                row.addWidget(label)
                
                volume = desired_outputs.get(str(animal_id), self._schedule.water_volume or 1.0)
                volume_input = QDoubleSpinBox()
                volume_input.setRange(0.1, 50.0)
                volume_input.setValue(float(volume) if volume else 1.0)
                volume_input.setSuffix(" mL")
                volume_input.setDecimals(2)
                volume_input.setMinimumHeight(32)
                row.addWidget(volume_input)
                
                row.addStretch()
                
                animals_layout.addLayout(row)
                self._animal_widgets[animal_id] = volume_input
        else:
            no_animals = QLabel("No animals in this schedule")
            no_animals.setStyleSheet("color: #9CA3AF; font-style: italic;")
            animals_layout.addWidget(no_animals)
        
        content_layout.addWidget(animals_group)
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        
        # ═══════════════════════════════════════════════════════════════
        # BUTTONS
        # ═══════════════════════════════════════════════════════════════
        button_box = QDialogButtonBox()
        
        save_btn = QPushButton("Save Changes")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #0D9488;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0F766E;
            }
        """)
        save_btn.clicked.connect(self._save_changes)
        button_box.addButton(save_btn, QDialogButtonBox.AcceptRole)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F3F4F6;
                color: #374151;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 10px 24px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #E5E7EB;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_box.addButton(cancel_btn, QDialogButtonBox.RejectRole)
        
        layout.addWidget(button_box)
    
    def _save_changes(self) -> None:
        """Save the edited schedule to database."""
        try:
            new_name = self._name_input.text().strip()
            if not new_name:
                QMessageBox.warning(self, "Validation Error", "Schedule name cannot be empty.")
                return
            
            # Update schedule in database
            new_start = self._start_input.dateTime().toPyDateTime()
            new_end = self._end_input.dateTime().toPyDateTime()
            
            if new_start >= new_end:
                QMessageBox.warning(self, "Validation Error", "End time must be after start time.")
                return
            
            # Collect new volumes
            new_volumes = {}
            for animal_id, widget in self._animal_widgets.items():
                new_volumes[str(animal_id)] = widget.value()
            
            # Update database
            self._database_handler.update_schedule(
                schedule_id=self._schedule.schedule_id,
                name=new_name,
                start_time=new_start.isoformat(),
                end_time=new_end.isoformat(),
                desired_outputs=new_volumes
            )
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save changes: {e}")
            print(f"[EditDialog] Save error: {e}")
            import traceback
            traceback.print_exc()


# ============================================================================
# SCHEDULE CARD (Compact for grid layout)
# ============================================================================

class ScheduleCard(QFrame):
    """
    Compact Material Design card for grid layout (3-4 per row).
    """
    
    clicked = pyqtSignal(object)
    edit_requested = pyqtSignal(object)
    delete_requested = pyqtSignal(object)
    drag_started = pyqtSignal(object)
    
    def __init__(self, schedule: Schedule, database_handler, parent=None):
        super().__init__(parent)
        self._schedule = schedule
        self._database_handler = database_handler
        self._selected = False
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Build compact card UI."""
        self.setObjectName("ScheduleCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        # Fixed size for grid layout
        self.setFixedHeight(100)
        self.setMinimumWidth(200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        # Header: Name + Mode badge
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        name_label = QLabel(self._schedule.name or "Untitled")
        name_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #1a1a1a;")
        name_label.setWordWrap(False)
        # Truncate long names
        if len(name_label.text()) > 20:
            name_label.setText(name_label.text()[:18] + "...")
            name_label.setToolTip(self._schedule.name)
        header_layout.addWidget(name_label, 1)
        
        # Mode badge (compact)
        mode = getattr(self._schedule, 'delivery_mode', 'staggered') or 'staggered'
        mode_badge = QLabel(mode[:1].upper())  # Just first letter: S or I
        badge_color = "#0D9488" if mode == "staggered" else "#6366F1"
        mode_badge.setStyleSheet(f"""
            background-color: {badge_color}; 
            color: white;
            padding: 2px 6px; 
            border-radius: 8px; 
            font-weight: 600; 
            font-size: 9px;
        """)
        mode_badge.setToolTip(mode.capitalize())
        header_layout.addWidget(mode_badge)
        
        layout.addLayout(header_layout)
        
        # Info row: Animals + Time
        info_layout = QHBoxLayout()
        info_layout.setSpacing(8)
        
        animal_count = len(self._schedule.animals) if hasattr(self._schedule, 'animals') and self._schedule.animals else 0
        animals_label = QLabel(f"🐭 {animal_count}")
        animals_label.setStyleSheet("color: #64748B; font-size: 11px;")
        info_layout.addWidget(animals_label)
        
        # Time
        if hasattr(self._schedule, 'start_time') and self._schedule.start_time:
            try:
                if isinstance(self._schedule.start_time, str):
                    start = datetime.fromisoformat(self._schedule.start_time)
                else:
                    start = self._schedule.start_time
                time_str = start.strftime("%m/%d %H:%M")
            except:
                time_str = ""
        else:
            time_str = ""
        
        if time_str:
            time_label = QLabel(f"⏰ {time_str}")
            time_label.setStyleSheet("color: #64748B; font-size: 11px;")
            info_layout.addWidget(time_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # Hint (smaller)
        hint = QLabel("Drag to run • Right-click to edit")
        hint.setStyleSheet("color: #9CA3AF; font-size: 9px;")
        layout.addWidget(hint)
        
        # Styling
        self.setStyleSheet("""
            QFrame#ScheduleCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
            QFrame#ScheduleCard:hover {
                border: 1px solid #0D9488;
                background-color: #F0FDFA;
            }
        """)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
            self.clicked.emit(self._schedule)
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not hasattr(self, '_drag_start_pos'):
            return
        if (event.pos() - self._drag_start_pos).manhattanLength() < 10:
            return
        self._start_drag()
    
    def _start_drag(self) -> None:
        """Initiate drag operation."""
        schedule = self._schedule
        
        try:
            schedule_details = self._database_handler.get_schedule_details(schedule.schedule_id)
            if not schedule_details:
                return
            schedule_detail = schedule_details[0]
        except Exception as e:
            print(f"[ScheduleCard] Error: {e}")
            return
        
        mime_data = QMimeData()
        schedule_data = {
            'schedule_id': schedule.schedule_id,
            'name': schedule.name,
            'water_volume': schedule.water_volume,
            'start_time': schedule.start_time,
            'end_time': schedule.end_time,
            'created_by': schedule.created_by,
            'is_super_user': schedule.is_super_user,
            'delivery_mode': schedule_detail['delivery_mode'],
            'animals': schedule_detail['animal_ids'],
            'desired_water_outputs': schedule_detail.get('desired_water_outputs', {}),
            'instant_deliveries': schedule_detail.get('delivery_schedule', [])
        }
        
        mime_data.setData('application/x-schedule', str(schedule_data).encode())
        
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        
        # Compact drag pixmap
        pixmap = QPixmap(200, 50)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        gradient = QLinearGradient(0, 0, 0, 50)
        gradient.setColorAt(0, QColor("#e8f0fe"))
        gradient.setColorAt(1, QColor("#c2d9fc"))
        
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor("#1a73e8"), 2))
        painter.drawRoundedRect(0, 0, 200, 50, 8, 8)
        
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.setPen(QColor("#1a73e8"))
        painter.drawText(10, 25, f"📋 {schedule.name[:20]}")
        
        painter.setFont(QFont("Arial", 8))
        painter.setPen(QColor("#5f6368"))
        painter.drawText(10, 42, "Drop on Run/Stop...")
        
        painter.end()
        
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(100, 25))
        
        self.drag_started.emit(self._schedule)
        drag.exec_(Qt.CopyAction)
    
    def _show_context_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        
        edit_action = menu.addAction("✏️ Edit")
        edit_action.triggered.connect(lambda: self.edit_requested.emit(self._schedule))
        
        menu.addSeparator()
        
        delete_action = menu.addAction("🗑️ Delete")
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self._schedule))
        
        menu.exec_(self.mapToGlobal(pos))
    
    @property
    def schedule(self) -> Schedule:
        return self._schedule


# ============================================================================
# SCHEDULES HUB (Main Widget)
# ============================================================================

class SchedulesHub(QWidget):
    """
    Schedules Hub - Central management view with grid layout and search.
    """
    
    mode_changed = pyqtSignal(str)
    assignments_cleared = pyqtSignal()
    create_requested = pyqtSignal()
    schedule_selected = pyqtSignal(object)
    
    def __init__(self, settings, print_to_terminal, database_handler, login_system,
                 system_controller=None, parent=None):
        super().__init__(parent)
        
        self.settings = settings
        self.print_to_terminal = print_to_terminal
        self.database_handler = database_handler
        self.login_system = login_system
        self.system_controller = system_controller
        
        self._schedule_cards: List[ScheduleCard] = []
        self._all_schedules: List[Schedule] = []
        
        self._init_ui()
        self.load_schedules()
        
        self.login_system.login_status_changed.connect(self.refresh)
    
    def _init_ui(self) -> None:
        """Build the hub UI with grid layout and search."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # ═══════════════════════════════════════════════════════════════
        # HEADER: Title + Info Button + New Schedule Button
        # ═══════════════════════════════════════════════════════════════
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        
        title = QLabel("My Schedules")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1a1a1a;")
        header_layout.addWidget(title)
        
        # Discrete info button (small, next to title)
        info_btn = QPushButton("ⓘ")
        info_btn.setFixedSize(24, 24)
        info_btn.setCursor(Qt.WhatsThisCursor)
        info_btn.setToolTip(
            "<b>How to use Schedules</b><br><br>"
            "• <b>Drag</b> a schedule card to Run/Stop to execute it<br>"
            "• <b>Right-click</b> a card for Edit/Delete options<br>"
            "• Use the <b>search bar</b> to find schedules by name<br>"
            "• Click <b>+ New Schedule</b> to create via wizard"
        )
        info_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #6B7280;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                color: #0D9488;
            }
        """)
        header_layout.addWidget(info_btn)
        
        header_layout.addStretch()
        
        # New Schedule Button
        new_btn = QPushButton("+ New Schedule")
        new_btn.setMinimumHeight(36)
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.setStyleSheet("""
            QPushButton {
                background-color: #0D9488;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0F766E;
            }
        """)
        new_btn.clicked.connect(self._on_new_schedule)
        header_layout.addWidget(new_btn)
        
        layout.addWidget(header)
        
        # ═══════════════════════════════════════════════════════════════
        # SEARCH BAR
        # ═══════════════════════════════════════════════════════════════
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("🔍 Search schedules...")
        self._search_input.setMinimumHeight(36)
        self._search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                background-color: #F8FAFB;
            }
            QLineEdit:focus {
                border-color: #0D9488;
                background-color: #FFFFFF;
            }
        """)
        self._search_input.textChanged.connect(self._on_search)
        layout.addWidget(self._search_input)
        
        # ═══════════════════════════════════════════════════════════════
        # SCHEDULES GRID (scrollable)
        # ═══════════════════════════════════════════════════════════════
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self._grid_container = QWidget()
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._grid_layout.setSpacing(10)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll.setWidget(self._grid_container)
        layout.addWidget(scroll, 1)
        
        # ═══════════════════════════════════════════════════════════════
        # EMPTY STATE
        # ═══════════════════════════════════════════════════════════════
        self._empty_state = QWidget()
        empty_layout = QVBoxLayout(self._empty_state)
        empty_layout.setAlignment(Qt.AlignCenter)
        
        empty_icon = QLabel("📋")
        empty_icon.setStyleSheet("font-size: 40px;")
        empty_icon.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_icon)
        
        empty_title = QLabel("No Schedules Yet")
        empty_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #374151;")
        empty_title.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_title)
        
        empty_desc = QLabel("Create your first schedule using the wizard.")
        empty_desc.setStyleSheet("font-size: 12px; color: #6B7280;")
        empty_desc.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_desc)
        
        create_btn = QPushButton("Create Schedule")
        create_btn.clicked.connect(self._on_new_schedule)
        create_btn.setStyleSheet("""
            QPushButton {
                background-color: #0D9488;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0F766E;
            }
        """)
        empty_layout.addWidget(create_btn, alignment=Qt.AlignCenter)
        
        self._empty_state.hide()
        layout.addWidget(self._empty_state)
    
    def _on_new_schedule(self) -> None:
        """Redirect to Wizard tab."""
        self.print_to_terminal("[SchedulesHub] Redirecting to Schedule Wizard...")
        self.create_requested.emit()
    
    def _on_search(self, text: str) -> None:
        """Filter schedules by search text."""
        self._display_schedules(text.strip().lower())
    
    def load_schedules(self) -> None:
        """Load schedules from database."""
        current_trainer = self.login_system.get_current_trainer()
        if current_trainer:
            trainer_id = current_trainer['trainer_id']
            self._all_schedules = self.database_handler.get_schedules_by_trainer(trainer_id)
        else:
            self._all_schedules = self.database_handler.get_all_schedules()
        
        self._display_schedules()
        self.print_to_terminal(f"[SchedulesHub] Loaded {len(self._all_schedules)} schedules")
    
    def _display_schedules(self, filter_text: str = "") -> None:
        """Display schedules in grid layout with optional filter."""
        # Clear existing
        self._clear_grid()
        
        # Filter schedules
        if filter_text:
            schedules = [s for s in self._all_schedules if filter_text in (s.name or "").lower()]
        else:
            schedules = self._all_schedules
        
        # Show empty state if no schedules
        if not schedules:
            self._empty_state.show()
            self._grid_container.hide()
            return
        
        self._empty_state.hide()
        self._grid_container.show()
        
        # Create cards in grid (3 per row)
        cols = 3
        for idx, schedule in enumerate(schedules):
            row = idx // cols
            col = idx % cols
            
            card = ScheduleCard(schedule, self.database_handler)
            card.clicked.connect(self._on_schedule_clicked)
            card.edit_requested.connect(self._on_edit_schedule)
            card.delete_requested.connect(self._on_delete_schedule)
            
            self._schedule_cards.append(card)
            self._grid_layout.addWidget(card, row, col)
        
        # Add spacer columns to prevent cards from stretching
        for col in range(cols):
            self._grid_layout.setColumnStretch(col, 1)
    
    def _clear_grid(self) -> None:
        """Remove all schedule cards."""
        for card in self._schedule_cards:
            card.deleteLater()
        self._schedule_cards.clear()
        
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _on_schedule_clicked(self, schedule: Schedule) -> None:
        self.schedule_selected.emit(schedule)
    
    def _on_edit_schedule(self, schedule: Schedule) -> None:
        """Open edit dialog for schedule."""
        dialog = ScheduleEditDialog(
            schedule=schedule,
            database_handler=self.database_handler,
            system_controller=self.system_controller,
            parent=self
        )
        
        if dialog.exec_() == QDialog.Accepted:
            self.print_to_terminal(f"[SchedulesHub] Schedule '{schedule.name}' updated")
            self.load_schedules()  # Refresh
    
    def _on_delete_schedule(self, schedule: Schedule) -> None:
        """Delete schedule with confirmation."""
        reply = QMessageBox.question(
            self,
            "Delete Schedule",
            f"Are you sure you want to delete '{schedule.name}'?\n\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Use correct method name: remove_schedule
                self.database_handler.remove_schedule(schedule.schedule_id)
                self.print_to_terminal(f"[SchedulesHub] Deleted schedule: {schedule.name}")
                self.load_schedules()  # Refresh
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete schedule: {e}")
                self.print_to_terminal(f"[SchedulesHub] Delete error: {e}")
    
    def refresh(self) -> None:
        """Refresh the schedules list."""
        self._search_input.clear()
        self.load_schedules()
    
    # Compatibility methods
    def load_animals(self) -> None:
        pass
    
    def get_relay_assignments(self) -> Dict:
        return {}
    
    def set_delivery_mode(self, mode: str) -> None:
        self.mode_changed.emit(mode)
    
    def reset_all(self) -> None:
        self.refresh()
    
    def clear_all(self) -> None:
        pass
