from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QTreeWidget, QTreeWidgetItem, QTextBrowser,
    QSplitter, QLabel, QApplication,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPalette, QTextCharFormat, QColor
from urllib.parse import unquote

from utils.help_content_manager import HelpContentManager


class HelpTab(QWidget):
    help_topic_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.help_manager = HelpContentManager()
        self.current_topic_key: str = ""

        # Debounce timer for search
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(200)
        self.search_timer.timeout.connect(self.perform_search)

        self._init_ui()
        self._build_tree()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        # ---- LEFT SIDEBAR ----------------------------------------
        left_widget = QWidget()
        left_widget.setObjectName("HelpSidebar")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(6)

        self.search_bar = QLineEdit()
        self.search_bar.setObjectName("HelpSearch")
        self.search_bar.setPlaceholderText("Search help…")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.setAccessibleName("Search help topics")
        self.search_bar.textChanged.connect(self._on_search_text_changed)
        self.search_bar.returnPressed.connect(self._search_return_pressed)

        self.result_count = QLabel()
        self.result_count.setObjectName("HelpResultCount")
        self.result_count.setVisible(False)

        self.topic_tree = QTreeWidget()
        self.topic_tree.setObjectName("HelpTree")
        self.topic_tree.setHeaderHidden(True)
        self.topic_tree.setExpandsOnDoubleClick(False)
        self.topic_tree.setAccessibleName("Help topics")
        self.topic_tree.itemClicked.connect(self._on_item_clicked)
        self.topic_tree.itemActivated.connect(self._on_item_activated)

        left_layout.addWidget(self.search_bar)
        left_layout.addWidget(self.result_count)
        left_layout.addWidget(self.topic_tree, 1)

        # ---- RIGHT CONTENT PANE ----------------------------------
        right_widget = QWidget()
        right_widget.setObjectName("HelpContentPane")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(4)

        self.breadcrumb = QLabel("Help")
        self.breadcrumb.setObjectName("HelpBreadcrumb")
        self.breadcrumb.setAccessibleName("Current help topic path")

        self.content_browser = QTextBrowser()
        self.content_browser.setObjectName("HelpContent")
        self.content_browser.setOpenExternalLinks(True)
        self.content_browser.setOpenLinks(False)   # handle topic:// ourselves
        self.content_browser.setAccessibleName("Help content")
        self.content_browser.setAccessibleDescription(
            "Displays the selected help topic"
        )
        self.content_browser.anchorClicked.connect(self._on_anchor_clicked)

        right_layout.addWidget(self.breadcrumb)
        right_layout.addWidget(self.content_browser, 1)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter)

    def _build_tree(self):
        """Populate the tree strictly from help_manager.get_categories()."""
        self.topic_tree.clear()
        bold = QFont()
        bold.setBold(True)

        for category, topics in self.help_manager.get_categories().items():
            cat_item = QTreeWidgetItem([category])
            cat_item.setFont(0, bold)
            # Mark as category — not selectable for content
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemIsSelectable)
            cat_item.setData(0, Qt.UserRole, None)   # None = category
            self.topic_tree.addTopLevelItem(cat_item)

            for key in topics:
                child = QTreeWidgetItem([key])
                child.setData(0, Qt.UserRole, key)
                cat_item.addChild(child)

        self.topic_tree.expandAll()

    # ------------------------------------------------------------------
    # Theme detection
    # ------------------------------------------------------------------

    def _current_theme(self) -> str:
        app = QApplication.instance()
        if app is None:
            return 'light'
        lightness = app.palette().color(QPalette.Window).lightness()
        return 'dark' if lightness < 128 else 'light'

    def refresh_theme(self):
        """Re-render current page with the detected theme (call after theme switch)."""
        theme = self._current_theme()
        if self.current_topic_key:
            self.content_browser.setHtml(
                self.help_manager.get_content(self.current_topic_key, theme)
            )
        else:
            self.content_browser.setHtml(
                self.help_manager.get_landing_page(theme)
            )

    # ------------------------------------------------------------------
    # Content loading
    # ------------------------------------------------------------------

    def _load_topic(self, key: str):
        """Load topic content, update breadcrumb, emit signal."""
        theme = self._current_theme()
        html = self.help_manager.get_content(key, theme)
        self.current_topic_key = key
        self.content_browser.setHtml(html)

        # Find category for breadcrumb
        category = ""
        for cat, topics in self.help_manager.get_categories().items():
            if key in topics:
                category = cat
                break
        if category:
            self.breadcrumb.setText(f"Help  ›  {category}  ›  {key}")
        else:
            self.breadcrumb.setText(f"Help  ›  {key}")

        # Re-highlight if a search is active
        q = self.search_bar.text().strip()
        if q:
            self._highlight(q)

        self.help_topic_selected.emit(key)

    def _select_tree_item_by_key(self, key: str) -> bool:
        """Select and scroll to the tree item matching *key*.  Returns True on success."""
        for i in range(self.topic_tree.topLevelItemCount()):
            cat_item = self.topic_tree.topLevelItem(i)
            for j in range(cat_item.childCount()):
                child = cat_item.child(j)
                if child.data(0, Qt.UserRole) == key:
                    self.topic_tree.setCurrentItem(child)
                    self.topic_tree.scrollToItem(child)
                    return True
        return False

    # ------------------------------------------------------------------
    # Tree interaction
    # ------------------------------------------------------------------

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        key = item.data(0, Qt.UserRole)
        if key is None:
            # Category header — toggle expansion
            item.setExpanded(not item.isExpanded())
        else:
            self._load_topic(key)

    def _on_item_activated(self, item: QTreeWidgetItem, column: int):
        """Keyboard Enter on a topic item."""
        key = item.data(0, Qt.UserRole)
        if key is not None:
            self._load_topic(key)

    # ------------------------------------------------------------------
    # Anchor / link handling
    # ------------------------------------------------------------------

    def _on_anchor_clicked(self, url):
        scheme = url.scheme()
        if scheme == "topic":
            # topic://<url-encoded key>
            key = unquote(url.host() + url.path()).strip("/")
            if not key:
                # Qt puts the whole path in host sometimes; try path alone
                key = unquote(url.toString()[len("topic://"):])
            if key:
                self._select_tree_item_by_key(key)
                self._load_topic(key)
        else:
            # External URL — open in default browser
            import webbrowser
            webbrowser.open(url.toString())

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _on_search_text_changed(self):
        self.search_timer.start()

    def perform_search(self):
        query = self.search_bar.text().strip()
        if not query:
            self.result_count.setVisible(False)
            self._restore_full_tree()
            self._clear_highlight()
            return

        results = self.help_manager.search(query)
        matching_keys = {key for key, _snippet in results}

        # Update tree visibility
        has_any = False
        for i in range(self.topic_tree.topLevelItemCount()):
            cat_item = self.topic_tree.topLevelItem(i)
            cat_has_match = False
            for j in range(cat_item.childCount()):
                child = cat_item.child(j)
                key = child.data(0, Qt.UserRole)
                visible = key in matching_keys
                child.setHidden(not visible)
                if visible:
                    cat_has_match = True
                    has_any = True
            cat_item.setHidden(not cat_has_match)

        self.topic_tree.expandAll()

        # Update result count label
        n = len(results)
        if n == 0:
            self.result_count.setText(f"No results for ‘{query}’")
        else:
            self.result_count.setText(f"{n} result{'s' if n != 1 else ''}")
        self.result_count.setVisible(True)

        # Re-highlight current content if a topic is shown
        if self.current_topic_key:
            self._highlight(query)

    def _restore_full_tree(self):
        for i in range(self.topic_tree.topLevelItemCount()):
            cat_item = self.topic_tree.topLevelItem(i)
            cat_item.setHidden(False)
            for j in range(cat_item.childCount()):
                cat_item.child(j).setHidden(False)

    # ------------------------------------------------------------------
    # Highlighting via ExtraSelections
    # ------------------------------------------------------------------

    def _highlight(self, term: str):
        if not term:
            self._clear_highlight()
            return

        doc = self.content_browser.document()
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#FDE68A"))

        selections = []
        cursor = self.content_browser.textCursor()
        cursor.setPosition(0)

        find_flags = self.content_browser.document().defaultTextOption()  # not used directly
        from PyQt5.QtGui import QTextDocument
        pos = 0
        while True:
            found = doc.find(term, pos, QTextDocument.FindCaseSensitively.__class__(0))
            # Use case-insensitive find
            found = doc.find(term, pos)
            if found.isNull():
                break
            sel = QTextBrowser.ExtraSelection()
            sel.cursor = found
            sel.format = fmt
            selections.append(sel)
            pos = found.selectionEnd()
            if pos <= found.selectionStart():
                break

        self.content_browser.setExtraSelections(selections)

    def _clear_highlight(self):
        self.content_browser.setExtraSelections([])

    # ------------------------------------------------------------------
    # Keyboard / accessibility
    # ------------------------------------------------------------------

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()
        if (key == Qt.Key_F and mods & Qt.ControlModifier) or key == Qt.Key_F3:
            self.search_bar.setFocus()
            self.search_bar.selectAll()
        elif key == Qt.Key_Escape:
            if self.search_bar.text():
                self.search_bar.clear()
            else:
                self.search_bar.setFocus()
        else:
            super().keyPressEvent(event)

    def _search_return_pressed(self):
        """Move focus to tree and select first visible topic."""
        self.topic_tree.setFocus()
        for i in range(self.topic_tree.topLevelItemCount()):
            cat_item = self.topic_tree.topLevelItem(i)
            if cat_item.isHidden():
                continue
            for j in range(cat_item.childCount()):
                child = cat_item.child(j)
                if not child.isHidden():
                    self.topic_tree.setCurrentItem(child)
                    key = child.data(0, Qt.UserRole)
                    if key:
                        self._load_topic(key)
                    return

    # ------------------------------------------------------------------
    # Show event
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_theme()
        if not self.current_topic_key:
            # Show landing page
            theme = self._current_theme()
            self.content_browser.setHtml(
                self.help_manager.get_landing_page(theme)
            )
            self.breadcrumb.setText("Help")
