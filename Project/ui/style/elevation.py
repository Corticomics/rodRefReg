"""Card elevation: a soft shadow painted from a cached, pre-blurred 9-slice tile, in room the
card reserves round its box with a stylesheet margin.

Qt's stylesheets have no box-shadow, and QGraphicsDropShadowEffect is ruled out for cards: it
renders the card and all its children into a new pixmap and blurs it again on every change
inside the card, fills the global QPixmapCache, casts a shadow from whatever the card paints,
and on the Pi's Qt 5.15.8 composites its shadow over its own earlier output until it turns
near-black (QTBUG-102374, fixed in 5.15.10, which Debian bookworm does not ship). Instead:

- the recipe is data: tokens.ELEVATION names a recipe of tokens.SHADOWS for each theme (CSS
  box-shadow layers), in the shadow.ink role; the dark theme's is None and paints nothing;
- shadow.tile_alpha computes the recipe once per (recipe, radius, device pixel ratio, ink)
  into a small 9-slice tile, kept in a module dict (not QPixmapCache, which could evict it);
- the card's rule QFrame[elevation="card"] reserves the room with a margin (build_qss.py
  writes it from the recipes, so it cannot drift from them): Qt draws the card's box (fill,
  stroke, radius: ordinary stylesheet rules) inside it, and ElevatedMixin.paintEvent paints
  the tile round the box. Telegram Desktop's popup menus reserve and paint their shadow the
  same way;
- the recipe is read when painting, from the theme StyleManager applied last: a theme switch
  sets a new stylesheet, which repaints every widget, so the shadow follows with no signal.

A card in a layout is bigger than its box by the room: a parent that aligns the box with
other edges gives the room back in its own margins (see the cards' modules).

tokens.ELEVATION is the one source of a card's shadow: to change it, name another recipe
of tokens.SHADOWS there. Every recipe fits the reserved room, so nothing moves.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from PyQt5.QtCore import QRect
from PyQt5.QtGui import QColor, QImage, QPainter, QPixmap

from . import shadow
from .qt_palette import tokens
from .theme import current_theme

# The room every elevated card reserves (the stylesheet's margin, from the same recipes)
ROOM = shadow.reserved(tokens)


def recipe(level: str, theme: str):
    """The layers of elevation `level` in `theme`, or None when it paints no shadow."""
    light, dark = tokens.ELEVATION[level]
    name = light if theme == "light" else dark
    if name is None:
        return None
    return tokens.SHADOWS[name]


@dataclass(frozen=True)
class Tile:
    pixmap: QPixmap
    ext: shadow.Extent
    corner: tuple  # left, top, right, bottom slice sizes, logical px


_TILES: dict = {}


def cached_tile(layers, radius: float, dpr: float, ink: str) -> Tile:
    """The tile of `layers` round a box of `radius`, in `ink`, made once per process."""
    key = (layers, radius, dpr, ink)
    tile = _TILES.get(key)
    if tile is None:
        data = shadow.tile_alpha(layers, radius, dpr)
        colour = QColor(ink)
        rgb = (colour.red(), colour.green(), colour.blue())
        buf = bytearray(len(data.alpha) * 4)  # premultiplied R, G, B, A, whatever the endianness
        for i, a in enumerate(data.alpha):
            if a:
                buf[4 * i : 4 * i + 4] = bytes((c * a + 127) // 255 for c in rgb) + bytes((a,))
        image = QImage(
            bytes(buf),
            data.width,
            data.height,
            data.width * 4,
            QImage.Format_RGBA8888_Premultiplied,
        ).copy()
        image.setDevicePixelRatio(dpr)
        pixmap = QPixmap.fromImage(image)
        pixmap.setDevicePixelRatio(dpr)
        tile = _TILES[key] = Tile(pixmap, data.ext, data.corner)
    return tile


def paint_tile(painter: QPainter, box: QRect, tile: Tile) -> None:
    """Paint `tile` round `box` (logical px): the corners as they are, the edges stretched
    from the tile's 1 px middle strips, no centre (Telegram's Ui::Shadow, Breeze's TileSet)."""
    e, (cl, ct, cr, cb) = tile.ext, tile.corner
    pm = tile.pixmap
    d = pm.devicePixelRatio()
    o = box.adjusted(-e.left, -e.top, e.right, e.bottom)
    sw, sh = pm.width() / d, pm.height() / d
    cw, ch = o.width() - cl - cr, o.height() - ct - cb
    if cw < 0 or ch < 0:
        return  # a box smaller than the tile's corners: not a card

    def blit(tx, ty, tw, th, sx, sy, sw_, sh_):
        if tw > 0 and th > 0:
            painter.drawPixmap(
                QRect(tx, ty, tw, th),
                pm,
                QRect(round(sx * d), round(sy * d), round(sw_ * d), round(sh_ * d)),
            )

    x, y = o.x(), o.y()
    blit(x, y, cl, ct, 0, 0, cl, ct)
    blit(x + cl + cw, y, cr, ct, sw - cr, 0, cr, ct)
    blit(x, y + ct + ch, cl, cb, 0, sh - cb, cl, cb)
    blit(x + cl + cw, y + ct + ch, cr, cb, sw - cr, sh - cb, cr, cb)
    blit(x + cl, y, cw, ct, cl, 0, 1, ct)
    blit(x + cl, y + ct + ch, cw, cb, cl, sh - cb, 1, cb)
    blit(x, y + ct, cl, ch, 0, ct, cl, 1)
    blit(x + cl + cw, y + ct, cr, ch, sw - cr, ct, cr, 1)


class ElevatedMixin:
    """Mix into a QFrame card before QFrame: class Card(ElevatedMixin, QFrame).

    Call init_elevation() in __init__, before the card is first polished (shown). It sets the
    card's `elevation` property, which the stylesheet's QFrame[elevation="card"] rule gives
    the room for the shadow; the card's box (fill, stroke, radius) stays a stylesheet rule,
    and `radius` must be that rule's border-radius (the tile is drawn for it).

    at_rest=False: the shadow shows only while the pointer is on the card (a card that lifts
    under the pointer); entering and leaving the card repaint it.
    """

    _elev_level = None

    def init_elevation(
        self, level: str = "card", radius: float = 8.0, at_rest: bool = True
    ) -> None:
        self._elev_level = level
        self._elev_radius = float(radius)
        self._elev_at_rest = at_rest
        self.setProperty("elevation", level)

    def elevation_box(self) -> QRect:
        """The card's box (its border rect) in its own coordinates: its rect less the room."""
        return self.rect().adjusted(ROOM.left, ROOM.top, -ROOM.right, -ROOM.bottom)

    def elevation_shows(self) -> bool:
        """True while the card shows its shadow (in a theme whose recipe paints one)."""
        return self._elev_level is not None and (self._elev_at_rest or self.underMouse())

    def _touches_shadow(self, dirty: QRect) -> bool:
        """False when the dirty rect lies inside the box, away from its rim and its rounded
        corners: a child's update there (a label, a progress bar) costs no tile paint."""
        box = self.elevation_box()
        k = math.ceil(self._elev_radius)
        if not box.adjusted(1, 1, -1, -1).contains(dirty):
            return True
        corners = (
            QRect(box.left(), box.top(), k, k),
            QRect(box.right() - k + 1, box.top(), k, k),
            QRect(box.left(), box.bottom() - k + 1, k, k),
            QRect(box.right() - k + 1, box.bottom() - k + 1, k, k),
        )
        return any(corner.intersects(dirty) for corner in corners)

    def paintEvent(self, event) -> None:
        if self.elevation_shows():
            theme = current_theme()
            layers = recipe(self._elev_level, theme)
            if layers is not None and self._touches_shadow(event.rect()):
                tile = cached_tile(
                    layers,
                    self._elev_radius,
                    self.devicePixelRatioF(),
                    tokens.value("shadow.ink", theme),
                )
                painter = QPainter(self)
                paint_tile(painter, self.elevation_box(), tile)
                painter.end()
        super().paintEvent(event)

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        if self._elev_level is not None and not self._elev_at_rest:
            self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        if self._elev_level is not None and not self._elev_at_rest:
            self.update()
