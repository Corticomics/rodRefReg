"""
Glassmorphism Login Overlay

Design inspired by iOS frosted glass aesthetic:
- Full-window overlay with blur effect
- Semi-transparent card with backdrop blur simulation
- Gradient background with organic shapes
- Smooth animations

References:
- Qt Graphics Effects: https://doc.qt.io/qt-5/qgraphicsblureffect.html
- Qt Opacity: https://doc.qt.io/qt-5/qgraphicsopacityeffect.html
- iOS Human Interface Guidelines: Vibrancy and blur

Technical Notes:
- Qt doesn't support true backdrop-filter blur like CSS
- We simulate glassmorphism using:
  1. Semi-transparent widget background
  2. QGraphicsBlurEffect on a background snapshot
  3. Layered painting for the frosted effect
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFrame, QGraphicsDropShadowEffect,
    QGraphicsBlurEffect, QGraphicsOpacityEffect, QMessageBox,
    QSizePolicy, QApplication
)
from PyQt5.QtCore import (
    Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, 
    QTimer, QPoint, QRect, QSize
)
from PyQt5.QtGui import (
    QFont, QColor, QPainter, QLinearGradient, QPainterPath,
    QBrush, QPen, QPixmap, QRegion, QPalette
)


class GlassCard(QFrame):
    """
    Frosted glass card component.
    
    Simulates iOS-style glassmorphism with:
    - Semi-transparent background
    - Subtle border
    - Drop shadow for elevation
    - Rounded corners
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassCard")
        self._setup_style()
    
    def _setup_style(self):
        """Apply glassmorphism styling."""
        # Drop shadow for elevation
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)
        
        # Styling via stylesheet
        self.setStyleSheet("""
            GlassCard {
                background-color: rgba(255, 255, 255, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 24px;
            }
        """)


class GlassmorphismLoginOverlay(QWidget):
    """
    Full-window glassmorphism login overlay.
    
    Features:
    - Gradient background with organic blob shapes
    - Frosted glass card containing login form
    - Animated entrance/exit
    - Enter key support for login
    
    Usage:
        overlay = GlassmorphismLoginOverlay(login_system, parent=main_window)
        overlay.login_successful.connect(on_login)
        overlay.show()
    """
    
    login_successful = pyqtSignal(dict)  # Emits user_info on successful login
    login_cancelled = pyqtSignal()
    
    def __init__(self, login_system, database_handler=None, parent=None):
        super().__init__(parent)
        self.login_system = login_system
        self.database_handler = database_handler
        self._is_visible = False
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """Initialize the overlay UI."""
        # Main layout - centers the card
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)
        
        # Glass card container
        self.card = GlassCard()
        self.card.setFixedSize(480, 520)
        
        # Card content layout
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(48, 48, 48, 48)
        card_layout.setSpacing(16)
        
        # Header
        header_label = QLabel("WELCOME BACK")
        header_label.setAlignment(Qt.AlignCenter)
        header_font = QFont("IBM Plex Sans", 24, QFont.Bold)
        header_font.setLetterSpacing(QFont.AbsoluteSpacing, 3)
        header_label.setFont(header_font)
        header_label.setStyleSheet("color: white; background: transparent;")
        
        # Subtitle
        subtitle_label = QLabel("LOG IN TO CONTINUE")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_font = QFont("IBM Plex Sans", 11)
        subtitle_font.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); background: transparent;")
        
        # Spacer
        card_layout.addWidget(header_label)
        card_layout.addWidget(subtitle_label)
        card_layout.addSpacing(32)
        
        # Username field with icon
        self.username_container = self._create_input_field("👤", "Username")
        self.username_input = self.username_container.findChild(QLineEdit)
        
        # Password field with icon
        self.password_container = self._create_input_field("🔒", "Password", is_password=True)
        self.password_input = self.password_container.findChild(QLineEdit)
        
        card_layout.addWidget(self.username_container)
        card_layout.addSpacing(12)
        card_layout.addWidget(self.password_container)
        card_layout.addSpacing(24)
        
        # Login button
        self.login_button = QPushButton("Proceed to Application →")
        self.login_button.setFixedHeight(56)
        self.login_button.setCursor(Qt.PointingHandCursor)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #1A1D1F;
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 600;
                padding: 0 24px;
            }
            QPushButton:hover {
                background-color: #2D3748;
            }
            QPushButton:pressed {
                background-color: #0F1012;
            }
        """)
        card_layout.addWidget(self.login_button)
        
        # Create new profile link
        card_layout.addSpacing(16)
        
        self.create_profile_button = QPushButton("Create New Profile")
        self.create_profile_button.setCursor(Qt.PointingHandCursor)
        self.create_profile_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgba(255, 255, 255, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                font-size: 13px;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.5);
            }
        """)
        card_layout.addWidget(self.create_profile_button)
        
        # Guest mode link
        card_layout.addSpacing(8)
        self.guest_link = QLabel("Continue as Guest")
        self.guest_link.setAlignment(Qt.AlignCenter)
        self.guest_link.setCursor(Qt.PointingHandCursor)
        self.guest_link.setStyleSheet("""
            color: rgba(255, 255, 255, 0.6);
            font-size: 12px;
            background: transparent;
        """)
        self.guest_link.mousePressEvent = self._on_guest_click
        card_layout.addWidget(self.guest_link)
        
        card_layout.addStretch()
        
        # Add card to main layout
        main_layout.addWidget(self.card)
    
    def _create_input_field(self, icon: str, placeholder: str, is_password: bool = False) -> QFrame:
        """Create a styled input field with icon."""
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
            }
        """)
        container.setFixedHeight(56)
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)
        
        # Icon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 18px; background: transparent; color: #8492A6;")
        
        # Input field
        input_field = QLineEdit()
        input_field.setPlaceholderText(placeholder)
        if is_password:
            input_field.setEchoMode(QLineEdit.Password)
        input_field.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                font-size: 14px;
                color: #1A1D1F;
                padding: 0;
            }
            QLineEdit::placeholder {
                color: #8492A6;
            }
        """)
        
        layout.addWidget(icon_label)
        layout.addWidget(input_field, 1)
        
        # Show/hide button for password
        if is_password:
            show_btn = QPushButton("SHOW")
            show_btn.setCursor(Qt.PointingHandCursor)
            show_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #8492A6;
                    font-size: 11px;
                    font-weight: 600;
                    letter-spacing: 1px;
                }
                QPushButton:hover {
                    color: #1A1D1F;
                }
            """)
            show_btn.clicked.connect(lambda: self._toggle_password_visibility(input_field, show_btn))
            layout.addWidget(show_btn)
        
        return container
    
    def _toggle_password_visibility(self, input_field: QLineEdit, button: QPushButton):
        """Toggle password visibility."""
        if input_field.echoMode() == QLineEdit.Password:
            input_field.setEchoMode(QLineEdit.Normal)
            button.setText("HIDE")
        else:
            input_field.setEchoMode(QLineEdit.Password)
            button.setText("SHOW")
    
    def _connect_signals(self):
        """Connect signals and slots."""
        self.login_button.clicked.connect(self._handle_login)
        self.create_profile_button.clicked.connect(self._handle_create_profile)
        
        # Enter key to submit
        self.username_input.returnPressed.connect(lambda: self.password_input.setFocus())
        self.password_input.returnPressed.connect(self._handle_login)
    
    def paintEvent(self, event):
        """Paint gradient background with organic shapes."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Base gradient (purple-violet like the reference)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor("#8B5CF6"))    # Violet
        gradient.setColorAt(0.3, QColor("#A78BFA"))    # Light violet
        gradient.setColorAt(0.6, QColor("#7C3AED"))    # Purple
        gradient.setColorAt(1.0, QColor("#6366F1"))    # Indigo
        
        painter.fillRect(self.rect(), gradient)
        
        # Draw organic blob shapes for depth
        self._draw_blobs(painter)
    
    def _draw_blobs(self, painter: QPainter):
        """Draw decorative blob shapes."""
        painter.setPen(Qt.NoPen)
        
        # Large blob bottom-right
        blob1 = QPainterPath()
        blob1.addEllipse(
            self.width() - 300, 
            self.height() - 400, 
            500, 500
        )
        painter.setBrush(QColor(139, 92, 246, 100))  # Semi-transparent violet
        painter.drawPath(blob1)
        
        # Medium blob top-left
        blob2 = QPainterPath()
        blob2.addEllipse(-100, -100, 350, 350)
        painter.setBrush(QColor(167, 139, 250, 80))  # Lighter
        painter.drawPath(blob2)
        
        # Small accent blob
        blob3 = QPainterPath()
        blob3.addEllipse(self.width() - 150, 100, 200, 200)
        painter.setBrush(QColor(196, 181, 253, 60))
        painter.drawPath(blob3)
    
    def _handle_login(self):
        """Process login attempt."""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            self._shake_card()
            return
        
        try:
            user_info = self.login_system.authenticate(username, password)
            if user_info and 'trainer_id' in user_info:
                print(f"Login successful: {user_info}")
                self.login_successful.emit(user_info)
                self._animate_out()
            else:
                self._shake_card()
                self.password_input.clear()
                self.password_input.setFocus()
        except Exception as e:
            print(f"Login error: {e}")
            self._shake_card()
    
    def _handle_create_profile(self):
        """Handle new profile creation."""
        from PyQt5.QtWidgets import QDialog, QFormLayout, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Create New Profile")
        dialog.setFixedWidth(350)
        dialog.setStyleSheet("""
            QDialog {
                background: white;
                border-radius: 12px;
            }
            QLabel {
                color: #1A1D1F;
            }
            QLineEdit {
                padding: 10px;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #0D9488;
            }
        """)
        
        layout = QFormLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        
        username_field = QLineEdit()
        username_field.setPlaceholderText("Choose a username")
        
        password_field = QLineEdit()
        password_field.setPlaceholderText("Create a password")
        password_field.setEchoMode(QLineEdit.Password)
        
        confirm_field = QLineEdit()
        confirm_field.setPlaceholderText("Confirm password")
        confirm_field.setEchoMode(QLineEdit.Password)
        
        layout.addRow("Username:", username_field)
        layout.addRow("Password:", password_field)
        layout.addRow("Confirm:", confirm_field)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: self._create_profile(
            dialog, username_field.text(), password_field.text(), confirm_field.text()
        ))
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        dialog.exec_()
    
    def _create_profile(self, dialog, username, password, confirm):
        """Create a new user profile."""
        if not username or not password:
            QMessageBox.warning(dialog, "Error", "Please fill in all fields.")
            return
        
        if password != confirm:
            QMessageBox.warning(dialog, "Error", "Passwords do not match.")
            return
        
        try:
            # Create the user
            success = self.login_system.create_trainer(username, password)
            if success:
                QMessageBox.information(dialog, "Success", f"Profile '{username}' created successfully!")
                dialog.accept()
                # Auto-fill username
                self.username_input.setText(username)
                self.password_input.setFocus()
            else:
                QMessageBox.warning(dialog, "Error", "Username already exists.")
        except Exception as e:
            QMessageBox.critical(dialog, "Error", f"Failed to create profile: {e}")
    
    def _on_guest_click(self, event):
        """Handle guest mode selection."""
        self.login_system.set_guest_mode()
        self.login_cancelled.emit()
        self._animate_out()
    
    def _shake_card(self):
        """Shake animation for invalid input."""
        animation = QPropertyAnimation(self.card, b"pos")
        animation.setDuration(100)
        animation.setLoopCount(3)
        
        start_pos = self.card.pos()
        animation.setKeyValueAt(0, start_pos)
        animation.setKeyValueAt(0.25, start_pos + QPoint(-10, 0))
        animation.setKeyValueAt(0.75, start_pos + QPoint(10, 0))
        animation.setKeyValueAt(1, start_pos)
        
        animation.start()
        # Store reference to prevent garbage collection
        self._shake_animation = animation
    
    def _animate_out(self):
        """Animate overlay disappearing."""
        # Simple fade - in production could use QPropertyAnimation with opacity
        self.hide()
    
    def showEvent(self, event):
        """Handle show event - resize to parent."""
        super().showEvent(event)
        if self.parent():
            self.setGeometry(self.parent().rect())
        self.username_input.setFocus()
    
    def resizeEvent(self, event):
        """Handle resize - match parent size."""
        super().resizeEvent(event)
        if self.parent():
            self.setGeometry(self.parent().rect())

