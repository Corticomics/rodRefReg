"""
Modern Splash Screen with Progressive Loading

Design Principles:
- Immediate visual feedback on app launch
- Progressive loading with status updates
- Non-blocking UI using QThread for initialization
- Simple, reliable implementation

References:
- Qt Splash Screen: https://doc.qt.io/qt-5/qsplashscreen.html
- Threading Best Practices: https://doc.qt.io/qt-5/thread-basics.html
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QProgressBar, 
    QApplication, QSplashScreen
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt5.QtGui import QFont, QColor, QPainter, QLinearGradient, QPixmap


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
    finished_init = pyqtSignal(object)  # Returns initialized components
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
            except Exception:
                pass  # Non-fatal: continue with existing settings
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
            self.finished_init.emit(self._components)
            
        except Exception as e:
            import traceback
            self.error.emit(f"Initialization failed: {str(e)}\n{traceback.format_exc()}")


class SplashScreen(QWidget):
    """
    Modern splash screen with gradient background and progress tracking.
    
    Uses a simple QWidget instead of complex overlays for reliability.
    Sized to fit content, centered on screen.
    """
    
    initialization_complete = pyqtSignal(object)
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        
        # Fixed size splash - centered on screen
        self.setFixedSize(500, 350)
        self._center_on_screen()
        
        self._init_ui()
        self._worker = None
    
    def _center_on_screen(self):
        """Center the splash screen on the primary display."""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def _init_ui(self):
        """Initialize the splash screen UI."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # App icon/logo
        self.logo_label = QLabel("💧")
        self.logo_label.setAlignment(Qt.AlignCenter)
        logo_font = QFont("Segoe UI Emoji", 48)
        self.logo_label.setFont(logo_font)
        
        # App name
        self.title_label = QLabel("Rodent Refreshment Regulator")
        self.title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("IBM Plex Sans", 20, QFont.Bold)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: white;")
        
        # Tagline
        self.tagline_label = QLabel("Precision Water Delivery System")
        self.tagline_label.setAlignment(Qt.AlignCenter)
        tagline_font = QFont("IBM Plex Sans", 11)
        self.tagline_label.setFont(tagline_font)
        self.tagline_label.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(350)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 0.2);
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: white;
                border-radius: 4px;
            }
        """)
        
        # Status label
        self.status_label = QLabel("Starting...")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_font = QFont("IBM Plex Sans", 10)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet("color: rgba(255, 255, 255, 0.6);")
        
        # Add widgets
        layout.addStretch(1)
        layout.addWidget(self.logo_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.tagline_label)
        layout.addSpacing(30)
        layout.addWidget(self.progress_bar, alignment=Qt.AlignCenter)
        layout.addWidget(self.status_label)
        layout.addStretch(2)
    
    def paintEvent(self, event):
        """Paint gradient background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Teal gradient matching the app theme
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor("#0D9488"))  # Teal 600
        gradient.setColorAt(0.5, QColor("#0F766E"))  # Teal 700
        gradient.setColorAt(1.0, QColor("#115E59"))  # Teal 800
        
        # Rounded rectangle
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)
    
    def start_initialization(self):
        """Start background initialization."""
        self._worker = InitializationWorker()
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_init.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()
    
    def _on_progress(self, percentage: int, message: str):
        """Update progress UI (called from main thread via signal)."""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)
        # Process events to update UI immediately
        QApplication.processEvents()
    
    def _on_finished(self, components: dict):
        """Handle initialization completion."""
        self.progress_bar.setValue(100)
        self.status_label.setText("Ready!")
        # Brief delay to show completion
        QTimer.singleShot(300, lambda: self._complete(components))
    
    def _on_error(self, error_message: str):
        """Handle initialization error."""
        self.status_label.setText("Error during startup")
        self.status_label.setStyleSheet("color: #FCA5A5;")
        print(f"[SPLASH ERROR] {error_message}")
        # Still emit to allow fallback
        QTimer.singleShot(2000, lambda: self.initialization_complete.emit({}))
    
    def _complete(self, components: dict):
        """Complete initialization and close splash."""
        self.initialization_complete.emit(components)
        self.close()
