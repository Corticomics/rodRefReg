"""The QPalette of a theme, built from the same tokens as its stylesheet.

StyleManager.apply sets it on the application before the stylesheet. The stylesheet styles
the widgets its rules name; everything else draws with the palette, so the palette has to
follow the theme too:
- the window and dialogs (Window), and every plain container, which is transparent over it;
- the text of labels, inputs, tables and lists (WindowText, Text, ButtonText);
- placeholders (PlaceholderText). A `color` a stylesheet rule gives an input becomes its
  placeholder's colour too: from Qt 5.15.12 at half its alpha, which no colour can lift to
  4.5:1, and up to 5.15.11 (the Pi's 5.15.8) at full strength, so the hint looks like typed
  text. So no rule colours an input, and the palette gives the placeholder its colour;
- alternate table rows (AlternateBase): Fusion's own light grey under the dark theme's
  light text is what made the dark zebra rows unreadable;
- selection, rich-text links, tooltips, and the Disabled group of disabled widgets.

The roles come from tokens.QPALETTE and tokens.QPALETTE_DISABLED. Qt's shade roles (Light,
Midlight, Mid, Dark, Shadow) are derived from the button and window colours, so a frame
drawn with them suits the theme as well.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from PyQt5.QtGui import QColor, QPalette


def _load_tokens():
    # By path, as build_qss.py does: importing the ui package would import the whole GUI.
    path = Path(__file__).with_name("tokens.py")
    spec = importlib.util.spec_from_file_location("rrr_style_tokens", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tokens = _load_tokens()

GROUPS = (QPalette.Active, QPalette.Inactive, QPalette.Disabled)


def build_palette(theme: str) -> QPalette:
    """The application palette for `theme` ("light" or "dark")."""
    colour = {name: QColor(tokens.value(name, theme)) for name in tokens.TOKENS}
    palette = QPalette(colour[tokens.QPALETTE["Button"]], colour[tokens.QPALETTE["Window"]])
    for role_name, token in tokens.QPALETTE.items():
        role = getattr(QPalette, role_name)
        for group in GROUPS:
            palette.setColor(group, role, colour[token])
    for role_name, token in tokens.QPALETTE_DISABLED.items():
        palette.setColor(QPalette.Disabled, getattr(QPalette, role_name), colour[token])
    return palette
