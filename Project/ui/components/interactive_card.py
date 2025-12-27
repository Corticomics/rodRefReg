"""
Interactive Card Component - Selectable Card for Wizard Steps

Design Principles:
- Visual feedback on hover and selection
- Teal accent border when selected
- Radio-button behavior in groups
- Icon, title, description, and optional badge

Reference: Material Design Cards with Selection
https://material.io/components/cards#selection
"""

from __future__ import annotations

from typing import Optional
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal


class InteractiveCard(QFrame):
    """
    A card that can be selected/checked with visual feedback.
    
    Signals:
        clicked(): Emitted when card is clicked
        checked_changed(bool): Emitted when checked state changes
    
    Usage:
        card = InteractiveCard(
            title="Staggered Delivery",
            description="Distribute water evenly across a time window",
            icon="⏱",
            badge="Recommended"
        )
        card.clicked.connect(lambda: self._select_card(card))
    """
    
    clicked = pyqtSignal()
    checked_changed = pyqtSignal(bool)
    
    def __init__(
        self,
        title: str,
        description: str = "",
        icon: str = "",
        badge: str = "",
        checkable: bool = True,
        parent: Optional[QFrame] = None
    ):
        super().__init__(parent)
        self._title = title
        self._description = description
        self._icon = icon
        self._badge = badge
        self._checkable = checkable
        self._checked = False
        
        self.setObjectName("InteractiveCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._init_ui()
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        # Header row: icon + title
        header = QHBoxLayout()
        header.setSpacing(12)
        
        if self._icon:
            icon_label = QLabel(self._icon)
            icon_label.setObjectName("CardIcon")
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setFixedSize(32, 32)
            header.addWidget(icon_label)
        
        title_label = QLabel(self._title)
        title_label.setObjectName("CardTitle")
        title_label.setWordWrap(True)
        header.addWidget(title_label, 1)
        
        if self._badge:
            badge_label = QLabel(self._badge)
            badge_label.setObjectName("CardBadge")
            badge_label.setAlignment(Qt.AlignCenter)
            header.addWidget(badge_label)
        
        layout.addLayout(header)
        
        # Description
        if self._description:
            desc_label = QLabel(self._description)
            desc_label.setObjectName("CardDescription")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)
        
        self._update_style()
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse press."""
        if event.button() == Qt.LeftButton:
            if self._checkable:
                self.set_checked(not self._checked)
            self.clicked.emit()
        super().mousePressEvent(event)
    
    def set_checked(self, checked: bool) -> None:
        """Set the checked state."""
        if self._checked != checked:
            self._checked = checked
            self._update_style()
            self.checked_changed.emit(checked)
    
    def is_checked(self) -> bool:
        """Get the checked state."""
        return self._checked
    
    def _update_style(self) -> None:
        """Update visual style based on state."""
        self.setProperty("checked", self._checked)
        self.style().unpolish(self)
        self.style().polish(self)
    
    def get_title(self) -> str:
        """Get card title."""
        return self._title


class SelectableCardGroup:
    """
    Manages a group of InteractiveCards with single-selection behavior.
    
    Usage:
        group = SelectableCardGroup()
        group.add_card("staggered", card1)
        group.add_card("instant", card2)
        group.selection_changed.connect(self._on_selection)
    """
    
    def __init__(self):
        self._cards: dict[str, InteractiveCard] = {}
        self._selected_key: Optional[str] = None
        self._callbacks: list = []
    
    def add_card(self, key: str, card: InteractiveCard) -> None:
        """Add a card to the group."""
        self._cards[key] = card
        card.clicked.connect(lambda k=key: self._on_card_clicked(k))
    
    def _on_card_clicked(self, key: str) -> None:
        """Handle card click - ensure single selection."""
        self._selected_key = key
        for k, card in self._cards.items():
            card.set_checked(k == key)
        
        # Notify listeners
        for callback in self._callbacks:
            callback(key)
    
    def on_selection_changed(self, callback) -> None:
        """Register a callback for selection changes."""
        self._callbacks.append(callback)
    
    def get_selected_key(self) -> Optional[str]:
        """Get the currently selected key."""
        return self._selected_key
    
    def clear_selection(self) -> None:
        """Clear all selections."""
        self._selected_key = None
        for card in self._cards.values():
            card.set_checked(False)

