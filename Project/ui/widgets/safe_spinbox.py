"""
Safe SpinBox Widgets for Laboratory Applications
=================================================

Disables scroll wheel to prevent accidental value changes during page navigation.

Critical for:
- Precision experiments (±5% delivery variance requirement)
- Lab safety (wrong values = bad science)
- User expectations (explicit value changes only)

Best Practices:
- Medical devices: Explicit confirmation required (FDA guidance)
- Industrial control: Accidental changes = safety hazards
- Scientific software: Data integrity paramount

Usage:
    from ui.widgets.safe_spinbox import SafeSpinBox, SafeDoubleSpinBox
    
    # Replace QSpinBox with SafeSpinBox
    self.min_triggers = SafeSpinBox()
    
    # Replace QDoubleSpinBox with SafeDoubleSpinBox  
    self.flow_sampling_hz = SafeDoubleSpinBox()
"""

from PyQt5.QtWidgets import QSpinBox, QDoubleSpinBox
from PyQt5.QtCore import Qt


class SafeSpinBox(QSpinBox):
    """
    SpinBox with scroll wheel disabled for lab safety.
    
    User must:
    1. Click to focus
    2. Type value OR use up/down arrows
    
    Prevents accidental changes during page scrolling.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.StrongFocus)  # Require explicit focus
    
    def wheelEvent(self, event):
        """
        Ignore wheel events unless widget has focus.
        
        This prevents accidental changes while scrolling the page.
        User must click the spinbox first to enable wheel control.
        """
        if self.hasFocus():
            # Allow wheel when focused (intentional interaction)
            super().wheelEvent(event)
        else:
            # Ignore wheel when not focused (accidental scroll)
            event.ignore()


class SafeDoubleSpinBox(QDoubleSpinBox):
    """
    DoubleSpinBox with scroll wheel disabled for lab safety.
    
    User must:
    1. Click to focus
    2. Type value OR use up/down arrows
    
    Prevents accidental changes during page scrolling.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.StrongFocus)  # Require explicit focus
    
    def wheelEvent(self, event):
        """
        Ignore wheel events unless widget has focus.
        
        This prevents accidental changes while scrolling the page.
        User must click the spinbox first to enable wheel control.
        """
        if self.hasFocus():
            # Allow wheel when focused (intentional interaction)
            super().wheelEvent(event)
        else:
            # Ignore wheel when not focused (accidental scroll)
            event.ignore()

