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
        self.sensor_health = "Unknown"
        
        self._init_ui()
        self._apply_material_style()
    
    def _init_ui(self):
        """Initialize card UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Header row: Animal info + Health indicator
        header_layout = QHBoxLayout()
        
        # Animal info
        self.animal_label = QLabel(f"Animal {self.animal_id}")
        self.animal_label.setStyleSheet("font-size: 13pt; font-weight: bold; color: #333;")
        header_layout.addWidget(self.animal_label)
        
        header_layout.addStretch()
        
        # Cage badge
        self.cage_badge = QLabel(f"Cage {self.cage_id}")
        self.cage_badge.setStyleSheet(
            "background-color: #2196F3; color: white; "
            "padding: 5px 10px; border-radius: 10px; font-weight: bold; font-size: 10pt;"
        )
        header_layout.addWidget(self.cage_badge)
        
        layout.addLayout(header_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 10px;
                background-color: #E0E0E0;
                height: 25px;
                text-align: center;
            }
            QProgressBar::chunk {
                border-radius: 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                          stop:0 #4CAF50, stop:1 #81C784);
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Volume info row
        volume_layout = QHBoxLayout()
        
        self.volume_label = QLabel(f"0.000 / {self.target_volume_ml:.3f} mL")
        self.volume_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #555;")
        volume_layout.addWidget(self.volume_label)
        
        volume_layout.addStretch()
        
        # Status indicator
        self.status_label = QLabel("Waiting")
        self.status_label.setStyleSheet("font-size: 11pt; color: #757575;")
        volume_layout.addWidget(self.status_label)
        
        layout.addLayout(volume_layout)
        
        # Health indicators row
        health_layout = QHBoxLayout()
        
        self.sensor_indicator = QLabel("Sensor: —")
        self.sensor_indicator.setStyleSheet("font-size: 9pt; color: #999;")
        health_layout.addWidget(self.sensor_indicator)
        
        health_layout.addStretch()
        
        self.pulse_counter = QLabel("Pulses: 0")
        self.pulse_counter.setStyleSheet("font-size: 9pt; color: #999;")
        health_layout.addWidget(self.pulse_counter)
        
        layout.addLayout(health_layout)
        
        # Time remaining (optional, hidden initially)
        self.time_remaining_label = QLabel()
        self.time_remaining_label.setStyleSheet("font-size: 9pt; color: #999; font-style: italic;")
        self.time_remaining_label.setVisible(False)
        layout.addWidget(self.time_remaining_label)
    
    def _apply_material_style(self):
        """Apply Material Design elevation/shadow"""
        self.setFrameShape(QFrame.Box)
        self.setStyleSheet("""
            MaterialCard {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #E0E0E0;
            }
            MaterialCard:hover {
                border: 1px solid #BDBDBD;
            }
        """)
        
        # Drop shadow effect (via CSS - limited in PyQt)
        self.setGraphicsEffect(None)  # Would use QGraphicsDropShadowEffect in production
    
    def update_progress(self, delivered_ml, status="Delivering"):
        """Update card with new progress data"""
        self.delivered_volume_ml = delivered_ml
        self.status = status
        
        # Update progress bar
        progress_pct = min(100, int((delivered_ml / self.target_volume_ml) * 100))
        self.progress_bar.setValue(progress_pct)
        
        # Update volume label
        self.volume_label.setText(f"{delivered_ml:.3f} / {self.target_volume_ml:.3f} mL")
        
        # Update status with emoji
        status_emoji = {
            "Waiting": "⏸",
            "Delivering": "▶️",
            "Paused": "⏸",
            "Complete": "✅",
            "Failed": "❌"
        }
        emoji = status_emoji.get(status, "⏸")
        self.status_label.setText(f"{emoji} {status}")
        
        # Color code status
        status_colors = {
            "Waiting": "#757575",
            "Delivering": "#4CAF50",
            "Paused": "#FF9800",
            "Complete": "#4CAF50",
            "Failed": "#F44336"
        }
        color = status_colors.get(status, "#757575")
        self.status_label.setStyleSheet(f"font-size: 11pt; color: {color}; font-weight: bold;")
        
        # Change progress bar color based on status
        if status == "Complete":
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: none;
                    border-radius: 10px;
                    background-color: #E0E0E0;
                    height: 25px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    border-radius: 10px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                              stop:0 #4CAF50, stop:1 #66BB6A);
                }
            """)
        elif status == "Failed":
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: none;
                    border-radius: 10px;
                    background-color: #E0E0E0;
                    height: 25px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    border-radius: 10px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                              stop:0 #F44336, stop:1 #EF5350);
                }
            """)
    
    def update_sensor_health(self, health_status):
        """Update sensor health indicator"""
        self.sensor_health = health_status
        
        health_emoji = {
            "OK": "🟢",
            "Warning": "🟡",
            "Error": "🔴",
            "Unknown": "⚪"
        }
        emoji = health_emoji.get(health_status, "⚪")
        
        health_colors = {
            "OK": "#4CAF50",
            "Warning": "#FF9800",
            "Error": "#F44336",
            "Unknown": "#999"
        }
        color = health_colors.get(health_status, "#999")
        
        self.sensor_indicator.setText(f"{emoji} Sensor: {health_status}")
        self.sensor_indicator.setStyleSheet(f"font-size: 9pt; color: {color}; font-weight: bold;")
    
    def update_pulse_count(self, pulse_count):
        """Update pulse counter"""
        self.pulse_counter.setText(f"Pulses: {pulse_count}")
    
    def set_time_remaining(self, seconds):
        """Display estimated time remaining"""
        if seconds > 0:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            self.time_remaining_label.setText(f"⏱ Est. {minutes}:{secs:02d} remaining")
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
        
        # Header with schedule info
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #f5f5f5; border-radius: 5px; padding: 10px;")
        header_layout = QHBoxLayout(header_frame)
        
        self.schedule_title = QLabel()
        self.schedule_title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #333;")
        header_layout.addWidget(self.schedule_title)
        
        header_layout.addStretch()
        
        self.elapsed_time_label = QLabel("Elapsed: 0:00")
        self.elapsed_time_label.setStyleSheet("font-size: 11pt; color: #666;")
        header_layout.addWidget(self.elapsed_time_label)
        
        layout.addWidget(header_frame)
        
        # Cards container (scrollable)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent;")
        
        self.cards_container = QWidget()
        self.cards_layout = QGridLayout(self.cards_container)
        self.cards_layout.setSpacing(15)
        
        scroll_area.setWidget(self.cards_container)
        layout.addWidget(scroll_area)
        
        # Timer will be created when schedule starts (avoid cross-thread issues)
        self.elapsed_timer = None
    
    def start_schedule(self, schedule_name, animals_data):
        """
        Initialize tracker for new schedule.
        
        Args:
            schedule_name: Name of the schedule
            animals_data: Dict {animal_id: {'cage_id': int, 'target_volume': float}}
        """
        self.schedule_name = schedule_name
        self.schedule_start_time = datetime.now()
        
        self.schedule_title.setText(f"📊 Running: {schedule_name}")
        
        # Clear existing cards
        self.clear_cards()
        
        # Create cards for each animal
        row = 0
        col = 0
        max_cols = 3  # 3 cards per row
        
        for animal_id, data in animals_data.items():
            card = MaterialCard(
                animal_id=animal_id,
                cage_id=data['cage_id'],
                target_volume_ml=data['target_volume'],
                parent=self
            )
            
            self.cards[animal_id] = card
            self.cards_layout.addWidget(card, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # CRITICAL: Create timer fresh each time (avoid cross-thread killTimer issues)
        if self.elapsed_timer:
            self.elapsed_timer.stop()
            self.elapsed_timer.deleteLater()
        
        self.elapsed_timer = QTimer(self)  # Explicit parent = this widget (GUI thread)
        self.elapsed_timer.timeout.connect(self._update_elapsed_time)
        self.elapsed_timer.start(1000)  # Update every second
    
    def update_animal_progress(self, animal_id, delivered_ml, status="Delivering", 
                               pulse_count=0, sensor_health="Unknown"):
        """Update progress for specific animal"""
        if animal_id in self.cards:
            card = self.cards[animal_id]
            card.update_progress(delivered_ml, status)
            card.update_pulse_count(pulse_count)
            card.update_sensor_health(sensor_health)
    
    def update_all_animals_status(self, status):
        """Update status for all animals (e.g., "Paused")"""
        for card in self.cards.values():
            card.update_progress(card.delivered_volume_ml, status)
    
    def schedule_complete(self):
        """Handle schedule completion"""
        if self.elapsed_timer:
            self.elapsed_timer.stop()
        
        # Update all cards to complete
        for card in self.cards.values():
            if card.delivered_volume_ml >= card.target_volume_ml * 0.95:  # 95% threshold
                card.update_progress(card.delivered_volume_ml, "Complete")
        
        # Auto-dismiss after 10 seconds (create timer fresh to avoid cross-thread issues)
        if self.auto_dismiss_timer:
            self.auto_dismiss_timer.stop()
            self.auto_dismiss_timer.deleteLater()
        
        self.auto_dismiss_timer = QTimer(self)  # Explicit parent
        self.auto_dismiss_timer.timeout.connect(self._auto_dismiss)
        self.auto_dismiss_timer.setSingleShot(True)
        self.auto_dismiss_timer.start(10000)  # 10 seconds
    
    def _auto_dismiss(self):
        """Fade out and hide tracker"""
        # In production, would use QPropertyAnimation for fade effect
        self.hide()
    
    def clear_cards(self):
        """Remove all animal cards"""
        for card in self.cards.values():
            card.deleteLater()
        self.cards.clear()
        
        # Clear layout
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _update_elapsed_time(self):
        """Update elapsed time display"""
        if self.schedule_start_time:
            elapsed = datetime.now() - self.schedule_start_time
            elapsed_seconds = int(elapsed.total_seconds())
            minutes = elapsed_seconds // 60
            seconds = elapsed_seconds % 60
            self.elapsed_time_label.setText(f"Elapsed: {minutes}:{seconds:02d}")
    
    def stop(self):
        """Stop tracking and clean up"""
        if self.elapsed_timer:
            self.elapsed_timer.stop()
        if self.auto_dismiss_timer:
            self.auto_dismiss_timer.stop()


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

