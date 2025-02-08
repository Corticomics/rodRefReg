from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QTreeWidget, QTreeWidgetItem, QTextBrowser, 
    QPushButton, QSplitter, QLabel, QScrollArea, QListWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from utils.help_content_manager import HelpContentManager

class HelpTab(QWidget):
    help_topic_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.help_manager = HelpContentManager()
        self.init_ui()
        self.load_help_content()

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
        right_layout.insertWidget(0, self.breadcrumb)
        
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
        
        # Quick links bar
        quick_links = QHBoxLayout()
        quick_link_style = """
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #dadce0;
                border-radius: 4px;
                padding: 8px 16px;
                color: #1a73e8;
            }
            QPushButton:hover {
                background-color: #e8f0fe;
            }
        """
        for text in ["Getting Started", "Troubleshooting", "FAQ"]:
            btn = QPushButton(text)
            btn.setStyleSheet(quick_link_style)
            btn.clicked.connect(lambda checked, t=text: self.show_quick_topic(t))
            quick_links.addWidget(btn)
        right_layout.addLayout(quick_links)
        
        # Add related topics section
        self.related_topics = QWidget()
        related_layout = QVBoxLayout(self.related_topics)
        related_label = QLabel("Related Topics")
        related_label.setStyleSheet("font-weight: bold; color: #202124;")
        related_layout.addWidget(related_label)
        self.related_list = QListWidget()
        self.related_list.itemClicked.connect(self.on_related_topic_clicked)
        related_layout.addWidget(self.related_list)
        right_layout.addWidget(self.related_topics)
        
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
            ],
            "Troubleshooting": [
                "Common Issues",
                "Error Messages",
                "Emergency Procedures"
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

    def filter_topics(self, search_text):
        """Filter help topics based on search text"""
        for i in range(self.topic_tree.topLevelItemCount()):
            category_item = self.topic_tree.topLevelItem(i)
            category_visible = False
            
            for j in range(category_item.childCount()):
                topic_item = category_item.child(j)
                topic_text = topic_item.text(0).lower()
                matches = search_text.lower() in topic_text
                topic_item.setHidden(not matches)
                category_visible = category_visible or matches
            
            category_item.setHidden(not category_visible)

    def on_topic_selected(self, item, column):
        """Handle topic selection"""
        topic = item.text(0)
        content = self.help_manager.get_content(topic)
        self.content_browser.setHtml(content)
        self.help_topic_selected.emit(topic)

    def show_quick_topic(self, topic):
        """Show content for quick link topics"""
        content = self.help_manager.get_content(topic)
        self.content_browser.setHtml(content)

    def on_related_topic_clicked(self, item):
        """Handle related topic selection"""
        topic = item.text(0)
        content = self.help_manager.get_content(topic)
        self.content_browser.setHtml(content)
        self.help_topic_selected.emit(topic) 