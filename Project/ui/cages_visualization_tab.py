# ui/cages_visualization_tab.py
"""
Cages Visualization Tab - Visual representation of the physical relay HAT board.

Features:
- Mirrors physical 16-relay HAT layout
- Inline cage name editing (double-click to edit)
- Auto-save on focus loss
"""

import os
from typing import Any, Dict, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class RelayTerminalWidget(QFrame):
    """
    Relay terminal with inline cage name editing.

    Interaction:
    - Single click: Select/highlight the terminal
    - Double click: Enter edit mode for cage name
    - Click elsewhere / Enter: Save changes
    - Escape: Cancel editing

    Reference: Qt QLineEdit for inline editing
    https://doc.qt.io/qt-5/qlineedit.html
    """

    clicked = pyqtSignal(int)
    # Emits (cage_id, new_name). cage_id is the stable DB identifier (1..N
    # across all HATs); relay_id alone is ambiguous because under multi-HAT
    # one-global-master semantics cage_id != relay_id for HATs > 0.
    name_changed = pyqtSignal(int, str)

    def __init__(
        self,
        relay_id: int,
        cage_data: Optional[Dict[str, Any]] = None,
        is_master: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._relay_id = relay_id
        self._cage_data = cage_data
        # cage_id: stable DB identifier. Falls back to relay_id only when
        # cage_data is missing (orphan terminal); master terminals have no
        # cage_id and never emit name_changed anyway.
        self._cage_id = cage_data.get('cage_id', relay_id) if cage_data else relay_id
        self._is_master = is_master
        self._selected = False
        self._editing = False
        self._name_label = None
        self._name_edit = None
        self._init_ui()

    def _init_ui(self) -> None:
        """Build terminal widget with editable name."""
        self.setObjectName("MasterTerminal" if self._is_master else "RelayTerminal")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)
        self.setMaximumWidth(220)  # Limit width for better proportions
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        # Relay number badge
        relay_label = QLabel(f"R{self._relay_id}")
        relay_label.setObjectName("RelayNumber")
        relay_label.setAlignment(Qt.AlignCenter)
        relay_label.setFixedWidth(32)
        layout.addWidget(relay_label)

        # Name display/edit area
        if self._is_master:
            name_label = QLabel("MASTER SOLENOID")
            name_label.setObjectName("MasterLabel")
            layout.addWidget(name_label, 1)
        else:
            cage_id = self._cage_data.get('cage_id', 0) if self._cage_data else 0
            cage_name = (
                self._cage_data.get('name', f'Cage {cage_id}')
                if self._cage_data
                else f'Cage {self._relay_id}'
            )

            # Name label (visible by default)
            self._name_label = QLabel(cage_name)
            self._name_label.setObjectName("CageNameLabel")
            if len(cage_name) > 20:
                self._name_label.setText(cage_name[:18] + "…")
                self._name_label.setToolTip(cage_name)
            layout.addWidget(self._name_label, 1)

            # Name edit (hidden by default)
            self._name_edit = QLineEdit(cage_name)
            self._name_edit.setObjectName("CageNameEdit")
            self._name_edit.setVisible(False)
            self._name_edit.returnPressed.connect(self._finish_editing)
            self._name_edit.editingFinished.connect(self._finish_editing)
            layout.addWidget(self._name_edit, 1)

        # Status dot
        status_dot = QLabel("●")
        status_dot.setObjectName("MasterStatusDot" if self._is_master else "StatusDot")
        layout.addWidget(status_dot)

    def mousePressEvent(self, event):
        """Single click to select."""
        if event.button() == Qt.LeftButton:
            self._selected = True
            self._update_selection_style()
            self.clicked.emit(self._relay_id)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Double click to edit (non-master only)."""
        if event.button() == Qt.LeftButton and not self._is_master and self._name_edit:
            self._start_editing()
        super().mouseDoubleClickEvent(event)

    def _start_editing(self) -> None:
        """Enter edit mode."""
        if self._editing or not self._name_edit:
            return

        self._editing = True

        # Get current full name from cage_data
        if self._cage_data:
            cage_id = self._cage_data.get('cage_id', 0)
            current_name = self._cage_data.get('name', f'Cage {cage_id}')
        else:
            current_name = f'Cage {self._relay_id}'

        self._name_edit.setText(current_name)
        self._name_label.setVisible(False)
        self._name_edit.setVisible(True)
        self._name_edit.setFocus()
        self._name_edit.selectAll()

    def _finish_editing(self) -> None:
        """Exit edit mode and save."""
        if not self._editing or not self._name_edit:
            return

        self._editing = False
        new_name = self._name_edit.text().strip()

        if not new_name:
            # Revert to original if empty
            cage_id = self._cage_data.get('cage_id', 0) if self._cage_data else self._relay_id
            new_name = f'Cage {cage_id}'

        # Update display
        display_name = new_name if len(new_name) <= 20 else new_name[:18] + "…"
        self._name_label.setText(display_name)
        if len(new_name) > 20:
            self._name_label.setToolTip(new_name)
        else:
            self._name_label.setToolTip("")

        self._name_edit.setVisible(False)
        self._name_label.setVisible(True)

        # Emit signal to save
        self.name_changed.emit(self._cage_id, new_name)

    def _update_selection_style(self) -> None:
        """Update visual state for selection."""
        if self._selected:
            self.setProperty("selected", True)
        else:
            self.setProperty("selected", False)
        self.style().unpolish(self)
        self.style().polish(self)

    def deselect(self) -> None:
        """Remove selection highlight."""
        self._selected = False
        self._update_selection_style()

    def keyPressEvent(self, event):
        """Handle Escape to cancel editing."""
        if event.key() == Qt.Key_Escape and self._editing:
            self._editing = False
            self._name_edit.setVisible(False)
            self._name_label.setVisible(True)
            return
        super().keyPressEvent(event)

    @property
    def relay_id(self) -> int:
        return self._relay_id


class CagesVisualizationTab(QWidget):
    """
    Tab displaying physical relay HAT board layout with inline editing.
    """

    cage_selected = pyqtSignal(int)
    cage_names_updated = pyqtSignal()  # Emitted when any cage name is changed

    def __init__(
        self, database_handler, system_controller=None, print_to_terminal=None, parent=None
    ):
        super().__init__(parent)
        self._database_handler = database_handler
        self._system_controller = system_controller
        self._print_to_terminal = print_to_terminal or (lambda x: None)

        self._num_hats = 1
        self._master_relay = 16
        if system_controller and hasattr(system_controller, 'settings'):
            self._num_hats = int(system_controller.settings.get('num_hats', 1))
            self._master_relay = int(system_controller.settings.get('global_master_relay_id', 16))

        self._relay_widgets: Dict[int, RelayTerminalWidget] = {}
        self._selected_relay: Optional[int] = None
        self._init_ui()
        self._load_cage_data()

    def _init_ui(self) -> None:
        """Build the visualization layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # ═══════════════════════════════════════════════════════════════
        # HEADER with title and info button
        # ═══════════════════════════════════════════════════════════════
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Relay Board Layout")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #1F2937;")
        header_layout.addWidget(title, alignment=Qt.AlignVCenter)

        # Info button (uses global QSS via InfoButton objectName)
        from PyQt5.QtWidgets import QPushButton

        info_btn = QPushButton("?")
        info_btn.setObjectName("InfoButton")
        info_btn.setCursor(Qt.PointingHandCursor)
        info_btn.clicked.connect(self._show_relay_info)
        header_layout.addWidget(info_btn, alignment=Qt.AlignVCenter)

        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # ═══════════════════════════════════════════════════════════════
        # BOARD VISUALIZATION — one tab per HAT
        # ═══════════════════════════════════════════════════════════════
        board_frame = QFrame()
        board_frame.setObjectName("Card")
        board_frame.setProperty("card", True)
        board_frame.setStyleSheet("""
            QFrame#Card {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)

        board_layout = QVBoxLayout(board_frame)
        board_layout.setContentsMargins(16, 12, 16, 16)
        board_layout.setSpacing(8)

        subtitle = QLabel("Double-click a cage to rename it")
        subtitle.setStyleSheet(
            "color: #6B7280; font-size: 13px; font-style: italic;"
            " padding: 4px 8px; background: transparent;"
        )
        subtitle.setAlignment(Qt.AlignCenter)
        board_layout.addWidget(subtitle)

        # Per-HAT containers populated by _build_hat_tab. Keyed by hat_index
        # so _load_cage_data can place widgets without walking the tab widget.
        self._hat_containers: Dict[int, Dict[str, QVBoxLayout]] = {}

        self._hat_tab_widget = QTabWidget()
        self._hat_tab_widget.setObjectName("HatTabs")
        for hat_index in range(self._num_hats):
            self._hat_tab_widget.addTab(self._build_hat_tab(hat_index), f"HAT {hat_index}")
        board_layout.addWidget(self._hat_tab_widget, 1)

        main_layout.addWidget(board_frame, 1)

        # ═══════════════════════════════════════════════════════════════
        # LEGEND BAR
        # ═══════════════════════════════════════════════════════════════
        legend_layout = QHBoxLayout()
        legend_layout.setSpacing(24)

        cage_legend = QHBoxLayout()
        cage_legend.setSpacing(6)
        cage_dot = QLabel("●")
        cage_dot.setObjectName("StatusDot")
        cage_legend.addWidget(cage_dot)
        cage_legend.addWidget(QLabel("Cage valve"))
        legend_layout.addLayout(cage_legend)

        master_legend = QHBoxLayout()
        master_legend.setSpacing(6)
        master_dot = QLabel("●")
        master_dot.setObjectName("MasterStatusDot")
        master_legend.addWidget(master_dot)
        master_legend.addWidget(QLabel("Master solenoid"))
        legend_layout.addLayout(master_legend)

        legend_layout.addStretch()

        self._status_label = QLabel("")
        self._status_label.setObjectName("Caption")
        legend_layout.addWidget(self._status_label)

        main_layout.addLayout(legend_layout)

        # Click anywhere to deselect
        self.setFocusPolicy(Qt.ClickFocus)

    def _build_hat_tab(self, hat_index: int) -> QWidget:
        """Build one HAT's 3-column board (LEFT terminals, image, RIGHT).

        Stores the LEFT/RIGHT layouts in ``self._hat_containers[hat_index]``
        so ``_load_cage_data`` can populate them without traversing the tab
        widget. The center column reuses the existing physical-board image
        per HAT — every HAT has the same physical layout.
        """
        page = QWidget()
        columns = QHBoxLayout(page)
        columns.setSpacing(12)

        # LEFT column: relays (hat_index*16)+1 .. +8
        left_column = QVBoxLayout()
        left_column.setSpacing(4)
        left_column.setAlignment(Qt.AlignTop)
        left_header = QLabel("LEFT SIDE")
        left_header.setObjectName("ColumnHeader")
        left_header.setAlignment(Qt.AlignCenter)
        left_column.addWidget(left_header)
        left_container = QVBoxLayout()
        left_container.setSpacing(3)
        left_column.addLayout(left_container)
        left_column.addStretch()
        columns.addLayout(left_column, 1)

        # CENTER: physical board image (reused per HAT — they're identical)
        center_column = QVBoxLayout()
        center_column.setAlignment(Qt.AlignCenter)
        image_path = os.path.join(
            os.path.dirname(__file__),
            'src',
            'relay architecture with lab els.png',
        )
        if os.path.exists(image_path):
            board_image = QLabel()
            pixmap = QPixmap(image_path)
            scaled = pixmap.scaled(
                500,
                650,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            board_image.setPixmap(scaled)
            board_image.setAlignment(Qt.AlignCenter)
            board_image.setToolTip(
                f"Physical relay HAT board layout — HAT {hat_index}\n"
                "Match cage wires to the corresponding terminal labels"
            )
            center_column.addWidget(board_image)
        else:
            placeholder = QLabel("[Board Diagram Not Found]")
            placeholder.setStyleSheet("color: #9CA3AF; font-size: 14px;")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setMinimumSize(400, 500)
            center_column.addWidget(placeholder)
        columns.addLayout(center_column, 2)

        # RIGHT column: relays (hat_index+1)*16 down to (hat_index*16)+9
        right_column = QVBoxLayout()
        right_column.setSpacing(4)
        right_column.setAlignment(Qt.AlignTop)
        right_header = QLabel("RIGHT SIDE")
        right_header.setObjectName("ColumnHeader")
        right_header.setAlignment(Qt.AlignCenter)
        right_column.addWidget(right_header)
        right_container = QVBoxLayout()
        right_container.setSpacing(3)
        right_column.addLayout(right_container)
        right_column.addStretch()
        columns.addLayout(right_column, 1)

        self._hat_containers[hat_index] = {
            'left': left_container,
            'right': right_container,
        }
        return page

    def mousePressEvent(self, event):
        """Click on empty area deselects and finishes any editing."""
        self._deselect_all()
        super().mousePressEvent(event)

    def _deselect_all(self) -> None:
        """Deselect all terminal widgets."""
        for widget in self._relay_widgets.values():
            widget.deselect()
        self._selected_relay = None

    def _show_relay_info(self) -> None:
        """Show relay-to-cage relationship info dialog."""
        from PyQt5.QtWidgets import QMessageBox

        QMessageBox.information(
            self,
            "Relay-to-Cage Relationship",
            "Each tab represents one physical relay HAT.\n\n"
            "On every HAT:\n"
            "• Left side terminals: HAT-local relays 1-8\n"
            "• Right side terminals: HAT-local relays 9-16\n\n"
            "The master solenoid is global (default: relay 16 on HAT 0).\n"
            "All other relays across all HATs are cage valves.\n\n"
            "Wire each cage's valve to its corresponding terminal.\n"
            "Double-click a cage name to rename it.",
        )

    def _load_cage_data(self) -> None:
        """Load cage data and populate per-HAT terminals.

        Iterates every HAT tab and fills its LEFT (relays 1-8 of the HAT)
        and RIGHT (relays 16-9 of the HAT) columns. The global master
        relay (default 16) is shown only on the HAT it belongs to;
        cages on every other HAT are rendered as regular terminals.
        """
        # Clear all per-HAT containers + the central widget map.
        for containers in self._hat_containers.values():
            self._clear_layout(containers['left'])
            self._clear_layout(containers['right'])
        self._relay_widgets.clear()

        try:
            cages = self._database_handler.get_cages_for_dropdown(
                num_hats=self._num_hats,
                master_relay=self._master_relay,
            )

            cage_by_relay: Dict[int, Dict] = {}
            for cage in cages:
                relay_id = cage.get('relay_id', cage.get('cage_id'))
                cage_by_relay[relay_id] = cage

            for hat_index in range(self._num_hats):
                containers = self._hat_containers.get(hat_index)
                if not containers:
                    continue
                base = hat_index * 16

                # LEFT: HAT-local relays 1..8 -> absolute (base+1)..(base+8)
                for offset in range(1, 9):
                    relay_id = base + offset
                    is_master = relay_id == self._master_relay
                    widget = RelayTerminalWidget(
                        relay_id=relay_id,
                        cage_data=cage_by_relay.get(relay_id) if not is_master else None,
                        is_master=is_master,
                    )
                    widget.clicked.connect(self._on_relay_clicked)
                    widget.name_changed.connect(self._on_name_changed)
                    containers['left'].addWidget(widget)
                    self._relay_widgets[relay_id] = widget

                # RIGHT: HAT-local relays 16..9 -> absolute (base+16)..(base+9)
                for offset in range(16, 8, -1):
                    relay_id = base + offset
                    is_master = relay_id == self._master_relay
                    widget = RelayTerminalWidget(
                        relay_id=relay_id,
                        cage_data=cage_by_relay.get(relay_id) if not is_master else None,
                        is_master=is_master,
                    )
                    widget.clicked.connect(self._on_relay_clicked)
                    widget.name_changed.connect(self._on_name_changed)
                    containers['right'].addWidget(widget)
                    self._relay_widgets[relay_id] = widget

            self._status_label.setText(f"{len(cages)} cages · {self._num_hats} HAT")

        except Exception as e:
            self._status_label.setText(f"Error: {str(e)}")
            self._print_to_terminal(f"[CagesTab] Error: {e}")

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        """Remove all widgets from layout."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_relay_clicked(self, relay_id: int) -> None:
        """Handle terminal selection."""
        # Deselect others
        for rid, widget in self._relay_widgets.items():
            if rid != relay_id:
                widget.deselect()

        self._selected_relay = relay_id
        self.cage_selected.emit(relay_id)

    def _on_name_changed(self, cage_id: int, new_name: str) -> None:
        """Save cage name to database and notify other components.

        Uses the cage_id supplied by the widget (not the relay_id). Under
        the one-global-master multi-HAT semantics, cage_id != relay_id for
        cages on HATs > 0 — a 1:1 fallback would silently corrupt those
        rename writes.
        """
        try:
            # Resolve the relay_id from the relay_widgets map so set_cage_name
            # still receives both ids (the DB schema indexes by both).
            relay_id = next(
                (rid for rid, w in self._relay_widgets.items() if w._cage_id == cage_id),
                cage_id,
            )
            self._database_handler.set_cage_name(
                cage_id=cage_id,
                relay_id=relay_id,
                name=new_name,
            )
            self._print_to_terminal(
                f"[CagesTab] Saved: Cage {cage_id} (relay {relay_id}) → '{new_name}'"
            )
            self.cage_names_updated.emit()
        except Exception as e:
            self._print_to_terminal(f"[CagesTab] Save error: {e}")

    def refresh(self) -> None:
        """Re-read settings, then reload cage data.

        Pulls ``num_hats`` and ``global_master_relay_id`` fresh from
        ``system_controller.settings`` so that "Change Relay Hats"
        actually reflects in the status label and the cages query.
        Without this re-read the cached values from ``__init__`` would
        keep the old count visible until the next app launch.
        """
        if self._system_controller and hasattr(self._system_controller, 'settings'):
            settings = self._system_controller.settings
            self._num_hats = int(settings.get('num_hats', self._num_hats))
            self._master_relay = int(settings.get('global_master_relay_id', self._master_relay))
        self._rebuild_hat_tabs_if_count_changed()
        self._load_cage_data()

    def _rebuild_hat_tabs_if_count_changed(self) -> None:
        """Add or remove HAT tabs so the count matches ``self._num_hats``.

        Preserves the operator's currently-selected tab when possible.
        If the active tab no longer exists (e.g. went 2 -> 1 while on
        HAT 1), falls back to HAT 0.
        """
        current = self._hat_tab_widget.count()
        target = self._num_hats
        if current == target:
            return

        previously_selected = self._hat_tab_widget.currentIndex()

        if target > current:
            for hat_index in range(current, target):
                self._hat_tab_widget.addTab(self._build_hat_tab(hat_index), f"HAT {hat_index}")
        else:
            for _ in range(current - target):
                removed_index = self._hat_tab_widget.count() - 1
                widget = self._hat_tab_widget.widget(removed_index)
                self._hat_tab_widget.removeTab(removed_index)
                if widget is not None:
                    widget.deleteLater()
                self._hat_containers.pop(removed_index, None)

        if previously_selected >= target:
            self._hat_tab_widget.setCurrentIndex(0)
        else:
            self._hat_tab_widget.setCurrentIndex(previously_selected)
