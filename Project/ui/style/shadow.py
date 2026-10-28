"""Card shadows as numbers, without Qt: how far a recipe reaches past a card, the room a card
reserves for it, the alpha of each pixel past a straight edge, and the pixels of its tile.

A recipe (tokens.SHADOWS) is a tuple of CSS box-shadow layers (x, y, blur, spread, alpha),
in px, painted in the shadow.ink role. As CSS draws it (CSS Backgrounds 3, "shadow-blur"):
each layer is the card's border box grown by its spread (its corner radius too), moved by
(x, y) and blurred by a Gaussian of sigma = blur / 2; the layers composite "over" one
another, and nothing is drawn inside the border box.

Three readers: ui/style/elevation.py paints the tile, build_qss.py writes the reserved room
into the stylesheet (${elevation.<level>.margin}), and the tests check the profile against
the display models (test_theme_contrast.py, E1 and E2). Pure Python: build_qss.py and the
tests load it by path, as they load tokens.py.
"""

from __future__ import annotations

import math
from typing import NamedTuple


# NamedTuples, not dataclasses: a dataclass needs its module in sys.modules, and this one is
# loaded by path.
class Extent(NamedTuple):
    """How far a shadow reaches past the card's border box on each side, in whole px."""

    left: int
    top: int
    right: int
    bottom: int

    def qss(self) -> str:
        """The stylesheet margin that reserves it: top right bottom left."""
        return f"{self.top}px {self.right}px {self.bottom}px {self.left}px"


def extent(layers) -> Extent:
    """How far `layers` reach past the border box: 3 sigma (1.5 x blur) plus the spread,
    shifted by the offset. Past it a layer keeps under 0.14 % of its alpha, below one 8-bit
    step for any alpha a recipe uses."""

    def reach(sx, sy):
        return max(
            0,
            max(
                math.ceil(1.5 * blur + spread + sx * x + sy * y)
                for x, y, blur, spread, _ in layers
            ),
        )

    return Extent(reach(-1, 0), reach(0, -1), reach(1, 0), reach(0, 1))


def union(extents) -> Extent:
    extents = list(extents)
    if not extents:
        return Extent(0, 0, 0, 0)
    return Extent(
        *(max(getattr(e, side) for e in extents) for side in ("left", "top", "right", "bottom"))
    )


def reserved(tokens) -> Extent:
    """The room every elevated card reserves round its box: the union of the reach of every
    recipe in tokens.SHADOWS, so ELEVATION may name any of them, in either theme, without a
    widget moving. The dark theme keeps the room and paints nothing in it."""
    return union(extent(layers) for layers in tokens.SHADOWS.values())


def qss_values(tokens) -> dict[str, str]:
    """The stylesheet values build_qss.py writes besides colours: ${elevation.<level>.margin}
    for every level of tokens.ELEVATION (one room for all: see reserved())."""
    room = reserved(tokens).qss()
    return {f"elevation.{level}.margin": room for level in tokens.ELEVATION}


# ---- The alpha of a pixel --------------------------------------------------------------------


def _phi(z: float) -> float:
    return 0.5 * math.erfc(-z / math.sqrt(2.0))


def layer_alpha(distance: float, blur: float, alpha: float) -> float:
    """One layer's alpha at `distance` px outside its grown, moved shape (negative inside)."""
    if blur <= 0:
        return alpha if distance <= 0 else 0.0
    return alpha * _phi(-distance / (blur / 2.0))


def edge_alpha(layers, edge: str, row: int) -> float:
    """The alpha of pixel `row` past a straight edge of the box, far from its corners: row 0
    is the first pixel outside the border box, its centre 0.5 px out. `edge` is "bottom",
    "top", "left" or "right"."""
    t = row + 0.5
    total = 0.0
    for x, y, blur, spread, alpha in layers:
        shift = {"bottom": y, "top": -y, "left": -x, "right": x}[edge]
        a = layer_alpha(t - shift - spread, blur, alpha)
        total = a + total * (1 - a)  # "over"; one ink, so only alpha accumulates
    return total


def over(background: str, ink: str, alpha: float) -> str:
    """The 8-bit colour of `ink` at `alpha` over an opaque `background` ("#RRGGBB")."""
    bg = [int(background[i : i + 2], 16) for i in (1, 3, 5)]
    fg = [int(ink[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(b + (f - b) * alpha):02X}" for b, f in zip(bg, fg))


# ---- The tile --------------------------------------------------------------------------------


def _sd_round_rect(px, py, x0, y0, x1, y1, r):
    """Signed distance from (px, py) to the rounded rect [x0, x1] x [y0, y1] of radius r
    (negative inside)."""
    hx = (x1 - x0) / 2 - r
    hy = (y1 - y0) / 2 - r
    qx = abs(px - (x0 + x1) / 2) - hx
    qy = abs(py - (y0 + y1) / 2) - hy
    return math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - r


class TileAlpha(NamedTuple):
    """A 9-slice tile's alpha, one byte a pixel, row by row (width x height device px), with
    the extent it paints past the box and its corner slices (left, top, right, bottom) in
    logical px."""

    width: int
    height: int
    alpha: bytes
    ext: Extent
    corner: tuple


def tile_alpha(layers, radius: float, dpr: float = 1.0) -> TileAlpha:
    """The shadow of `layers` round a rounded rect of `radius` (logical px), as a 9-slice
    tile: a box 2 * reach + 1 px square, so each corner slice holds a whole corner and the
    1 px middle strips hold the straight-edge profile.

    The tile is painted after the card's box: where the box covers a whole pixel the tile is
    empty, and on the box's anti-aliased rim the shadow is scaled by what the box leaves
    uncovered (Breeze's and Telegram's DestinationOut cut-out).
    """
    ext = extent(layers)
    s_max = max(blur for _, _, blur, _, _ in layers) / 2.0
    reach = math.ceil(
        radius + 3 * s_max + max(abs(x) + abs(y) + abs(s) for x, y, _, s, _ in layers)
    )
    body = 2 * reach + 1
    cl, ct, cr, cb = ext.left + reach, ext.top + reach, ext.right + reach, ext.bottom + reach
    w, h = cl + 1 + cr, ct + 1 + cb
    width, height = round(w * dpr), round(h * dpr)
    x0, y0 = ext.left, ext.top
    x1, y1 = x0 + body, y0 + body
    out = bytearray(width * height)
    for j in range(height):
        py = (j + 0.5) / dpr
        for i in range(width):
            px = (i + 0.5) / dpr
            inside = _sd_round_rect(px, py, x0, y0, x1, y1, radius) * dpr
            if inside <= -0.5:
                continue  # under the box
            keep = min(1.0, 0.5 + inside)  # what the box's anti-aliased rim leaves uncovered
            total = 0.0
            for x, y, blur, spread, alpha in layers:
                d = _sd_round_rect(
                    px - x,
                    py - y,
                    x0 - spread,
                    y0 - spread,
                    x1 + spread,
                    y1 + spread,
                    radius + spread,
                )
                a = layer_alpha(d, blur, alpha)
                total = a + total * (1 - a)
            out[j * width + i] = round(255 * total * keep)
    return TileAlpha(width, height, bytes(out), ext, (cl, ct, cr, cb))
