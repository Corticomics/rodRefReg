from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QTreeWidget, QTreeWidgetItem, QTextBrowser, 
    QSplitter, QLabel
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QTextCharFormat, QColor
from utils.help_content_manager import HelpContentManager

class HelpTab(QWidget):
    help_topic_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.help_manager = HelpContentManager()
        self.current_path = []
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        self.init_ui()
        self.load_help_content()
        self.setup_keyboard_navigation()

    def setup_keyboard_navigation(self):
        """Setup keyboard shortcuts for navigation"""
        self.topic_tree.setFocusPolicy(Qt.StrongFocus)
        self.search_bar.setFocusPolicy(Qt.StrongFocus)
        self.content_browser.setFocusPolicy(Qt.StrongFocus)
        
        # Add keyboard shortcuts
        self.search_bar.returnPressed.connect(self.focus_topic_tree)
        self.topic_tree.itemExpanded.connect(lambda item: self.update_breadcrumb())
        self.topic_tree.itemCollapsed.connect(lambda item: self.update_breadcrumb())

    def update_breadcrumb(self):
        """Update breadcrumb navigation"""
        if not self.current_path:
            self.breadcrumb.setText("Home")
            return
            
        path_text = " > ".join(self.current_path)
        self.breadcrumb.setText(path_text)
        self.breadcrumb.setToolTip(path_text)

    def perform_search(self):
        """Perform search with highlighting"""
        search_text = self.search_bar.text().lower()
        if not search_text:
            self.filter_topics("")
            self.content_browser.clear()
            return

        # Highlight matches in content
        if hasattr(self, 'current_content'):
            format = QTextCharFormat()
            format.setBackground(QColor("#fff2cc"))
            
            cursor = self.content_browser.textCursor()
            cursor.beginEditBlock()
            
            # Reset format
            cursor.select(cursor.Document)
            cursor.setCharFormat(QTextCharFormat())
            
            # Apply new highlighting
            while cursor.movePosition(cursor.NextWord, cursor.KeepAnchor):
                if cursor.selectedText().lower() == search_text:
                    cursor.mergeCharFormat(format)
                cursor.movePosition(cursor.NextWord)
            
            cursor.endEditBlock()

        self.filter_topics(search_text)

    def on_topic_selected(self, item, column):
        """Handle topic selection with path tracking"""
        topic = item.text(0)
        
        # Update path
        self.current_path = []
        current = item
        while current is not None:
            self.current_path.insert(0, current.text(0))
            current = current.parent()
            
        self.update_breadcrumb()
        
        # Get and display content
        content = self.help_manager.get_content(topic)
        self.current_content = content
        self.content_browser.setHtml(content)
        
        self.help_topic_selected.emit(topic)

    def filter_topics(self, search_text):
        """Filter topics with improved visibility handling"""
        if not search_text:
            for i in range(self.topic_tree.topLevelItemCount()):
                self.set_tree_item_visible(self.topic_tree.topLevelItem(i), True)
            return

        for i in range(self.topic_tree.topLevelItemCount()):
            category_item = self.topic_tree.topLevelItem(i)
            self.filter_tree_item(category_item, search_text.lower())

    def filter_tree_item(self, item, search_text):
        """Recursively filter tree items"""
        visible = False
        
        # Check this item
        if search_text in item.text(0).lower():
            visible = True
        
        # Check children
        for i in range(item.childCount()):
            child_visible = self.filter_tree_item(item.child(i), search_text)
            visible = visible or child_visible
            
        self.set_tree_item_visible(item, visible)
        return visible

    def set_tree_item_visible(self, item, visible):
        """Set item visibility with proper parent handling"""
        item.setHidden(not visible)
        if visible:
            parent = item.parent()
            while parent is not None:
                parent.setHidden(False)
                parent = parent.parent()

    def init_ui(self):
        """Initialize the UI components"""
        main_layout = QHBoxLayout(self)
        
        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Navigation and Search
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Search bar with icon
        search_container = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search help topics...")
        self.search_bar.textChanged.connect(self.filter_topics)
        self.search_bar.setStyleSheet("""
            QLineEdit {
                border: 1px solid #dadce0;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #1a73e8;
            }
        """)
        search_container.addWidget(self.search_bar)
        left_layout.addLayout(search_container)
        
        # Topic tree
        self.topic_tree = QTreeWidget()
        self.topic_tree.setHeaderLabel("Help Topics")
        self.topic_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #e0e4e8;
                border-radius: 4px;
            }
            QTreeWidget::item {
                padding: 8px;
            }
            QTreeWidget::item:selected {
                background-color: #e8f0fe;
                color: #1a73e8;
            }
        """)
        self.topic_tree.itemClicked.connect(self.on_topic_selected)
        left_layout.addWidget(self.topic_tree)
        
        # Right side - Content display
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Add breadcrumb navigation
        self.breadcrumb = QLabel()
        self.breadcrumb.setStyleSheet("""
            QLabel {
                color: #5f6368;
                padding: 8px;
                background: #f8f9fa;
                border-radius: 4px;
                margin-bottom: 8px;
            }
        """)
        right_layout.addWidget(self.breadcrumb)
        
        # Content browser
        self.content_browser = QTextBrowser()
        self.content_browser.setOpenExternalLinks(True)
        self.content_browser.setStyleSheet("""
            QTextBrowser {
                border: 1px solid #e0e4e8;
                border-radius: 4px;
                background-color: white;
            }
        """)
        right_layout.addWidget(self.content_browser)
        
        # Add widgets to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)

    def load_help_content(self):
        """Load the help content structure into the topic tree"""
        self.topic_tree.clear()
        
        # Define the help structure
        help_structure = {
            "Getting Started": [
                "System Overview",
                "First Time Setup",
                "Basic Operations"
            ],
            "Animal Management": [
                "Adding Animals",
                "Health Monitoring",
                "Data Collection"
            ],
            "Water Delivery": [
                "Creating Schedules",
                "Volume Control",
                "Safety Features"
            ],
            "System Settings": [
                "Hardware Setup",
                "User Management",
                "Notifications"
            ]
        }
        
        # Populate the topic tree
        for category, topics in help_structure.items():
            category_item = QTreeWidgetItem([category])
            self.topic_tree.addTopLevelItem(category_item)
            for topic in topics:
                topic_item = QTreeWidgetItem([topic])
                category_item.addChild(topic_item)
        
        self.topic_tree.expandAll()

    def focus_topic_tree(self):
        """Move focus to the topic tree when enter is pressed in search bar"""
        self.topic_tree.setFocus()
        if self.topic_tree.topLevelItemCount() > 0:
            first_item = self.topic_tree.topLevelItem(0)
            self.topic_tree.setCurrentItem(first_item)

    def keyPressEvent(self, event):
        """Handle keyboard navigation"""
        if event.key() == Qt.Key_F3:
            self.search_bar.setFocus()
        elif event.key() == Qt.Key_Escape:
            if self.search_bar.hasFocus():
                self.search_bar.clear()
            else:
                self.search_bar.setFocus()
        super().keyPressEvent(event)

    def showEvent(self, event):
        """Set initial focus to search bar when tab is shown"""
        super().showEvent(event)
        self.search_bar.setFocus() 