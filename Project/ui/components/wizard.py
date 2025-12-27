"""
Wizard Container Component - RSO-Inspired Step-by-Step UI Pattern

Design Principles:
- Multi-step guided configuration (reduces cognitive load)
- Visual progress indicator with step states
- Navigation controls with validation
- Signal-based completion for loose coupling

Reference: Material Design Steppers
https://material.io/components/steppers

Architecture:
- WizardStep: Individual step definition
- WizardProgress: Visual step indicator
- WizardContainer: Main orchestrator
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


@dataclass
class WizardStep:
    """Definition of a wizard step."""
    key: str                              # Unique identifier
    title: str                            # Display title
    description: str                      # Short description
    icon: str = ""                        # Optional icon character
    can_skip: bool = False                # Whether step can be skipped
    validation_fn: Optional[Callable[[], bool]] = None  # Validation function


class WizardProgress(QWidget):
    """
    Visual progress indicator showing step states.
    
    States:
    - completed: Checkmark, teal background
    - current: Filled circle, teal border
    - pending: Gray outline
    """
    
    def __init__(self, steps: List[WizardStep], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._steps = steps
        self._current_index = 0
        self._init_ui()
    
    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(0)
        
        self._step_widgets: List[QWidget] = []
        self._connectors: List[QFrame] = []
        
        for i, step in enumerate(self._steps):
            # Step indicator
            step_widget = self._create_step_indicator(i, step)
            self._step_widgets.append(step_widget)
            layout.addWidget(step_widget)
            
            # Connector line (except after last step)
            if i < len(self._steps) - 1:
                connector = QFrame()
                connector.setObjectName("WizardConnector")
                connector.setFixedHeight(2)
                connector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self._connectors.append(connector)
                layout.addWidget(connector)
        
        self._update_styles()
    
    def _create_step_indicator(self, index: int, step: WizardStep) -> QWidget:
        """Create a single step indicator with number and title."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignHCenter)
        
        # Circle with number/checkmark
        circle = QLabel()
        circle.setObjectName("WizardStepCircle")
        circle.setFixedSize(36, 36)
        circle.setAlignment(Qt.AlignCenter)
        circle.setProperty("step_index", index)
        container._circle = circle
        layout.addWidget(circle, alignment=Qt.AlignHCenter)
        
        # Step title
        title = QLabel(step.title)
        title.setObjectName("WizardStepTitle")
        title.setAlignment(Qt.AlignCenter)
        container._title = title
        layout.addWidget(title)
        
        return container
    
    def set_current_step(self, index: int) -> None:
        """Update the current step and refresh styles."""
        self._current_index = max(0, min(index, len(self._steps) - 1))
        self._update_styles()
    
    def _update_styles(self) -> None:
        """Update visual states of all steps."""
        for i, widget in enumerate(self._step_widgets):
            circle = widget._circle
            title = widget._title
            
            if i < self._current_index:
                # Completed
                circle.setProperty("state", "completed")
                circle.setText("✓")
                title.setProperty("state", "completed")
            elif i == self._current_index:
                # Current
                circle.setProperty("state", "current")
                circle.setText(str(i + 1))
                title.setProperty("state", "current")
            else:
                # Pending
                circle.setProperty("state", "pending")
                circle.setText(str(i + 1))
                title.setProperty("state", "pending")
            
            # Force style refresh
            circle.style().unpolish(circle)
            circle.style().polish(circle)
            title.style().unpolish(title)
            title.style().polish(title)
        
        # Update connectors
        for i, connector in enumerate(self._connectors):
            if i < self._current_index:
                connector.setProperty("state", "completed")
            else:
                connector.setProperty("state", "pending")
            connector.style().unpolish(connector)
            connector.style().polish(connector)


class WizardContainer(QWidget):
    """
    Main wizard orchestrator with step content and navigation.
    
    Signals:
        step_changed(int): Emitted when current step changes
        completed(): Emitted when wizard is completed (Finish clicked)
        cancelled(): Emitted when wizard is cancelled (Back on step 0)
    
    Usage:
        wizard = WizardContainer(steps=[...])
        wizard.add_step_content("step1", widget1)
        wizard.add_step_content("step2", widget2)
        wizard.completed.connect(self._on_wizard_complete)
    """
    
    step_changed = pyqtSignal(int)
    completed = pyqtSignal()
    cancelled = pyqtSignal()
    
    def __init__(
        self, 
        steps: List[WizardStep],
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._steps = steps
        self._current_index = 0
        self._step_contents: Dict[str, QWidget] = {}
        self._init_ui()
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Progress indicator
        self._progress = WizardProgress(self._steps)
        layout.addWidget(self._progress)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setObjectName("WizardSeparator")
        layout.addWidget(separator)
        
        # Content area (stacked widget)
        self._content_stack = QStackedWidget()
        self._content_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._content_stack, 1)
        
        # Navigation buttons
        nav_container = QWidget()
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(20, 16, 20, 16)
        nav_layout.setSpacing(12)
        
        self._back_button = QPushButton("‹     Back")
        self._back_button.setObjectName("WizardBackButton")
        self._back_button.setMinimumWidth(120)
        self._back_button.setMinimumHeight(48)
        self._back_button.clicked.connect(self._go_back)
        
        nav_layout.addWidget(self._back_button)
        nav_layout.addStretch()
        
        self._next_button = QPushButton("Next     ›")
        self._next_button.setObjectName("WizardNextButton")
        self._next_button.setProperty("variant", "primary")
        self._next_button.setMinimumWidth(140)
        self._next_button.setMinimumHeight(48)
        self._next_button.clicked.connect(self._go_next)
        
        nav_layout.addWidget(self._next_button)
        
        layout.addWidget(nav_container)
        
        self._update_navigation()
    
    def add_step_content(self, step_key: str, widget: QWidget) -> None:
        """Add content widget for a step."""
        self._step_contents[step_key] = widget
        self._content_stack.addWidget(widget)
    
    def set_current_step(self, index: int) -> None:
        """Navigate to a specific step."""
        if 0 <= index < len(self._steps):
            self._current_index = index
            self._progress.set_current_step(index)
            
            # Show corresponding content
            step_key = self._steps[index].key
            if step_key in self._step_contents:
                widget = self._step_contents[step_key]
                self._content_stack.setCurrentWidget(widget)
            
            self._update_navigation()
            self.step_changed.emit(index)
    
    def _update_navigation(self) -> None:
        """Update navigation button states."""
        # Back button
        self._back_button.setVisible(self._current_index > 0)
        
        # Next button
        is_last = self._current_index == len(self._steps) - 1
        self._next_button.setText("Finish     ›" if is_last else "Next     ›")
        
        # Validate current step
        current_step = self._steps[self._current_index]
        if current_step.validation_fn:
            self._next_button.setEnabled(current_step.validation_fn())
        else:
            self._next_button.setEnabled(True)
    
    def set_next_enabled(self, enabled: bool) -> None:
        """Enable/disable the Next button (for validation)."""
        self._next_button.setEnabled(enabled)
    
    def _go_back(self) -> None:
        """Navigate to previous step."""
        if self._current_index > 0:
            self.set_current_step(self._current_index - 1)
        else:
            self.cancelled.emit()
    
    def _go_next(self) -> None:
        """Navigate to next step or complete."""
        if self._current_index < len(self._steps) - 1:
            self.set_current_step(self._current_index + 1)
        else:
            self.completed.emit()
    
    def get_current_step_key(self) -> str:
        """Get the key of the current step."""
        return self._steps[self._current_index].key
    
    def reset(self) -> None:
        """Reset wizard to first step."""
        self.set_current_step(0)

