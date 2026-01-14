"""
Schedule Progress Tracker - Material Design Cards
================================================

Real-time visual feedback for running schedules.

Best Practices:
- Material Design card components
- Real-time updates via signals
- Per-animal progress tracking
- Hardware health indicators
- Auto-dismiss on completion
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QFrame, QScrollArea, QGridLayout, QPushButton
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor, QPalette, QFont
from datetime import datetime


class MaterialCard(QFrame):
    """
    Material Design card for individual animal progress.
    
    Components:
    - Animal name/ID
    - Cage number
    - Progress bar (0-100%)
    - Volume delivered/target
    - Status indicator
    - Sensor health
    """
    
    def __init__(self, animal_id, cage_id, target_volume_ml, parent=None):
        super().__init__(parent)
        
        self.animal_id = animal_id
        self.cage_id = cage_id
        self.target_volume_ml = target_volume_ml
        self.delivered_volume_ml = 0.0
        self.status = "Waiting"
        
        # Size policy for 4-column grid layout
        from PyQt5.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setMinimumWidth(180)
        self.setMaximumWidth(280)
        
        self._init_ui()
        self._apply_material_style()
    
    def _init_ui(self):
        """Initialize card UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Header row: Animal info + Cage badge
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)
        
        # Animal info
        self.animal_label = QLabel(f"Animal {self.animal_id}")
        self.animal_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #1a1a1a;")
        header_layout.addWidget(self.animal_label)
        
        header_layout.addStretch()
        
        # Cage badge
        self.cage_badge = QLabel(f"Cage {self.cage_id}")
        self.cage_badge.setStyleSheet(
            "background-color: #0D9488; color: white; "
            "padding: 5px 10px; border-radius: 10px; font-weight: 600; font-size: 11px;"
        )
        header_layout.addWidget(self.cage_badge)
        
        layout.addLayout(header_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #E2E8F0;
                border-radius: 11px;
                background-color: #F1F5F9;
                text-align: center;
                font-size: 11px;
                font-weight: 500;
                color: #475569;
            }
            QProgressBar::chunk {
                border-radius: 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                          stop:0 #0D9488, stop:1 #14B8A6);
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Volume info row
        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(6)
        
        self.volume_label = QLabel(f"0.000 / {self.target_volume_ml:.3f} mL")
        self.volume_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #334155;")
        volume_layout.addWidget(self.volume_label)
        
        volume_layout.addStretch()
        
        # Status indicator
        self.status_label = QLabel("|| Waiting")
        self.status_label.setStyleSheet("font-size: 11px; color: #64748B;")
        volume_layout.addWidget(self.status_label)
        
        layout.addLayout(volume_layout)
    
    def _apply_material_style(self):
        """Apply Material Design card style"""
        self.setFrameShape(QFrame.StyledPanel)
        self.setLineWidth(0)
        self.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)
    
    def update_progress(self, delivered_ml, status="Delivering"):
        """Update card with new progress data"""
        self.delivered_volume_ml = delivered_ml
        self.status = status
        
        # Update progress bar
        progress_pct = min(100, int((delivered_ml / self.target_volume_ml) * 100))
        self.progress_bar.setValue(progress_pct)
        
        # Update volume label
        self.volume_label.setText(f"{delivered_ml:.3f} / {self.target_volume_ml:.3f} mL")
        
        # Update status with icon (ASCII for reliable display)
        status_icons = {
            "Waiting": "||",
            "Delivering": ">",
            "Paused": "||",
            "Complete": "[OK]",
            "Failed": "[X]"
        }
        icon = status_icons.get(status, "||")
        self.status_label.setText(f"{icon} {status}")
        
        # Color code status
        status_colors = {
            "Waiting": "#64748B",
            "Delivering": "#0D9488",
            "Paused": "#D97706",
            "Complete": "#059669",
            "Failed": "#DC2626"
        }
        color = status_colors.get(status, "#64748B")
        self.status_label.setStyleSheet(f"font-size: 11px; color: {color}; font-weight: 600;")
        
        # Change progress bar color based on status
        if status == "Complete":
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #D1FAE5;
                    border-radius: 11px;
                    background-color: #ECFDF5;
                    text-align: center;
                    font-size: 11px;
                    font-weight: 500;
                    color: #065F46;
                }
                QProgressBar::chunk {
                    border-radius: 10px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                              stop:0 #059669, stop:1 #10B981);
                }
            """)
        elif status == "Failed":
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #FECACA;
                    border-radius: 11px;
                    background-color: #FEF2F2;
                    text-align: center;
                    font-size: 11px;
                    font-weight: 500;
                    color: #991B1B;
                }
                QProgressBar::chunk {
                    border-radius: 10px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                              stop:0 #DC2626, stop:1 #EF4444);
                }
            """)
    
    def set_time_remaining(self, seconds):
        """Display estimated time remaining"""
        if seconds > 0:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            self.time_remaining_label.setText(f"Est. {minutes}:{secs:02d} remaining")
            self.time_remaining_label.setVisible(True)
        else:
            self.time_remaining_label.setVisible(False)


class ScheduleProgressTracker(QWidget):
    """
    Main progress tracker widget with Material Design cards.
    
    Features:
    - Grid layout of animal cards
    - Real-time updates from RelayWorker
    - Hardware health summary
    - Auto-dismiss on completion
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.cards = {}  # {animal_id: MaterialCard}
        self.schedule_name = ""
        self.schedule_start_time = None
        self.auto_dismiss_timer = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize tracker UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Header with schedule info - use objectName for QSS styling
        header_frame = QFrame()
        header_frame.setObjectName("TrackerHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 8, 12, 8)
        
        self.schedule_title = QLabel()
        self.schedule_title.setObjectName("ScheduleTitle")
        header_layout.addWidget(self.schedule_title)
        
        header_layout.addStretch()
        
        self.elapsed_time_label = QLabel("Elapsed: 0:00")
        self.elapsed_time_label.setObjectName("ElapsedTime")
        header_layout.addWidget(self.elapsed_time_label)
        
        layout.addWidget(header_frame)
        
        # Cards container (scrollable)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setObjectName("TrackerScrollArea")
        
        self.cards_container = QWidget()
        self.cards_layout = QGridLayout(self.cards_container)
        self.cards_layout.setSpacing(12)
        
        scroll_area.setWidget(self.cards_container)
        layout.addWidget(scroll_area)
        
        # Timer will be created when schedule starts (avoid cross-thread issues)
        self.elapsed_timer = None
    
    def show_loading(self, schedule_name: str):
        """
        Show loading state immediately before data is ready.
        
        Optimization: Called BEFORE database queries to give instant UI feedback.
        Per Qt best practices, immediate visual response < 16ms target.
        
        Args:
            schedule_name: Name of the schedule being loaded
        """
        print(f"[ProgressTracker] show_loading called: {schedule_name}")
        
        # Stop any existing timers
        self._stop_all_timers()
        
        # Clear existing cards
        self.clear_cards()
        
        # Show loading state
        self.schedule_title.setText(f"Loading: {schedule_name}...")
        self.elapsed_time_label.setText("Preparing...")
    
    def start_schedule(self, schedule_name, animals_data):
        """
        Initialize tracker for new schedule with progressive card loading.
        
        Optimization Strategy:
        1. Block layout signals during batch card creation (prevents N reflows)
        2. Create cards in batches with brief yields to event loop
        3. Start timer only after all cards are created
        
        Thread Safety: Must be called from GUI thread.
        Per Qt documentation, QTimer must be used in the thread where it was created.
        
        Args:
            schedule_name: Name of the schedule
            animals_data: Dict {animal_id: {'cage_id': int, 'target_volume': float}}
        """
        print(f"[ProgressTracker] start_schedule called: {schedule_name}")
        print(f"[ProgressTracker] animals_data: {animals_data}")
        
        # CRITICAL: Ensure widget is visible
        self.show()
        
        # Stop any existing timers FIRST
        self._stop_all_timers()
        
        self.schedule_name = schedule_name
        self.schedule_start_time = datetime.now()
        
        self.schedule_title.setText(f"Running: {schedule_name}")
        self.elapsed_time_label.setText("Elapsed: 0:00")
        
        # Clear existing cards
        self.clear_cards()
        
        # ═══════════════════════════════════════════════════════════════════
        # OPTIMIZATION: Batch card creation with signal blocking
        # Qt Best Practice: Block signals during bulk widget operations
        # Reference: https://doc.qt.io/qt-5/qobject.html#blockSignals
        # ═══════════════════════════════════════════════════════════════════
        
        # Block layout signals to prevent N layout recalculations
        self.cards_container.blockSignals(True)
        
        try:
            row = 0
            col = 0
            max_cols = 4

            for animal_id, data in animals_data.items():
                animal_id_int = int(animal_id)

                card = MaterialCard(
                    animal_id=animal_id_int,
                    cage_id=data['cage_id'],
                    target_volume_ml=data['target_volume'],
                    parent=self
                )

                self.cards[animal_id_int] = card
                self.cards_layout.addWidget(card, row, col)

                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
        finally:
            # Unblock signals and trigger single layout update
            self.cards_container.blockSignals(False)
        
        # Force single layout update after all cards added
        self.cards_container.updateGeometry()
        
        print(f"[ProgressTracker] Total cards created: {len(self.cards)}")
        
        # Create elapsed timer fresh
        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.timeout.connect(self._update_elapsed_time)
        self.elapsed_timer.start(1000)
    
    def _stop_all_timers(self):
        """
        Safely stop and clean up all timers.
        
        Qt Best Practice: Stop timers before deleteLater() to avoid
        "QTimer can only be used with threads started with QThread" errors.
        Reference: https://doc.qt.io/qt-5/qtimer.html#details
        """
        if self.elapsed_timer is not None:
            try:
                self.elapsed_timer.stop()
                self.elapsed_timer.deleteLater()
            except RuntimeError:
                pass  # Timer was already deleted
            self.elapsed_timer = None
        
        if self.auto_dismiss_timer is not None:
            try:
                self.auto_dismiss_timer.stop()
                self.auto_dismiss_timer.deleteLater()
            except RuntimeError:
                pass
            self.auto_dismiss_timer = None
    
    def update_animal_progress(self, animal_id, delivered_ml, status="Delivering", 
                               pulse_count=0, sensor_health="Unknown"):
        """
        Update progress for specific animal.
        
        Thread Safety: This method may be called from worker thread via Qt.QueuedConnection.
        Per Qt documentation, QueuedConnection marshals the call to the receiver's thread.
        
        Args:
            animal_id: Animal identifier (int)
            delivered_ml: Volume delivered so far
            status: Current delivery status
            pulse_count: Number of pulses delivered (optional, for pulse mode)
            sensor_health: Flow sensor health status (optional)
        """
        # Ensure animal_id is int for consistent lookup
        try:
            animal_id = int(animal_id)
        except (ValueError, TypeError):
            print(f"[ProgressTracker] Invalid animal_id type: {type(animal_id)}")
            return
        
        if animal_id not in self.cards:
            print(f"[ProgressTracker] No card for animal {animal_id}, available: {list(self.cards.keys())}")
            return
        
            card = self.cards[animal_id]
            card.update_progress(delivered_ml, status)
        # Note: pulse_count and sensor_health are available for future enhancements
        # but MaterialCard.update_progress() handles the core display
    
    def update_all_animals_status(self, status):
        """Update status for all animals (e.g., "Paused")"""
        for card in self.cards.values():
            card.update_progress(card.delivered_volume_ml, status)
    
    def schedule_complete(self):
        """
        Handle schedule completion.
        
        Updates card statuses and schedules auto-dismiss.
        """
        # Stop elapsed timer (but keep auto_dismiss for later)
        if self.elapsed_timer is not None:
            try:
                self.elapsed_timer.stop()
            except RuntimeError:
                pass
        
        # Update all cards to complete status
        for card in self.cards.values():
            if card.delivered_volume_ml >= card.target_volume_ml * 0.95:  # 95% threshold
                card.update_progress(card.delivered_volume_ml, "Complete")
            else:
                # Mark as incomplete if below threshold
                card.update_progress(card.delivered_volume_ml, "Incomplete")
        
        # Cancel any pending auto-dismiss timer
        if self.auto_dismiss_timer is not None:
            try:
                self.auto_dismiss_timer.stop()
                self.auto_dismiss_timer.deleteLater()
            except RuntimeError:
                pass
            self.auto_dismiss_timer = None
        
        # Schedule auto-dismiss after 10 seconds
        self.auto_dismiss_timer = QTimer(self)
        self.auto_dismiss_timer.timeout.connect(self._auto_dismiss)
        self.auto_dismiss_timer.setSingleShot(True)
        self.auto_dismiss_timer.start(10000)
    
    def _auto_dismiss(self):
        """Fade out and hide tracker"""
        # In production, would use QPropertyAnimation for fade effect
        self.hide()
    
    def clear_cards(self):
        """Remove all animal cards"""
        print(f"[ProgressTracker] clear_cards() called. Current cards: {list(self.cards.keys())}")
        print(f"[ProgressTracker] clear_cards() tracker id: {id(self)}")
        for card in self.cards.values():
            card.deleteLater()
        self.cards.clear()
        
        # Clear layout
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        print(f"[ProgressTracker] clear_cards() completed. Cards now: {list(self.cards.keys())}")
    
    def _update_elapsed_time(self):
        """Update elapsed time display"""
        if self.schedule_start_time:
            elapsed = datetime.now() - self.schedule_start_time
            elapsed_seconds = int(elapsed.total_seconds())
            minutes = elapsed_seconds // 60
            seconds = elapsed_seconds % 60
            self.elapsed_time_label.setText(f"Elapsed: {minutes}:{seconds:02d}")
    
    def stop(self):
        """
        Stop tracking and clean up all resources.
        
        Called when schedule is stopped or widget is being destroyed.
        """
        self._stop_all_timers()
        self.clear_cards()
        self.schedule_start_time = None
        self.schedule_name = ""


class ScheduleProgressWidget(QWidget):
    """
    Wrapper widget that switches between table and cards.
    
    States:
    - IDLE: Show table (existing schedule table)
    - RUNNING: Show progress cards
    - COMPLETE: Show cards for 10s, then return to table
    """
    
    def __init__(self, table_widget, parent=None):
        super().__init__(parent)
        
        self.table_widget = table_widget
        self.progress_tracker = ScheduleProgressTracker(self)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize wrapper UI"""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Add both widgets
        self.layout.addWidget(self.table_widget)
        self.layout.addWidget(self.progress_tracker)
        
        # Initially show table, hide tracker
        self.table_widget.setVisible(True)
        self.progress_tracker.setVisible(False)
    
    def switch_to_tracker(self, schedule_name, animals_data):
        """Switch from table to progress tracker"""
        self.table_widget.setVisible(False)
        self.progress_tracker.setVisible(True)
        self.progress_tracker.start_schedule(schedule_name, animals_data)
    
    def switch_to_table(self):
        """Switch from tracker back to table"""
        self.progress_tracker.stop()
        self.progress_tracker.clear_cards()
        self.progress_tracker.setVisible(False)
        self.table_widget.setVisible(True)
    
    def get_tracker(self):
        """Get reference to progress tracker for signal connections"""
        return self.progress_tracker

