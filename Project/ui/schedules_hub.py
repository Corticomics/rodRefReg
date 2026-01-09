# ui/schedules_hub.py
"""
Schedules Hub - Central view for managing water delivery schedules.

This replaces the legacy drag-and-drop schedule setup with a cleaner hub interface.

Features:
- View all schedules in a clean table/card layout
- Create new schedules via Wizard redirect
- Edit existing schedules
- Delete schedules with confirmation
- Drag schedules to Run/Stop section for execution

Design Principles:
- Clean, modern UI following Material Design principles
- Single responsibility: view and manage schedules
- Schedule creation delegated to Wizard tab
- Consistent styling with app theme

Reference: Material Design Data Tables
https://material.io/components/data-tables
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, List
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QMessageBox, QMenu, QAbstractItemView, QSizePolicy,
    QGroupBox, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData, QPoint
from PyQt5.QtGui import QDrag, QPixmap, QPainter, QColor, QFont, QLinearGradient, QPen

from models.Schedule import Schedule


class ScheduleCard(QFrame):
    """
    Material Design card representing a single schedule.
    
    Supports:
    - Display of schedule info
    - Click to select
    - Drag to Run/Stop section
    - Context menu for edit/delete
    """
    
    clicked = pyqtSignal(object)  # Emits schedule object
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
        """Build card UI."""
        self.setObjectName("ScheduleCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        # Enable drag
        self.setAcceptDrops(False)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # Header row: Name + Mode badge
        header_layout = QHBoxLayout()
        
        name_label = QLabel(self._schedule.name or "Untitled")
        name_label.setObjectName("ScheduleCardTitle")
        name_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #1a1a1a;")
        header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        
        # Mode badge
        mode = getattr(self._schedule, 'delivery_mode', 'staggered') or 'staggered'
        mode_badge = QLabel(mode.capitalize())
        mode_badge.setObjectName("ModeBadge")
        badge_color = "#0D9488" if mode == "staggered" else "#6366F1"
        mode_badge.setStyleSheet(f"""
            background-color: {badge_color}; 
            color: white;
            padding: 3px 8px; 
            border-radius: 10px; 
            font-weight: 500; 
            font-size: 10px;
        """)
        header_layout.addWidget(mode_badge)
        
        layout.addLayout(header_layout)
        
        # Info row: Animals count + Time
        info_layout = QHBoxLayout()
        
        # Get animal count from schedule
        animal_count = len(self._schedule.animals) if hasattr(self._schedule, 'animals') and self._schedule.animals else 0
        animals_label = QLabel(f"🐭 {animal_count} animals")
        animals_label.setStyleSheet("color: #64748B; font-size: 12px;")
        info_layout.addWidget(animals_label)
        
        info_layout.addStretch()
        
        # Created time
        if hasattr(self._schedule, 'start_time') and self._schedule.start_time:
            try:
                if isinstance(self._schedule.start_time, str):
                    start = datetime.fromisoformat(self._schedule.start_time)
                else:
                    start = self._schedule.start_time
                time_str = start.strftime("%m/%d %H:%M")
            except:
                time_str = "N/A"
        else:
            time_str = "N/A"
        
        time_label = QLabel(f"⏰ {time_str}")
        time_label.setStyleSheet("color: #64748B; font-size: 12px;")
        info_layout.addWidget(time_label)
        
        layout.addLayout(info_layout)
        
        # Drag hint
        hint = QLabel("Drag to Run/Stop to execute")
        hint.setStyleSheet("color: #9CA3AF; font-size: 10px; font-style: italic;")
        layout.addWidget(hint)
        
        # Card styling
        self.setStyleSheet("""
            QFrame#ScheduleCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
            QFrame#ScheduleCard:hover {
                border: 1px solid #0D9488;
                background-color: #F0FDFA;
            }
        """)
    
    def mousePressEvent(self, event):
        """Handle mouse press for drag start."""
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
            self.clicked.emit(self._schedule)
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for drag initiation."""
        if not (event.buttons() & Qt.LeftButton):
            return
        if not hasattr(self, '_drag_start_pos'):
            return
        
        # Check if drag distance threshold met
        if (event.pos() - self._drag_start_pos).manhattanLength() < 10:
            return
        
        self._start_drag()
    
    def _start_drag(self) -> None:
        """Initiate drag operation with schedule data."""
        schedule = self._schedule
        
        # Get schedule details from database
        try:
            schedule_details = self._database_handler.get_schedule_details(schedule.schedule_id)
            if not schedule_details:
                return
            
            schedule_detail = schedule_details[0]
        except Exception as e:
            print(f"[ScheduleCard] Error getting schedule details: {e}")
            return
        
        # Create mime data
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
        
        # Create drag pixmap
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        
        # Visual representation
        pixmap = QPixmap(280, 70)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Gradient background
        gradient = QLinearGradient(0, 0, 0, 70)
        gradient.setColorAt(0, QColor("#e8f0fe"))
        gradient.setColorAt(1, QColor("#c2d9fc"))
        
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor("#1a73e8"), 2))
        painter.drawRoundedRect(0, 0, pixmap.width(), pixmap.height(), 10, 10)
        
        # Schedule name
        painter.setFont(QFont("Arial", 11, QFont.Bold))
        painter.setPen(QColor("#1a73e8"))
        painter.drawText(15, 25, f"📋 {schedule.name}")
        
        # Mode and count
        painter.setFont(QFont("Arial", 9))
        painter.setPen(QColor("#5f6368"))
        mode = schedule_detail.get('delivery_mode', 'staggered').capitalize()
        count = len(schedule_detail.get('animal_ids', []))
        painter.drawText(15, 45, f"{mode} • {count} animals")
        
        # Hint
        painter.drawText(15, 60, "Drop on Run/Stop to execute...")
        
        painter.end()
        
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
        
        self.drag_started.emit(self._schedule)
        drag.exec_(Qt.CopyAction)
    
    def _show_context_menu(self, pos: QPoint) -> None:
        """Show context menu for edit/delete."""
        menu = QMenu(self)
        
        edit_action = menu.addAction("✏️ Edit Schedule")
        edit_action.triggered.connect(lambda: self.edit_requested.emit(self._schedule))
        
        menu.addSeparator()
        
        delete_action = menu.addAction("🗑️ Delete Schedule")
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self._schedule))
        
        menu.exec_(self.mapToGlobal(pos))
    
    @property
    def schedule(self) -> Schedule:
        return self._schedule


class SchedulesHub(QWidget):
    """
    Schedules Hub - Central management view for schedules.
    
    Replaces the legacy drag-and-drop SchedulesTab with a cleaner interface
    that focuses on viewing, managing, and executing schedules.
    
    Features:
    - Grid of schedule cards
    - "+ New Schedule" redirects to Wizard tab
    - Edit/Delete via context menu
    - Drag to Run/Stop for execution
    
    Signals:
        mode_changed: Compatibility signal for Run/Stop section
        create_requested: Emitted when user wants to create new schedule
        schedule_selected: Emitted when a schedule is clicked
    """
    
    mode_changed = pyqtSignal(str)  # Compatibility with RunStopSection
    assignments_cleared = pyqtSignal()  # Compatibility signal
    create_requested = pyqtSignal()  # Request to switch to Wizard tab
    schedule_selected = pyqtSignal(object)  # When schedule is clicked
    
    def __init__(self, settings, print_to_terminal, database_handler, login_system,
                 system_controller=None, parent=None):
        super().__init__(parent)
        
        self.settings = settings
        self.print_to_terminal = print_to_terminal
        self.database_handler = database_handler
        self.login_system = login_system
        self.system_controller = system_controller
        
        self._schedule_cards: List[ScheduleCard] = []
        
        self._init_ui()
        self.load_schedules()
        
        # Connect to login changes
        self.login_system.login_status_changed.connect(self.refresh)
    
    def _init_ui(self) -> None:
        """Build the hub UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # ═══════════════════════════════════════════════════════════════
        # HEADER: Title + New Schedule Button
        # ═══════════════════════════════════════════════════════════════
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("My Schedules")
        title.setObjectName("Title")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #1a1a1a;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # New Schedule Button
        self.new_schedule_btn = QPushButton("+ New Schedule")
        self.new_schedule_btn.setProperty("variant", "primary")
        self.new_schedule_btn.setMinimumHeight(40)
        self.new_schedule_btn.setCursor(Qt.PointingHandCursor)
        self.new_schedule_btn.setStyleSheet("""
            QPushButton {
                background-color: #0D9488;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0F766E;
            }
            QPushButton:pressed {
                background-color: #115E59;
            }
        """)
        self.new_schedule_btn.clicked.connect(self._on_new_schedule)
        header_layout.addWidget(self.new_schedule_btn)
        
        layout.addWidget(header)
        
        # ═══════════════════════════════════════════════════════════════
        # INFO BAR
        # ═══════════════════════════════════════════════════════════════
        info_bar = QFrame()
        info_bar.setStyleSheet("""
            QFrame {
                background-color: #F0F9FF;
                border: 1px solid #BAE6FD;
                border-radius: 8px;
                padding: 8px 12px;
            }
        """)
        info_layout = QHBoxLayout(info_bar)
        info_layout.setContentsMargins(12, 8, 12, 8)
        
        info_icon = QLabel("ℹ️")
        info_layout.addWidget(info_icon)
        
        info_text = QLabel(
            "Drag a schedule to the Run/Stop section to execute it. "
            "Right-click for edit/delete options."
        )
        info_text.setStyleSheet("color: #0369A1; font-size: 12px;")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text, 1)
        
        layout.addWidget(info_bar)
        
        # ═══════════════════════════════════════════════════════════════
        # SCHEDULES GRID (scrollable)
        # ═══════════════════════════════════════════════════════════════
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self._grid_container = QWidget()
        self._grid_layout = QVBoxLayout(self._grid_container)
        self._grid_layout.setAlignment(Qt.AlignTop)
        self._grid_layout.setSpacing(12)
        
        scroll.setWidget(self._grid_container)
        layout.addWidget(scroll, 1)
        
        # ═══════════════════════════════════════════════════════════════
        # EMPTY STATE (shown when no schedules)
        # ═══════════════════════════════════════════════════════════════
        self._empty_state = QWidget()
        empty_layout = QVBoxLayout(self._empty_state)
        empty_layout.setAlignment(Qt.AlignCenter)
        
        empty_icon = QLabel("📋")
        empty_icon.setStyleSheet("font-size: 48px;")
        empty_icon.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_icon)
        
        empty_title = QLabel("No Schedules Yet")
        empty_title.setStyleSheet("font-size: 16px; font-weight: 600; color: #374151;")
        empty_title.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_title)
        
        empty_desc = QLabel("Create your first schedule using the wizard.")
        empty_desc.setStyleSheet("font-size: 13px; color: #6B7280;")
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
                padding: 10px 24px;
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
        """Handle new schedule button - emit signal to switch to Wizard tab."""
        self.print_to_terminal("[SchedulesHub] Redirecting to Schedule Wizard...")
        self.create_requested.emit()
    
    def load_schedules(self) -> None:
        """Load schedules from database and display as cards."""
        # Clear existing cards
        self._clear_grid()
        
        # Get schedules based on login status
        current_trainer = self.login_system.get_current_trainer()
        if current_trainer:
            trainer_id = current_trainer['trainer_id']
            schedules = self.database_handler.get_schedules_by_trainer(trainer_id)
        else:
            schedules = self.database_handler.get_all_schedules()
        
        # Show/hide empty state
        if not schedules:
            self._empty_state.show()
            self._grid_container.hide()
            return
        
        self._empty_state.hide()
        self._grid_container.show()
        
        # Create cards for each schedule
        for schedule in schedules:
            card = ScheduleCard(schedule, self.database_handler)
            card.clicked.connect(self._on_schedule_clicked)
            card.edit_requested.connect(self._on_edit_schedule)
            card.delete_requested.connect(self._on_delete_schedule)
            
            self._schedule_cards.append(card)
            self._grid_layout.addWidget(card)
        
        self.print_to_terminal(f"[SchedulesHub] Loaded {len(schedules)} schedules")
    
    def _clear_grid(self) -> None:
        """Remove all schedule cards."""
        for card in self._schedule_cards:
            card.deleteLater()
        self._schedule_cards.clear()
        
        # Clear layout
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _on_schedule_clicked(self, schedule: Schedule) -> None:
        """Handle schedule card click."""
        self.schedule_selected.emit(schedule)
    
    def _on_edit_schedule(self, schedule: Schedule) -> None:
        """Handle edit request - show message (edit via wizard not implemented yet)."""
        QMessageBox.information(
            self,
            "Edit Schedule",
            f"Editing '{schedule.name}' is not yet implemented.\n\n"
            "To modify this schedule, please delete it and create a new one using the wizard."
        )
    
    def _on_delete_schedule(self, schedule: Schedule) -> None:
        """Handle delete request with confirmation."""
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
                self.database_handler.delete_schedule(schedule.schedule_id)
                self.print_to_terminal(f"[SchedulesHub] Deleted schedule: {schedule.name}")
                self.load_schedules()  # Refresh
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete schedule: {e}")
                self.print_to_terminal(f"[SchedulesHub] Delete error: {e}")
    
    def refresh(self) -> None:
        """Refresh the schedules list."""
        self.load_schedules()
    
    # ═══════════════════════════════════════════════════════════════
    # COMPATIBILITY METHODS
    # These exist to maintain compatibility with existing code
    # ═══════════════════════════════════════════════════════════════
    
    def load_animals(self) -> None:
        """Compatibility: No-op, animals not needed in hub view."""
        pass
    
    def get_relay_assignments(self) -> Dict:
        """Compatibility: Return empty dict."""
        return {}
    
    def set_delivery_mode(self, mode: str) -> None:
        """Compatibility: Emit mode changed signal."""
        self.mode_changed.emit(mode)
    
    def reset_all(self) -> None:
        """Compatibility: Refresh schedules."""
        self.refresh()
    
    def clear_all(self) -> None:
        """Compatibility: No assignments to clear in hub."""
        pass
