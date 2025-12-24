"""
Modern Splash Screen with Progressive Loading

Design Principles:
- Immediate visual feedback on app launch (per UX best practices)
- Progressive loading with status updates
- Non-blocking UI using QThread for initialization
- Smooth animations for professional feel

References:
- Qt Splash Screen: https://doc.qt.io/qt-5/qsplashscreen.html
- Threading Best Practices: https://doc.qt.io/qt-5/thread-basics.html
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QProgressBar, 
    QGraphicsDropShadowEffect, QApplication
)
from PyQt5.QtCore import (
    Qt, pyqtSignal, QThread, QTimer, QPropertyAnimation, 
    QEasingCurve, QSize
)
from PyQt5.QtGui import (
    QFont, QColor, QPainter, QLinearGradient, 
    QPainterPath, QBrush, QPen
)


class InitializationWorker(QThread):
    """
    Background worker for app initialization.
    
    Per Qt Threading Documentation:
    - Heavy initialization should happen off the main thread
    - Use signals to communicate progress back to UI
    - Never access UI widgets directly from worker thread
    
    Reference: https://doc.qt.io/qt-5/threads-qobject.html
    """
    
    progress = pyqtSignal(int, str)  # (percentage, status_message)
    finished = pyqtSignal(object)    # Returns initialized components
    error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self._components = {}
    
    def run(self):
        """Execute initialization steps in background thread."""
        try:
            # Step 1: Database (15%)
            self.progress.emit(5, "Connecting to database...")
            from models.database_handler import DatabaseHandler
            self._components['database_handler'] = DatabaseHandler()
            self.progress.emit(15, "Database connected")
            
            # Step 2: System Controller (30%)
            self.progress.emit(20, "Loading settings...")
            from controllers.system_controller import SystemController
            self._components['system_controller'] = SystemController(
                self._components['database_handler']
            )
            self.progress.emit(30, "Settings loaded")
            
            # Step 3: Hardware Detection (50%)
            self.progress.emit(35, "Detecting hardware...")
            try:
                self._components['system_controller'].ensure_solenoid_defaults()
            except Exception as e:
                # Non-fatal: continue with existing settings
                pass
            self.progress.emit(50, "Hardware configured")
            
            # Step 4: Relay System (65%)
            self.progress.emit(55, "Initializing relay system...")
            app_settings = self._components['system_controller'].settings
            
            from models.relay_unit_manager import RelayUnitManager
            from gpio.gpio_handler import RelayHandler
            
            relay_unit_manager = RelayUnitManager(app_settings)
            app_settings['relay_unit_manager'] = relay_unit_manager
            
            self._components['relay_handler'] = RelayHandler(
                relay_unit_manager, 
                app_settings['num_hats']
            )
            self.progress.emit(65, "Relay system ready")
            
            # Step 5: Controllers (80%)
            self.progress.emit(70, "Loading controllers...")
            from controllers.projects_controller import ProjectsController
            from controllers.pump_controller import PumpController
            
            controller = ProjectsController()
            pump_controller = PumpController(
                self._components['relay_handler'],
                self._components['database_handler']
            )
            controller.pump_controller = pump_controller
            app_settings['pump_controller'] = pump_controller
            
            self._components['controller'] = controller
            self.progress.emit(80, "Controllers initialized")
            
            # Step 6: Notifications (90%)
            self.progress.emit(85, "Setting up notifications...")
            from notifications.notifications import NotificationHandler
            
            self._components['notification_handler'] = NotificationHandler(
                app_settings.get('slack_token'),
                app_settings.get('channel_id')
            )
            self.progress.emit(90, "Notifications ready")
            
            # Step 7: Login System (95%)
            self.progress.emit(92, "Preparing login system...")
            from models.login_system import LoginSystem
            
            login_system = LoginSystem(self._components['database_handler'])
            if not login_system.is_logged_in():
                login_system.set_guest_mode()
            self._components['login_system'] = login_system
            self.progress.emit(95, "Login system ready")
            
            # Complete
            self.progress.emit(100, "Ready!")
            self.finished.emit(self._components)
            
        except Exception as e:
            import traceback
            self.error.emit(f"Initialization failed: {str(e)}\n{traceback.format_exc()}")


class SplashScreen(QWidget):
    """
    Modern splash screen with gradient background and progress tracking.
    
    Design:
    - Full-screen overlay with gradient background
    - Centered branding and progress indicator
    - Smooth fade-out transition when loading completes
    
    References:
    - Qt Frameless Window: https://doc.qt.io/qt-5/qt.html#WindowType-enum
    - Animation Framework: https://doc.qt.io/qt-5/animation-overview.html
    """
    
    initialization_complete = pyqtSignal(object)  # Emits initialized components
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint |
            Qt.SplashScreen
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        
        # Full screen on primary display
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        
        self._init_ui()
        self._worker = None
    
    def _init_ui(self):
        """Initialize the splash screen UI."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(24)
        
        # App icon/logo placeholder
        self.logo_label = QLabel("💧")
        self.logo_label.setAlignment(Qt.AlignCenter)
        logo_font = QFont()
        logo_font.setPointSize(64)
        self.logo_label.setFont(logo_font)
        
        # App name
        self.title_label = QLabel("Rodent Refreshment Regulator")
        self.title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("IBM Plex Sans", 28, QFont.Bold)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: white;")
        
        # Tagline
        self.tagline_label = QLabel("Precision Water Delivery System")
        self.tagline_label.setAlignment(Qt.AlignCenter)
        tagline_font = QFont("IBM Plex Sans", 14)
        self.tagline_label.setFont(tagline_font)
        self.tagline_label.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(400)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 0.2);
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: white;
                border-radius: 3px;
            }
        """)
        
        # Status label
        self.status_label = QLabel("Starting...")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_font = QFont("IBM Plex Sans", 11)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet("color: rgba(255, 255, 255, 0.6);")
        
        # Add widgets
        layout.addStretch(2)
        layout.addWidget(self.logo_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.tagline_label)
        layout.addSpacing(40)
        layout.addWidget(self.progress_bar, alignment=Qt.AlignCenter)
        layout.addWidget(self.status_label)
        layout.addStretch(3)
        
        # Version info at bottom
        self.version_label = QLabel("v1.0.0")
        self.version_label.setAlignment(Qt.AlignCenter)
        self.version_label.setStyleSheet("color: rgba(255, 255, 255, 0.4);")
        layout.addWidget(self.version_label)
        layout.addSpacing(20)
    
    def paintEvent(self, event):
        """Paint gradient background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create teal-to-purple gradient (matching RSO style)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor("#0D9488"))    # Teal
        gradient.setColorAt(0.5, QColor("#6366F1"))    # Indigo
        gradient.setColorAt(1.0, QColor("#8B5CF6"))    # Violet
        
        painter.fillRect(self.rect(), gradient)
    
    def start_initialization(self):
        """Start background initialization."""
        self._worker = InitializationWorker()
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()
    
    def _on_progress(self, percentage: int, message: str):
        """Update progress UI (called from main thread via signal)."""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)
    
    def _on_finished(self, components: dict):
        """Handle initialization completion."""
        # Brief delay to show 100% before closing
        QTimer.singleShot(500, lambda: self._fade_out(components))
    
    def _on_error(self, error_message: str):
        """Handle initialization error."""
        self.status_label.setText("Error during startup")
        self.status_label.setStyleSheet("color: #FCA5A5;")
        print(f"[SPLASH ERROR] {error_message}")
        # Still try to emit with whatever we have
        QTimer.singleShot(2000, lambda: self.initialization_complete.emit({}))
    
    def _fade_out(self, components: dict):
        """Fade out splash screen and emit completion signal."""
        # Simple approach: just close and emit
        self.initialization_complete.emit(components)
        self.close()


class MinimalSplash(QWidget):
    """
    Minimal splash for quick display while heavy splash loads.
    Shows immediately to provide instant feedback.
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint |
            Qt.SplashScreen
        )
        
        self.setFixedSize(300, 200)
        
        # Center on screen
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - 300) // 2
        y = (screen.height() - 200) // 2
        self.move(x, y)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        label = QLabel("Loading...")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: white; font-size: 16px;")
        layout.addWidget(label)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#0D9488"))

