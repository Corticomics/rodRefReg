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

import math
from datetime import datetime, timedelta
from typing import Any, Dict, List

from models.Schedule import Schedule
from PyQt5.QtCore import QMimeData, QPoint, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QDrag, QFont, QLinearGradient, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
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

from .components.primary_button import PrimaryButton
from .schedule_wizard import (
    Step3ConfigureParameters,
    build_schedule_from_config,
    estimate_min_window_seconds,
)

# ============================================================================
# SCHEDULE EDIT DIALOG (reuses schedule_wizard.Step3ConfigureParameters)
# ============================================================================


class ScheduleEditDialog(QDialog):
    """Modal for editing an existing schedule.

    Reuses the schedule wizard's ``Step3ConfigureParameters`` widget (the
    canonical per-animal config UI: cage dropdown, quick-apply, per-animal
    start/end/volume, plus its validation) instead of re-implementing it, and
    persists every change transactionally via
    ``DatabaseHandler.update_staggered_schedule`` — including cage reassignment
    and the ``schedule_staggered_windows`` the delivery engine reads.

    Launched as a pop-up from the Schedules Hub (it never routes the user into
    the Wizard tab). Construct on demand, ``exec_()`` modally, and react to
    ``QDialog.Accepted``.

    Instant-mode schedules are not yet editable (the instant storage path has a
    separate, tracked bug — see Project/docs/INSTANT_SCHEDULE_BUG.md); for those
    the dialog shows a short notice instead of a half-working form.
    """

    def __init__(self, schedule: Schedule, database_handler, system_controller=None, parent=None):
        super().__init__(parent)
        self._schedule = schedule
        self._database_handler = database_handler
        self._system_controller = system_controller
        self._animals: List[Dict[str, Any]] = []
        self._preset_configs: Dict[int, Dict[str, Any]] = {}
        self._step3: Step3ConfigureParameters | None = None
        # Set to a message string when the schedule can't be edited with the
        # one-row-per-animal form (e.g. >1 instant delivery per animal).
        self._blocked_reason: str | None = None

        self._delivery_mode = getattr(schedule, "delivery_mode", "staggered") or "staggered"

        self.setWindowTitle(f"Edit Schedule: {schedule.name}")
        # Open large enough to show the whole form (header, name, Quick Apply
        # and the first animal rows) without the operator having to resize.
        # Keep a smaller minimum so it still fits modest screens; the inner
        # Step-3 scroll area handles many-animal overflow.
        self.setMinimumSize(760, 540)
        self.resize(1080, 780)
        self.setModal(True)
        self.change_summary: List[str] = []

        self._load_schedule_details()
        if self._blocked_reason:
            self._init_notice_ui(self._blocked_reason)
        else:
            self._init_ui()

    @staticmethod
    def _parse_dt(value, fallback: datetime) -> datetime:
        try:
            if isinstance(value, datetime):
                return value
            if isinstance(value, str):
                return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            pass
        return fallback

    def _load_schedule_details(self) -> None:
        """Pre-fetch animals + per-animal settings into the preset configs.

        Done before ``_init_ui`` so the embedded Step 3 builds already-filled
        rows. Cage assignment is stored as ``relay_unit_id`` (== the dropdown's
        ``cage_id``) in ``schedule_animals``. Staggered volume comes from
        ``schedule_desired_outputs`` and times from the schedule bounds; instant
        delivery time + volume come from ``schedule_instant_deliveries``.
        """
        try:
            details_list = self._database_handler.get_schedule_details(self._schedule.schedule_id)
        except Exception as e:  # pragma: no cover - defensive
            print(f"[EditDialog] Error loading details: {e}")
            details_list = []
        details = details_list[0] if details_list else {}

        animal_ids = details.get("animal_ids", [])
        cage_by_animal = details.get("relay_unit_assignments", {})  # {str(animal_id): cage_id}

        instant_by_animal: Dict[int, list] = {}
        if self._delivery_mode == "instant":
            for d in details.get("delivery_schedule", []):
                instant_by_animal.setdefault(d["animal_id"], []).append(d)
            # The form is one delivery per animal (matching what the wizard
            # creates). If any animal has several deliveries we can't represent
            # it without silently dropping data — fall back to a read-only note.
            if any(len(v) > 1 for v in instant_by_animal.values()):
                self._blocked_reason = (
                    "This instant schedule has more than one delivery time for an "
                    "animal, which the editor can't show yet without losing data. "
                    "Delete and recreate it with the wizard to change it."
                )
                return

        desired = details.get("desired_water_outputs", {})  # {str(animal_id): volume}
        start_dt = self._parse_dt(self._schedule.start_time, datetime.now())
        end_dt = self._parse_dt(self._schedule.end_time, start_dt + timedelta(hours=1))
        default_volume = float(self._schedule.water_volume or 1.0)

        for animal_id in animal_ids:
            try:
                animal = self._database_handler.get_animal_by_id(animal_id)
            except Exception:  # pragma: no cover - defensive
                animal = None
            self._animals.append(
                {
                    "id": animal_id,
                    "lab_id": animal.lab_animal_id if animal else animal_id,
                    "name": animal.name if animal else f"Animal {animal_id}",
                }
            )
            if self._delivery_mode == "instant":
                d = (instant_by_animal.get(animal_id) or [None])[0]
                self._preset_configs[animal_id] = {
                    "delivery_time": self._parse_dt(
                        d["datetime"] if d else None, datetime.now() + timedelta(minutes=5)
                    ),
                    "volume": float(d["volume"]) if d else default_volume,
                    "cage_id": cage_by_animal.get(str(animal_id))
                    or (d["relay_unit_id"] if d else None),
                }
            else:
                self._preset_configs[animal_id] = {
                    "start_time": start_dt,
                    "end_time": end_dt,
                    "volume": float(desired.get(str(animal_id), default_volume)),
                    "cage_id": cage_by_animal.get(str(animal_id)),
                }

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Reuse the wizard's per-animal configuration step verbatim.
        self._step3 = Step3ConfigureParameters(
            database_handler=self._database_handler,
            system_controller=self._system_controller,
        )
        self._step3.load_for_edit(
            self._animals, self._preset_configs, self._schedule.name or "", self._delivery_mode
        )
        layout.addWidget(self._step3, 1)

        footer = QWidget()
        footer.setObjectName("DialogFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(24, 12, 24, 16)
        footer_layout.setSpacing(12)
        footer_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(36)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        footer_layout.addWidget(cancel_btn)

        save_btn = PrimaryButton("Save Changes")
        save_btn.setMinimumHeight(36)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save_changes)
        footer_layout.addWidget(save_btn)

        layout.addWidget(footer)

    def _init_notice_ui(self, message: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("This schedule can't be edited here")
        title.setObjectName("Title")
        title.setWordWrap(True)
        layout.addWidget(title)

        body = QLabel(message)
        body.setWordWrap(True)
        layout.addWidget(body)
        layout.addStretch()

        footer = QHBoxLayout()
        footer.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setMinimumHeight(36)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

    def _save_changes(self) -> None:
        # Field-level validation (name, volumes > 0, staggered end after start,
        # instant delivery time present) is shared with the wizard via Step 3.
        if not self._step3.is_valid():
            QMessageBox.warning(
                self,
                "Invalid schedule",
                "Check that the schedule has a name, every animal has a volume "
                "greater than 0 mL, and the timing for each animal is set.",
            )
            return

        # Staggered-only animal-safety check: a window must be long enough to
        # deliver every cage sequentially (one valve at a time). Instant
        # deliveries are single moments, so there's no window to validate.
        if self._delivery_mode == "staggered":
            animal_configs = self._step3.get_animal_configs()
            need = estimate_min_window_seconds(animal_configs)
            windows = [
                (cfg["end_time"] - cfg["start_time"]).total_seconds()
                for cfg in animal_configs.values()
                if cfg.get("start_time") and cfg.get("end_time")
            ]
            if windows and min(windows) < need:
                minutes = max(1, math.ceil(need / 60))
                QMessageBox.warning(
                    self,
                    "Delivery window too short",
                    f"{len(animal_configs)} cage(s) need at least about {minutes} "
                    "minute(s) to deliver safely — valves fire one at a time. "
                    "Extend the end time.",
                )
                return

        config = {
            "schedule_type": self._delivery_mode,
            "animals": [a["id"] for a in self._animals],
            "parameters": self._step3.get_parameters(),
        }
        try:
            # trainer=None: the update_* methods don't rewrite created_by /
            # is_super_user, so the original owner is preserved.
            schedule = build_schedule_from_config(
                config,
                trainer=None,
                system_controller=self._system_controller,
                schedule_id=self._schedule.schedule_id,
            )
        except ValueError as e:
            QMessageBox.warning(self, "Invalid cage assignment", str(e))
            return

        # Diff old vs new BEFORE the write so the hub can log what changed.
        self.change_summary = self._build_change_summary(schedule)

        if self._delivery_mode == "instant":
            saved = self._database_handler.update_instant_schedule(schedule)
        else:
            saved = self._database_handler.update_staggered_schedule(schedule)

        if saved:
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Error",
                "Failed to save changes to the database. The schedule was not modified.",
            )

    @staticmethod
    def _fmt_time(value) -> str:
        dt = ScheduleEditDialog._parse_dt(value, None)
        return dt.strftime("%m/%d %H:%M") if isinstance(dt, datetime) else str(value)

    @staticmethod
    def _fmt_vol(value) -> str:
        try:
            return f"{float(value):g} mL"
        except (TypeError, ValueError):
            return f"{value} mL"

    def _animal_label(self, animal_id) -> str:
        for a in self._animals:
            if a["id"] == animal_id:
                return f"{a['lab_id']} - {a['name']}"
        return f"Animal {animal_id}"

    def _build_change_summary(self, new_schedule) -> List[str]:
        """Human-readable list of what this edit changed (old → new)."""
        changes: List[str] = []

        if (self._schedule.name or "") != (new_schedule.name or ""):
            changes.append(f"Name: '{self._schedule.name}' → '{new_schedule.name}'")

        old_ids = set(self._preset_configs.keys())
        new_ids = set(new_schedule.animals)

        if self._delivery_mode == "instant":
            # Per-animal delivery time (instant has no schedule-wide window).
            new_dt = {d["animal_id"]: d["datetime"] for d in new_schedule.instant_deliveries}
            for animal_id in sorted(old_ids & new_ids):
                old_d = self._preset_configs.get(animal_id, {}).get("delivery_time")
                new_d = new_dt.get(animal_id)
                if self._parse_dt(old_d, None) != self._parse_dt(new_d, None):
                    changes.append(
                        f"{self._animal_label(animal_id)} delivery time: "
                        f"{self._fmt_time(old_d)} → {self._fmt_time(new_d)}"
                    )
        else:
            old_start = self._parse_dt(self._schedule.start_time, None)
            new_start = self._parse_dt(new_schedule.start_time, None)
            if old_start != new_start:
                changes.append(
                    f"Start time: {self._fmt_time(self._schedule.start_time)} "
                    f"→ {self._fmt_time(new_schedule.start_time)}"
                )
            old_end = self._parse_dt(self._schedule.end_time, None)
            new_end = self._parse_dt(new_schedule.end_time, None)
            if old_end != new_end:
                changes.append(
                    f"End time: {self._fmt_time(self._schedule.end_time)} "
                    f"→ {self._fmt_time(new_schedule.end_time)}"
                )

        for animal_id in sorted(new_ids - old_ids):
            changes.append(f"Animal added: {self._animal_label(animal_id)}")
        for animal_id in sorted(old_ids - new_ids):
            changes.append(f"Animal removed: {self._animal_label(animal_id)}")

        # Per-animal volume / cage changes for animals present before and after.
        # desired_water_outputs is populated for both modes by Schedule.add_animal.
        for animal_id in sorted(old_ids & new_ids):
            preset = self._preset_configs.get(animal_id, {})
            old_vol = preset.get("volume")
            new_vol = new_schedule.desired_water_outputs.get(str(animal_id))
            if old_vol is not None and new_vol is not None and float(old_vol) != float(new_vol):
                changes.append(
                    f"{self._animal_label(animal_id)} volume: "
                    f"{self._fmt_vol(old_vol)} → {self._fmt_vol(new_vol)}"
                )
            old_cage = preset.get("cage_id")
            new_cage = new_schedule.relay_unit_assignments.get(str(animal_id))
            if old_cage != new_cage:
                changes.append(f"{self._animal_label(animal_id)} cage: {old_cage} → {new_cage}")

        return changes


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

        # Edit selected button (hidden by default; shown in select mode).
        # Editing is single-schedule, so it stays disabled unless exactly one
        # schedule is selected.
        self._edit_selected_btn = QPushButton("Edit Schedule")
        self._edit_selected_btn.setMinimumHeight(28)
        self._edit_selected_btn.setVisible(False)
        self._edit_selected_btn.setCursor(Qt.PointingHandCursor)
        self._edit_selected_btn.setToolTip("Select exactly one schedule to edit")
        self._edit_selected_btn.setStyleSheet("""
            QPushButton { background-color: #0D9488; color: white; border: none; border-radius: 6px; padding: 5px 12px; font-weight: 500; font-size: 11px; }
            QPushButton:hover { background-color: #0F766E; }
            QPushButton:disabled { background-color: #CBD5E1; color: #F8FAFC; }
        """)
        self._edit_selected_btn.clicked.connect(self._edit_selected)
        header.addWidget(self._edit_selected_btn)

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
            self._edit_selected_btn.setVisible(True)
            self._edit_selected_btn.setEnabled(False)
        else:
            self._select_btn.setText("Select")
            self._select_btn.setStyleSheet("""
                QPushButton { background-color: #F3F4F6; color: #374151; border: 1px solid #D1D5DB; border-radius: 6px; padding: 5px 12px; font-weight: 500; font-size: 11px; }
                QPushButton:hover { background-color: #E5E7EB; }
            """)
            self._delete_selected_btn.setVisible(False)
            self._edit_selected_btn.setVisible(False)

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
        # Editing acts on a single schedule, so only enable for exactly one.
        self._edit_selected_btn.setEnabled(count == 1)

    def _edit_selected(self) -> None:
        if len(self._selected_schedules) != 1:
            return
        schedule = self._selected_schedules[0]
        # Leave select mode before opening the editor so the post-save reload
        # returns to the normal card view (mirrors the delete flow).
        self._toggle_select_mode()
        self._on_edit_schedule(schedule)

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
            "• Click 'Select', pick one schedule, then 'Edit Schedule'\n"
            "• Click 'Select' to choose schedules for bulk deletion\n"
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
            changes = getattr(dialog, "change_summary", []) or []
            if changes:
                self.print_to_terminal(f"[SchedulesHub] Schedule '{schedule.name}' updated:")
                for line in changes:
                    self.print_to_terminal(f"    • {line}")
            else:
                self.print_to_terminal(
                    f"[SchedulesHub] Schedule '{schedule.name}' saved (no changes)"
                )
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
