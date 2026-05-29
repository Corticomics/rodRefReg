"""
Simple Splash Screen for App Startup

Design Principles:
- Centered window (not fullscreen) for reliability
- Progressive loading with status updates
- Clean, professional design matching app theme
- Non-blocking background initialization

References:
- Qt SplashScreen: https://doc.qt.io/qt-5/qsplashscreen.html
- Threading Best Practices: https://doc.qt.io/qt-5/thread-basics.html
"""

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QLinearGradient, QPainter
from PyQt5.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
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
    finished = pyqtSignal(object)  # Returns initialized components
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

            from gpio.gpio_handler import RelayHandler
            from models.relay_unit_manager import RelayUnitManager

            relay_unit_manager = RelayUnitManager(app_settings)
            app_settings['relay_unit_manager'] = relay_unit_manager

            self._components['relay_handler'] = RelayHandler(
                relay_unit_manager, app_settings['num_hats']
            )
            self.progress.emit(65, "Relay system ready")

            # Step 5: Controllers (80%)
            self.progress.emit(70, "Loading controllers...")
            from controllers.projects_controller import ProjectsController
            from controllers.pump_controller import PumpController

            controller = ProjectsController(self._components['database_handler'])
            pump_controller = PumpController(
                self._components['relay_handler'], self._components['database_handler']
            )
            controller.pump_controller = pump_controller
            app_settings['pump_controller'] = pump_controller

            self._components['controller'] = controller
            self.progress.emit(80, "Controllers initialized")

            # Step 6: Notifications (90%)
            self.progress.emit(85, "Setting up notifications...")
            from notifications.notifications import NotificationHandler

            self._components['notification_handler'] = NotificationHandler(
                app_settings.get('slack_token'), app_settings.get('channel_id')
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
    Simple centered splash screen with gradient background.

    Design:
    - Fixed size centered window (not fullscreen)
    - Teal gradient matching app theme
    - Progress bar and status text
    - Automatically closes when initialization completes
    """

    initialization_complete = pyqtSignal(object)  # Emits initialized components

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # Fixed size, centered on screen
        self.setFixedSize(450, 300)
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
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        # App icon
        self.logo_label = QLabel("💧")
        self.logo_label.setAlignment(Qt.AlignCenter)
        logo_font = QFont()
        logo_font.setPointSize(48)
        self.logo_label.setFont(logo_font)

        # App name
        self.title_label = QLabel("Rodent Refreshment Regulator")
        self.title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("IBM Plex Sans", 18, QFont.Bold)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: white;")

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(350)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 0.3);
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
        status_font = QFont("IBM Plex Sans", 11)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet("color: rgba(255, 255, 255, 0.8);")

        # Add widgets
        layout.addStretch()
        layout.addWidget(self.logo_label)
        layout.addWidget(self.title_label)
        layout.addSpacing(24)
        layout.addWidget(self.progress_bar, alignment=Qt.AlignCenter)
        layout.addWidget(self.status_label)
        layout.addStretch()

        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        """Paint gradient background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Rounded rectangle with teal gradient
        from PyQt5.QtGui import QPainterPath

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 16, 16)

        # Teal gradient matching app theme
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor("#0D9488"))  # Teal 600
        gradient.setColorAt(1.0, QColor("#0F766E"))  # Teal 700

        painter.fillPath(path, gradient)

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
        QTimer.singleShot(300, lambda: self._complete(components))

    def _on_error(self, error_message: str):
        """Handle initialization error."""
        self.status_label.setText("Error during startup")
        self.status_label.setStyleSheet("color: #FCA5A5;")
        print(f"[SPLASH ERROR] {error_message}")
        # Still emit with empty dict to allow fallback
        QTimer.singleShot(2000, lambda: self.initialization_complete.emit({}))

    def _complete(self, components: dict):
        """Complete initialization and close splash."""
        self.initialization_complete.emit(components)
        self.close()
