from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QTreeWidget, QTreeWidgetItem, QTextBrowser, 
    QPushButton, QSplitter, QLabel, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

class HelpTab(QWidget):
    help_topic_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_help_content()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        
        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Navigation and Search
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search help topics...")
        self.search_bar.textChanged.connect(self.filter_topics)
        left_layout.addWidget(self.search_bar)
        
        # Topic tree
        self.topic_tree = QTreeWidget()
        self.topic_tree.setHeaderLabel("Help Topics")
        self.topic_tree.itemClicked.connect(self.on_topic_selected)
        left_layout.addWidget(self.topic_tree)
        
        # Right side - Content display
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Content browser
        self.content_browser = QTextBrowser()
        self.content_browser.setOpenExternalLinks(True)
        right_layout.addWidget(self.content_browser)
        
        # Quick links bar
        quick_links = QHBoxLayout()
        for text in ["Getting Started", "Troubleshooting", "FAQ"]:
            btn = QPushButton(text)
            btn.clicked.connect(lambda checked, t=text: self.show_quick_topic(t))
            quick_links.addWidget(btn)
        right_layout.addLayout(quick_links)
        
        # Add widgets to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)

    def load_help_content(self):
        # Define the help content structure
        help_structure = {
            "Getting Started": [
                "System Overview",
                "First Time Setup",
                "Basic Operations"
            ],
            "Features": [
                "Animal Management",
                "Schedule Creation",
                "Water Delivery",
                "Data Collection"
            ],
            "Settings": [
                "System Configuration",
                "User Profiles",
                "Notifications"
            ],
            "Troubleshooting": [
                "Common Issues",
                "Error Messages",
                "System Checks"
            ]
        }
        
        # Populate the topic tree
        self.topic_tree.clear()
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
        content = self.get_help_content(topic)
        self.content_browser.setHtml(content)
        self.help_topic_selected.emit(topic)

    def show_quick_topic(self, topic):
        """Show content for quick link topics"""
        content = self.get_help_content(topic)
        self.content_browser.setHtml(content)

    def get_help_content(self, topic):
        """Retrieve help content for the selected topic"""
        # This would typically load from a help content database or files
        # For now, we'll return some sample content
        return f"""
        <h2>{topic}</h2>
        <div class="help-content">
            <p>This is the help content for {topic}.</p>
            <ul>
                <li>Feature explanation</li>
                <li>Usage instructions</li>
                <li>Tips and best practices</li>
            </ul>
        </div>
        """ 