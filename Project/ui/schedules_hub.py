# ui/schedules_hub.py
"""
Schedules Hub - Central view for managing water delivery schedules.

Features:
- View all schedules in a grid layout (3 per row)
- Search bar with debounced filtering (prevents lag)
- Multi-select mode for bulk deletion (iPhone-style)
- Create new schedules via Wizard redirect
- Edit existing schedules using wizard UI
- Delete schedules with confirmation
- Drag schedules to Run/Stop section for execution
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

from models.Schedule import Schedule
from PyQt5.QtCore import QDateTime, QMimeData, QPoint, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QDrag, QFont, QLinearGradient, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QDateTimeEdit,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# ============================================================================
# SCHEDULE EDIT DIALOG (Wizard-style UI matching schedule_wizard.py Step 3)
# ============================================================================


class ScheduleEditDialog(QDialog):
    """
    Dialog for editing an existing schedule using wizard-style UI.
    Matches the look and feel of schedule_wizard.py Step 3.
    """

    def __init__(self, schedule: Schedule, database_handler, system_controller=None, parent=None):
        super().__init__(parent)
        self._schedule = schedule
        self._database_handler = database_handler
        self._system_controller = system_controller
        self._schedule_details = None
        self._animal_widgets = {}
        self._cage_options = []

        self.setWindowTitle(f"Edit Schedule: {schedule.name}")
        self.setMinimumSize(800, 600)
        self.setModal(True)

        self._load_schedule_details()
        self._load_cage_options()
        self._init_ui()

    def _load_schedule_details(self) -> None:
        try:
            details = self._database_handler.get_schedule_details(self._schedule.schedule_id)
            if details:
                self._schedule_details = details[0]
            else:
                self._schedule_details = {}
        except Exception as e:
            print(f"[EditDialog] Error loading details: {e}")
            self._schedule_details = {}

    def _load_cage_options(self) -> None:
        """Load cage options for dropdown."""
        try:
            num_hats = 1
            master_relay = 16
            if self._system_controller and hasattr(self._system_controller, 'settings'):
                num_hats = int(self._system_controller.settings.get('num_hats', 1))
                master_relay = int(
                    self._system_controller.settings.get('global_master_relay_id', 16)
                )

            self._cage_options = self._database_handler.get_cages_for_dropdown(
                num_hats=num_hats, master_relay=master_relay
            )
        except:
            self._cage_options = [
                {'cage_id': i, 'display_name': f'Cage {i}'} for i in range(1, 16)
            ]

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 20)

        # Wizard-style header (matches Step 3)
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 8)
        header_layout.setSpacing(12)

        icon = QLabel("⚙")
        icon.setStyleSheet("""
            font-size: 20px;
            background-color: #F0FDFA;
            border: 2px solid #0D9488;
            border-radius: 18px;
            padding: 6px;
        """)
        icon.setFixedSize(40, 40)
        icon.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(icon)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        title = QLabel("Configure Parameters")
        title.setStyleSheet("font-size: 15px; font-weight: 600; color: #1F2937;")
        text_layout.addWidget(title)
        subtitle = QLabel("Set timing and volume for each animal")
        subtitle.setStyleSheet("font-size: 11px; color: #6B7280;")
        text_layout.addWidget(subtitle)
        header_layout.addLayout(text_layout, 1)

        layout.addWidget(header)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(0, 4, 0, 0)

        # Schedule Name
        name_container = QFrame()
        name_container.setStyleSheet("""
            QFrame { background: #F8FAFB; border: 1px solid #E5E7EB; border-radius: 6px; }
        """)
        name_layout = QHBoxLayout(name_container)
        name_layout.setContentsMargins(10, 6, 10, 6)
        name_label = QLabel("Name:")
        name_label.setStyleSheet("font-weight: 500; color: #374151; font-size: 12px;")
        name_layout.addWidget(name_label)
        self._name_input = QLineEdit(self._schedule.name or "")
        self._name_input.setStyleSheet("""
            QLineEdit { border: 1px solid #D1D5DB; border-radius: 4px; padding: 5px 8px; font-size: 12px; }
            QLineEdit:focus { border-color: #0D9488; }
        """)
        name_layout.addWidget(self._name_input, 1)
        content_layout.addWidget(name_container)

        # Quick Apply section (matches Step 3)
        quick_container = QFrame()
        quick_container.setStyleSheet("""
            QFrame { background: #F8FAFB; border: 1px solid #E5E7EB; border-radius: 6px; }
        """)
        quick_layout = QVBoxLayout(quick_container)
        quick_layout.setContentsMargins(10, 6, 10, 6)
        quick_layout.setSpacing(6)

        quick_title = QLabel("Quick Apply to All Animals")
        quick_title.setStyleSheet("font-weight: 500; color: #374151; font-size: 11px;")
        quick_layout.addWidget(quick_title)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(6)

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

        quick_row.addWidget(QLabel("Start:"))
        self._global_start = QDateTimeEdit()
        self._global_start.setDateTime(QDateTime(start_dt))
        self._global_start.setCalendarPopup(True)
        self._global_start.setMinimumHeight(26)
        self._global_start.setMinimumWidth(130)
        quick_row.addWidget(self._global_start)

        quick_row.addWidget(QLabel("End:"))
        self._global_end = QDateTimeEdit()
        self._global_end.setDateTime(QDateTime(end_dt))
        self._global_end.setCalendarPopup(True)
        self._global_end.setMinimumHeight(26)
        self._global_end.setMinimumWidth(130)
        quick_row.addWidget(self._global_end)

        quick_row.addWidget(QLabel("Vol:"))
        self._global_volume = QDoubleSpinBox()
        self._global_volume.setRange(0.1, 50.0)
        self._global_volume.setValue(1.0)
        self._global_volume.setSuffix(" mL")
        self._global_volume.setMinimumHeight(26)
        quick_row.addWidget(self._global_volume)

        apply_btn = QPushButton("Apply")
        apply_btn.setMinimumHeight(26)
        apply_btn.setStyleSheet("""
            QPushButton { background-color: #E5E7EB; border: none; border-radius: 4px; padding: 4px 10px; font-weight: 500; font-size: 11px; }
            QPushButton:hover { background-color: #D1D5DB; }
        """)
        apply_btn.clicked.connect(self._apply_to_all)
        quick_row.addWidget(apply_btn)

        quick_layout.addLayout(quick_row)
        content_layout.addWidget(quick_container)

        # Animal Settings (wizard-style rows matching Step 3)
        animals_label = QLabel(
            f"Animal Settings ({len(self._schedule_details.get('animal_ids', []))} animals)"
        )
        animals_label.setStyleSheet(
            "font-weight: 500; color: #374151; font-size: 11px; margin-top: 4px;"
        )
        content_layout.addWidget(animals_label)

        desired_outputs = (
            self._schedule_details.get('desired_water_outputs', {})
            if self._schedule_details
            else {}
        )
        animal_ids = self._schedule_details.get('animal_ids', []) if self._schedule_details else []

        for idx, animal_id in enumerate(animal_ids):
            row = self._create_animal_row(animal_id, desired_outputs.get(str(animal_id), 1.0), idx)
            content_layout.addWidget(row)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        # Footer buttons
        footer = QHBoxLayout()
        footer.setSpacing(10)
        footer.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(32)
        cancel_btn.setMinimumWidth(90)
        cancel_btn.setStyleSheet("""
            QPushButton { background-color: #F3F4F6; color: #374151; border: 1px solid #D1D5DB; border-radius: 6px; padding: 6px 16px; font-weight: 500; }
            QPushButton:hover { background-color: #E5E7EB; }
        """)
        cancel_btn.clicked.connect(self.reject)
        footer.addWidget(cancel_btn)

        save_btn = QPushButton("Save Changes")
        save_btn.setMinimumHeight(32)
        save_btn.setMinimumWidth(110)
        save_btn.setStyleSheet("""
            QPushButton { background-color: #0D9488; color: white; border: none; border-radius: 6px; padding: 6px 16px; font-weight: 600; }
            QPushButton:hover { background-color: #0F766E; }
        """)
        save_btn.clicked.connect(self._save_changes)
        footer.addWidget(save_btn)

        layout.addLayout(footer)

    def _create_animal_row(self, animal_id, volume, idx) -> QFrame:
        """Create wizard-style animal config row (matches Step 3)."""
        try:
            animal = self._database_handler.get_animal_by_id(animal_id)
            animal_name = (
                f"{animal.lab_animal_id} - {animal.name}" if animal else f"Animal {animal_id}"
            )
        except:
            animal_name = f"Animal {animal_id}"

        container = QFrame()
        container.setStyleSheet("""
            QFrame { background: #F8FAFB; border: 1px solid #E5E7EB; border-radius: 6px; }
        """)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(8)

        label = QLabel(f"<b>{animal_name}</b>")
        label.setMinimumWidth(100)
        label.setStyleSheet("font-size: 11px;")
        layout.addWidget(label)

        # Cage dropdown (matches Step 3)
        layout.addWidget(QLabel("Cage:"))
        cage_combo = QComboBox()
        cage_combo.setEditable(True)
        cage_combo.setInsertPolicy(QComboBox.NoInsert)
        cage_combo.setMinimumWidth(100)
        cage_combo.setMinimumHeight(24)

        display_names = []
        for cage_opt in self._cage_options:
            cage_combo.addItem(cage_opt['display_name'], cage_opt['cage_id'])
            display_names.append(cage_opt['display_name'])

        completer = QCompleter(display_names)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        cage_combo.setCompleter(completer)

        # Set default cage
        if idx < len(self._cage_options):
            cage_combo.setCurrentIndex(idx)

        layout.addWidget(cage_combo)

        layout.addWidget(QLabel("Start:"))
        start_dt = QDateTimeEdit()
        start_dt.setDateTime(
            self._global_start.dateTime()
            if hasattr(self, '_global_start')
            else QDateTime.currentDateTime()
        )
        start_dt.setCalendarPopup(True)
        start_dt.setMinimumWidth(120)
        start_dt.setMinimumHeight(24)
        layout.addWidget(start_dt)

        layout.addWidget(QLabel("End:"))
        end_dt = QDateTimeEdit()
        end_dt.setDateTime(
            self._global_end.dateTime()
            if hasattr(self, '_global_end')
            else QDateTime.currentDateTime().addSecs(3600 * 12)
        )
        end_dt.setCalendarPopup(True)
        end_dt.setMinimumWidth(120)
        end_dt.setMinimumHeight(24)
        layout.addWidget(end_dt)

        layout.addWidget(QLabel("Vol:"))
        volume_spin = QDoubleSpinBox()
        volume_spin.setRange(0.1, 50.0)
        volume_spin.setValue(float(volume) if volume else 1.0)
        volume_spin.setSuffix(" mL")
        volume_spin.setDecimals(2)
        volume_spin.setMinimumHeight(24)
        layout.addWidget(volume_spin)

        layout.addStretch()

        self._animal_widgets[animal_id] = {
            "cage": cage_combo,
            "start": start_dt,
            "end": end_dt,
            "volume": volume_spin,
        }

        return container

    def _apply_to_all(self) -> None:
        """Apply global settings to all animals."""
        for animal_id, widgets in self._animal_widgets.items():
            widgets["start"].setDateTime(self._global_start.dateTime())
            widgets["end"].setDateTime(self._global_end.dateTime())
            widgets["volume"].setValue(self._global_volume.value())

    def _save_changes(self) -> None:
        try:
            new_name = self._name_input.text().strip()
            if not new_name:
                QMessageBox.warning(self, "Validation Error", "Schedule name cannot be empty.")
                return

            if self._animal_widgets:
                first_widgets = list(self._animal_widgets.values())[0]
                new_start = first_widgets["start"].dateTime().toPyDateTime()
                new_end = first_widgets["end"].dateTime().toPyDateTime()
            else:
                new_start = self._global_start.dateTime().toPyDateTime()
                new_end = self._global_end.dateTime().toPyDateTime()

            if new_start >= new_end:
                QMessageBox.warning(self, "Validation Error", "End time must be after start time.")
                return

            new_volumes = {}
            for animal_id, widgets in self._animal_widgets.items():
                new_volumes[str(animal_id)] = widgets["volume"].value()

            self._database_handler.update_schedule(
                schedule_id=self._schedule.schedule_id,
                name=new_name,
                start_time=new_start.isoformat(),
                end_time=new_end.isoformat(),
                desired_outputs=new_volumes,
            )

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save changes: {e}")
            import traceback

            traceback.print_exc()


# ============================================================================
# SCHEDULE CARD (Mode badge, animal count, created at timestamp)
# ============================================================================


class ScheduleCard(QFrame):
    """
    Material Design card with mode badge and multi-select support.
    Features:
    - Mode badge (Staggered/Instant)
    - Animal count in body
    - Created at timestamp in bottom right
    - Multi-select checkbox (iPhone-style)
    """

    clicked = pyqtSignal(object)
    edit_requested = pyqtSignal(object)
    delete_requested = pyqtSignal(object)
    drag_started = pyqtSignal(object)
    selection_toggled = pyqtSignal(object, bool)

    def __init__(self, schedule: Schedule, database_handler, parent=None):
        super().__init__(parent)
        self._schedule = schedule
        self._database_handler = database_handler
        self._select_mode = False
        self._selected = False
        self._init_ui()

    def _init_ui(self) -> None:
        self.setObjectName("ScheduleCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self.setFixedHeight(115)
        self.setMinimumWidth(220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 8)
        layout.setSpacing(3)

        # Row 1: Checkbox + Name + Mode Badge
        header = QHBoxLayout()
        header.setSpacing(8)

        # Selection checkbox (hidden by default)
        self._checkbox = QCheckBox()
        self._checkbox.setVisible(False)
        self._checkbox.setStyleSheet("""
            QCheckBox::indicator { width: 18px; height: 18px; }
            QCheckBox::indicator:unchecked { border: 2px solid #D1D5DB; border-radius: 4px; background: white; }
            QCheckBox::indicator:checked { border: 2px solid #0D9488; border-radius: 4px; background: #0D9488; }
        """)
        self._checkbox.stateChanged.connect(self._on_checkbox_changed)
        header.addWidget(self._checkbox)

        name = self._schedule.name or "Untitled"
        name_label = QLabel(name if len(name) <= 16 else name[:14] + "...")
        name_label.setStyleSheet(
            "font-size: 13px; font-weight: 600; color: #1F2937; background: transparent;"
        )
        if len(name) > 16:
            name_label.setToolTip(name)
        header.addWidget(name_label, 1)

        # Mode badge (Staggered/Instant)
        mode = getattr(self._schedule, 'delivery_mode', 'staggered') or 'staggered'
        mode_text = "Staggered" if mode == "staggered" else "Instant"
        badge_color = "#0D9488" if mode == "staggered" else "#6366F1"
        mode_badge = QLabel(mode_text)
        mode_badge.setStyleSheet(f"""
            background-color: {badge_color};
            color: white;
            border-radius: 10px;
            font-weight: 600;
            font-size: 9px;
            padding: 3px 8px;
        """)
        header.addWidget(mode_badge)

        layout.addLayout(header)

        # Row 2: Animal count (with proper pluralization)
        animal_count = (
            len(self._schedule.animals)
            if hasattr(self._schedule, 'animals') and self._schedule.animals
            else 0
        )
        animal_word = "animal" if animal_count == 1 else "animals"
        animals_label = QLabel(f"{animal_count} {animal_word}")
        animals_label.setStyleSheet("color: #6B7280; font-size: 11px; background: transparent;")
        layout.addWidget(animals_label)

        # Row 3: Time range (below animal count)
        time_str = self._format_time_range()
        if time_str:
            time_label = QLabel(time_str)
            time_label.setStyleSheet("color: #6B7280; font-size: 11px; background: transparent;")
            layout.addWidget(time_label)

        # Row 4: Hint + Created at
        footer = QHBoxLayout()
        footer.setSpacing(4)

        hint = QLabel("Drag · Right-click")
        hint.setStyleSheet("color: #9CA3AF; font-size: 9px; background: transparent;")
        footer.addWidget(hint)

        footer.addStretch()

        created_str = self._format_created_time()
        if created_str:
            created_label = QLabel(created_str)
            created_label.setStyleSheet(
                "color: #0D9488; font-size: 9px; font-weight: 500; background: transparent;"
            )
            footer.addWidget(created_label)

        layout.addLayout(footer)

        self._update_card_style()

    def _format_time_range(self) -> str:
        start_str = ""
        end_str = ""

        try:
            if self._schedule.start_time:
                if isinstance(self._schedule.start_time, str):
                    start = datetime.fromisoformat(self._schedule.start_time)
                else:
                    start = self._schedule.start_time
                start_str = start.strftime("%m/%d %H:%M")
        except:
            pass

        try:
            if self._schedule.end_time:
                if isinstance(self._schedule.end_time, str):
                    end = datetime.fromisoformat(self._schedule.end_time)
                else:
                    end = self._schedule.end_time
                end_str = end.strftime("%H:%M")
        except:
            pass

        if start_str and end_str:
            return f"{start_str} → {end_str}"
        elif start_str:
            return start_str
        return ""

    def _format_created_time(self) -> str:
        """Format created time as Today/Yesterday/Full date."""
        try:
            if self._schedule.start_time:
                if isinstance(self._schedule.start_time, str):
                    dt = datetime.fromisoformat(self._schedule.start_time)
                else:
                    dt = self._schedule.start_time

                now = datetime.now()
                today = now.date()
                yesterday = today - timedelta(days=1)
                created_date = dt.date()

                time_str = dt.strftime("%H:%M")

                if created_date == today:
                    return f"Today {time_str}"
                elif created_date == yesterday:
                    return f"Yesterday {time_str}"
                else:
                    return dt.strftime("%m/%d/%Y %H:%M")
        except:
            pass
        return ""

    def _update_card_style(self) -> None:
        if self._selected:
            self.setStyleSheet("""
                QFrame#ScheduleCard {
                    background-color: #F0FDFA;
                    border: 2px solid #0D9488;
                    border-radius: 10px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#ScheduleCard {
                    background-color: #FFFFFF;
                    border: 1px solid #E5E7EB;
                    border-radius: 10px;
                }
                QFrame#ScheduleCard:hover {
                    border: 1px solid #0D9488;
                    background-color: #F0FDFA;
                }
            """)

    def set_select_mode(self, enabled: bool) -> None:
        self._select_mode = enabled
        self._checkbox.setVisible(enabled)
        if not enabled:
            self._checkbox.setChecked(False)
            self._selected = False
            self._update_card_style()

    def is_selected(self) -> bool:
        return self._selected

    def _on_checkbox_changed(self, state) -> None:
        self._selected = state == Qt.Checked
        self._update_card_style()
        self.selection_toggled.emit(self._schedule, self._selected)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._select_mode:
                self._checkbox.setChecked(not self._checkbox.isChecked())
            else:
                self._drag_start_pos = event.pos()
                self.clicked.emit(self._schedule)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._select_mode:
            return
        if not (event.buttons() & Qt.LeftButton):
            return
        if not hasattr(self, '_drag_start_pos'):
            return
        if (event.pos() - self._drag_start_pos).manhattanLength() < 10:
            return
        self._start_drag()

    def _start_drag(self) -> None:
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
            'instant_deliveries': schedule_detail.get('delivery_schedule', []),
        }

        mime_data.setData('application/x-schedule', str(schedule_data).encode())

        drag = QDrag(self)
        drag.setMimeData(mime_data)

        pixmap = QPixmap(200, 50)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        gradient = QLinearGradient(0, 0, 0, 50)
        gradient.setColorAt(0, QColor("#F0FDFA"))
        gradient.setColorAt(1, QColor("#CCFBF1"))

        painter.setBrush(gradient)
        painter.setPen(QPen(QColor("#0D9488"), 2))
        painter.drawRoundedRect(1, 1, 198, 48, 8, 8)

        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.setPen(QColor("#0D9488"))
        painter.drawText(12, 24, schedule.name[:22] if schedule.name else "Schedule")

        painter.setFont(QFont("Arial", 9))
        painter.setPen(QColor("#6B7280"))
        painter.drawText(12, 40, "Drop on Run/Stop...")

        painter.end()

        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(100, 25))

        self.drag_started.emit(self._schedule)
        drag.exec_(Qt.CopyAction)

    def _show_context_menu(self, pos: QPoint) -> None:
        if self._select_mode:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: white; border: 1px solid #E5E7EB; border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 8px 16px; border-radius: 4px; }
            QMenu::item:selected { background-color: #F0FDFA; color: #0D9488; }
        """)

        edit_action = menu.addAction("Edit Schedule")
        edit_action.triggered.connect(lambda: self.edit_requested.emit(self._schedule))

        menu.addSeparator()

        delete_action = menu.addAction("Delete Schedule")
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self._schedule))

        menu.exec_(self.mapToGlobal(pos))

    @property
    def schedule(self) -> Schedule:
        return self._schedule


# ============================================================================
# SCHEDULES HUB (Main Widget with multi-select)
# ============================================================================


class SchedulesHub(QWidget):
    """
    Schedules Hub with multi-select mode for bulk deletion.
    """

    mode_changed = pyqtSignal(str)
    assignments_cleared = pyqtSignal()
    create_requested = pyqtSignal()
    schedule_selected = pyqtSignal(object)

    def __init__(
        self,
        settings,
        print_to_terminal,
        database_handler,
        login_system,
        system_controller=None,
        parent=None,
    ):
        super().__init__(parent)

        self.settings = settings
        self.print_to_terminal = print_to_terminal
        self.database_handler = database_handler
        self.login_system = login_system
        self.system_controller = system_controller

        self._schedule_cards: List[ScheduleCard] = []
        self._all_schedules: List[Schedule] = []
        self._select_mode = False
        self._selected_schedules: List[Schedule] = []

        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._perform_search)
        self._pending_search = ""

        self._init_ui()
        self.load_schedules()

        self.login_system.login_status_changed.connect(self.refresh)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header row
        header = QHBoxLayout()
        header.setSpacing(10)
        header.setContentsMargins(0, 0, 0, 0)

        title = QLabel("My Schedules")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1F2937;")
        header.addWidget(title, alignment=Qt.AlignVCenter)

        # Info button (uses global QSS via InfoButton objectName)
        info_btn = QPushButton("?")
        info_btn.setObjectName("InfoButton")
        info_btn.setCursor(Qt.PointingHandCursor)
        info_btn.clicked.connect(self._show_info)
        header.addWidget(info_btn, alignment=Qt.AlignVCenter)

        header.addStretch()

        # Select mode button
        self._select_btn = QPushButton("Select")
        self._select_btn.setMinimumHeight(28)
        self._select_btn.setCursor(Qt.PointingHandCursor)
        self._select_btn.setStyleSheet("""
            QPushButton { background-color: #F3F4F6; color: #374151; border: 1px solid #D1D5DB; border-radius: 6px; padding: 5px 12px; font-weight: 500; font-size: 11px; }
            QPushButton:hover { background-color: #E5E7EB; }
        """)
        self._select_btn.clicked.connect(self._toggle_select_mode)
        header.addWidget(self._select_btn)

        # Delete selected button (hidden by default)
        self._delete_selected_btn = QPushButton("Delete Selected")
        self._delete_selected_btn.setMinimumHeight(28)
        self._delete_selected_btn.setVisible(False)
        self._delete_selected_btn.setStyleSheet("""
            QPushButton { background-color: #DC2626; color: white; border: none; border-radius: 6px; padding: 5px 12px; font-weight: 500; font-size: 11px; }
            QPushButton:hover { background-color: #B91C1C; }
        """)
        self._delete_selected_btn.clicked.connect(self._delete_selected)
        header.addWidget(self._delete_selected_btn)

        # New Schedule Button
        new_btn = QPushButton("+ New Schedule")
        new_btn.setMinimumHeight(28)
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.setStyleSheet("""
            QPushButton { background-color: #0D9488; color: white; border: none; border-radius: 6px; padding: 5px 12px; font-weight: 600; font-size: 11px; }
            QPushButton:hover { background-color: #0F766E; }
        """)
        new_btn.clicked.connect(self._on_new_schedule)
        header.addWidget(new_btn)

        layout.addLayout(header)

        # Search bar
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search schedules...")
        self._search_input.setMinimumHeight(32)
        self._search_input.setStyleSheet("""
            QLineEdit { border: 1px solid #E5E7EB; border-radius: 6px; padding: 6px 10px; font-size: 12px; background-color: #FAFAFA; }
            QLineEdit:focus { border-color: #0D9488; background-color: #FFFFFF; }
        """)
        self._search_input.textChanged.connect(self._on_search_text_changed)
        layout.addWidget(self._search_input)

        # Schedules grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        self._grid_container = QWidget()
        self._grid_container.setStyleSheet("background: transparent;")
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._grid_layout.setSpacing(10)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)

        scroll.setWidget(self._grid_container)
        self._scroll = scroll
        layout.addWidget(self._scroll, 1)

        # Empty state
        self._empty_state = QWidget()
        self._empty_state.setStyleSheet("background: transparent;")
        empty_layout = QVBoxLayout(self._empty_state)
        empty_layout.setAlignment(Qt.AlignCenter)

        empty_title = QLabel("No Schedules")
        empty_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #6B7280;")
        empty_title.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_title)

        empty_desc = QLabel("Create your first schedule using the wizard")
        empty_desc.setStyleSheet("font-size: 12px; color: #9CA3AF;")
        empty_desc.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_desc)

        create_btn = QPushButton("Create Schedule")
        create_btn.clicked.connect(self._on_new_schedule)
        create_btn.setStyleSheet("""
            QPushButton { background-color: #0D9488; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: 600; }
            QPushButton:hover { background-color: #0F766E; }
        """)
        empty_layout.addWidget(create_btn, alignment=Qt.AlignCenter)

        self._empty_state.hide()
        # Stretch so the empty state fills the space the scroll area vacates and
        # its AlignCenter layout centres the message vertically, instead of
        # pinning it to the bottom under a still-expanded scroll area.
        layout.addWidget(self._empty_state, 1)

    def _toggle_select_mode(self) -> None:
        self._select_mode = not self._select_mode
        self._selected_schedules.clear()

        if self._select_mode:
            self._select_btn.setText("Cancel")
            self._select_btn.setStyleSheet("""
                QPushButton { background-color: #FEE2E2; color: #DC2626; border: 1px solid #FECACA; border-radius: 6px; padding: 5px 12px; font-weight: 500; font-size: 11px; }
                QPushButton:hover { background-color: #FECACA; }
            """)
            self._delete_selected_btn.setVisible(True)
            self._delete_selected_btn.setEnabled(False)
        else:
            self._select_btn.setText("Select")
            self._select_btn.setStyleSheet("""
                QPushButton { background-color: #F3F4F6; color: #374151; border: 1px solid #D1D5DB; border-radius: 6px; padding: 5px 12px; font-weight: 500; font-size: 11px; }
                QPushButton:hover { background-color: #E5E7EB; }
            """)
            self._delete_selected_btn.setVisible(False)

        for card in self._schedule_cards:
            card.set_select_mode(self._select_mode)

    def _on_selection_toggled(self, schedule: Schedule, selected: bool) -> None:
        if selected:
            if schedule not in self._selected_schedules:
                self._selected_schedules.append(schedule)
        else:
            if schedule in self._selected_schedules:
                self._selected_schedules.remove(schedule)

        count = len(self._selected_schedules)
        self._delete_selected_btn.setEnabled(count > 0)
        self._delete_selected_btn.setText(f"Delete ({count})" if count > 0 else "Delete Selected")

    def _delete_selected(self) -> None:
        if not self._selected_schedules:
            return

        count = len(self._selected_schedules)
        reply = QMessageBox.question(
            self,
            "Delete Schedules",
            f"Delete {count} selected schedule(s)?\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            for schedule in self._selected_schedules:
                try:
                    self.database_handler.remove_schedule(schedule.schedule_id)
                    self.print_to_terminal(f"[SchedulesHub] Deleted: {schedule.name}")
                except Exception as e:
                    self.print_to_terminal(f"[SchedulesHub] Error deleting {schedule.name}: {e}")

            self._toggle_select_mode()
            self.load_schedules()

    def _show_info(self) -> None:
        """Show info dialog about how to use the schedules hub."""
        QMessageBox.information(
            self,
            "How to Use Schedules",
            "Welcome to the Schedules Hub!\n\n"
            "• Drag a card to the Run/Stop section to execute it\n"
            "• Right-click a card for Edit/Delete options\n"
            "• Click 'Select' for bulk deletion mode\n"
            "• Use the search bar to filter by name\n"
            "• Click '+ New Schedule' to create via wizard",
        )

    def _on_new_schedule(self) -> None:
        if self._select_mode:
            self._toggle_select_mode()
        self.print_to_terminal("[SchedulesHub] Redirecting to Schedule Wizard...")
        self.create_requested.emit()

    def _on_search_text_changed(self, text: str) -> None:
        self._pending_search = text.strip().lower()
        self._search_timer.stop()
        self._search_timer.start(300)

    def _perform_search(self) -> None:
        self._display_schedules(self._pending_search)

    def load_schedules(self) -> None:
        current_trainer = self.login_system.get_current_trainer()
        if current_trainer:
            trainer_id = current_trainer['trainer_id']
            self._all_schedules = self.database_handler.get_schedules_by_trainer(trainer_id)
        else:
            self._all_schedules = self.database_handler.get_all_schedules()

        # Sort by most recent first (newest at top, oldest at bottom)
        self._all_schedules.sort(key=self._get_schedule_sort_key, reverse=True)

        self._display_schedules()
        self.print_to_terminal(f"[SchedulesHub] Loaded {len(self._all_schedules)} schedules")

    def _get_schedule_sort_key(self, schedule: Schedule):
        """Get sort key for schedule (start_time for ordering)."""
        try:
            if schedule.start_time:
                if isinstance(schedule.start_time, str):
                    return datetime.fromisoformat(schedule.start_time)
                return schedule.start_time
        except:
            pass
        # Return minimum datetime for schedules without valid start_time
        return datetime.min

    def _display_schedules(self, filter_text: str = "") -> None:
        self._clear_grid()

        if filter_text:
            schedules = [s for s in self._all_schedules if filter_text in (s.name or "").lower()]
        else:
            schedules = self._all_schedules

        if not schedules:
            self._empty_state.show()
            self._scroll.hide()
            return

        self._empty_state.hide()
        self._scroll.show()

        cols = 3
        for idx, schedule in enumerate(schedules):
            row = idx // cols
            col = idx % cols

            card = ScheduleCard(schedule, self.database_handler)
            card.clicked.connect(self._on_schedule_clicked)
            card.edit_requested.connect(self._on_edit_schedule)
            card.delete_requested.connect(self._on_delete_schedule)
            card.selection_toggled.connect(self._on_selection_toggled)
            card.set_select_mode(self._select_mode)

            self._schedule_cards.append(card)
            self._grid_layout.addWidget(card, row, col)

        for col in range(cols):
            self._grid_layout.setColumnStretch(col, 1)

    def _clear_grid(self) -> None:
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
        dialog = ScheduleEditDialog(
            schedule=schedule,
            database_handler=self.database_handler,
            system_controller=self.system_controller,
            parent=self,
        )

        if dialog.exec_() == QDialog.Accepted:
            self.print_to_terminal(f"[SchedulesHub] Schedule '{schedule.name}' updated")
            self.load_schedules()

    def _on_delete_schedule(self, schedule: Schedule) -> None:
        reply = QMessageBox.question(
            self,
            "Delete Schedule",
            f"Delete '{schedule.name}'?\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            try:
                self.database_handler.remove_schedule(schedule.schedule_id)
                self.print_to_terminal(f"[SchedulesHub] Deleted: {schedule.name}")
                self.load_schedules()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {e}")

    def refresh(self) -> None:
        self._search_input.clear()
        if self._select_mode:
            self._toggle_select_mode()
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
