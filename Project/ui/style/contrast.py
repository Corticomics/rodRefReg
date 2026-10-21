"""Contrast maths for the colour tokens: pure Python, no Qt.

WCAG 2.x relative luminance and contrast ratio, as WCAG 2.2 defines them
(https://www.w3.org/TR/WCAG22/#dfn-relative-luminance and #dfn-contrast-ratio). A ratio is
never rounded: 4.499 fails a 4.5 threshold.

Display-chain models, applied to each 8-bit channel (as a float) before the luminance:

    clip   a full-range signal shown as limited range: v' = clamp((v - 16) * 255 / 219, 0, 255)
    wash   a limited-range signal shown as full range: v' = 16 + v * 219 / 255
    hicon  a monitor's contrast set too high:          v' = min(255, v * 255 / 240)

A Pi 5 on HDMI sends limited range for TV modes such as 1080p60, so a monitor that reads the
signal the other way washes the picture out or clips its light greys to white. The palette
keeps its surface steps visible under both. contrast_ratio_flare raises WCAG's viewing-flare
term instead, for a dim monitor in a bright lab.

APCA Lc (APCA-W3 0.0.98G-4g, https://github.com/Myndex/apca-w3) is a second opinion for light
surface steps only; WCAG 2.x is the conformance measure.

CIEDE2000 (delta_e_2000) measures how different two colours look, hue included, where a
contrast ratio only compares luminance: status words that share a column must not only
contrast with their background but also differ from each other.

Project/tests/unit/test_theme_contrast.py loads this file by path and checks it against the
examples W3C publishes and CIEDE2000's reference data. After editing it, run that test.
"""

from __future__ import annotations

import math


def _rgb(colour: str) -> tuple[float, float, float]:
    """#RRGGBB or #RGB as three floats from 0 to 255."""
    digits = colour.lstrip("#")
    if len(digits) == 3:
        digits = "".join(c * 2 for c in digits)
    if len(digits) != 6:
        raise ValueError(f"not a #RRGGBB colour: {colour!r}")
    return tuple(float(int(digits[i : i + 2], 16)) for i in (0, 2, 4))


def _linear(channel: float) -> float:
    c = channel / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _luminance(rgb: tuple[float, float, float]) -> float:
    r, g, b = rgb
    return 0.2126 * _linear(r) + 0.7152 * _linear(g) + 0.0722 * _linear(b)


def relative_luminance(colour: str) -> float:
    """WCAG relative luminance of a #RRGGBB colour, from 0 (black) to 1 (white)."""
    return _luminance(_rgb(colour))


MODELS = {
    "nominal": lambda v: v,
    "clip": lambda v: min(255.0, max(0.0, (v - 16) * 255 / 219)),
    "wash": lambda v: 16 + v * 219 / 255,
    "hicon": lambda v: min(255.0, v * 255 / 240),
}


def contrast_ratio(a: str, b: str, model: str = "nominal") -> float:
    """WCAG 2.x contrast ratio of two colours, after a display-chain model; order-free."""
    convert = MODELS[model]
    la = _luminance(tuple(convert(v) for v in _rgb(a)))
    lb = _luminance(tuple(convert(v) for v in _rgb(b)))
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def contrast_ratio_flare(a: str, b: str, flare: float = 0.10) -> float:
    """The WCAG ratio with its 0.05 viewing-flare term raised: a dim monitor in a bright lab."""
    la, lb = relative_luminance(a), relative_luminance(b)
    return (max(la, lb) + flare) / (min(la, lb) + flare)


_APCA = {
    "trc": 2.4,
    "r": 0.2126729,
    "g": 0.7151522,
    "b": 0.0721750,
    "norm_bg": 0.56,
    "norm_text": 0.57,
    "rev_text": 0.62,
    "rev_bg": 0.65,
    "black_threshold": 0.022,
    "black_clamp": 1.414,
    "scale": 1.14,
    "offset": 0.027,
    "delta_min": 0.0005,
    "low_clip": 0.1,
}


def _apca_y(colour: str) -> float:
    r, g, b = _rgb(colour)
    t = _APCA["trc"]
    return _APCA["r"] * (r / 255) ** t + _APCA["g"] * (g / 255) ** t + _APCA["b"] * (b / 255) ** t


def apca_lc(text: str, background: str) -> float:
    """Signed APCA Lc of `text` on `background`: positive for dark text on a light background."""
    a = _APCA
    ty, by = _apca_y(text), _apca_y(background)
    if ty <= a["black_threshold"]:
        ty += (a["black_threshold"] - ty) ** a["black_clamp"]
    if by <= a["black_threshold"]:
        by += (a["black_threshold"] - by) ** a["black_clamp"]
    if abs(by - ty) < a["delta_min"]:
        return 0.0
    if by > ty:
        s = (by ** a["norm_bg"] - ty ** a["norm_text"]) * a["scale"]
        return 0.0 if s < a["low_clip"] else (s - a["offset"]) * 100.0
    s = (by ** a["rev_bg"] - ty ** a["rev_text"]) * a["scale"]
    return 0.0 if s > -a["low_clip"] else (s + a["offset"]) * 100.0


def apca_step(a: str, b: str) -> float:
    """The smaller |Lc| of the two polarities: for a surface step neither colour is the text."""
    return min(abs(apca_lc(a, b)), abs(apca_lc(b, a)))


# ---- Colour difference ---------------------------------------------------------------

# sRGB to CIE XYZ (IEC 61966-2-1), and the D65 white point
_XYZ = (
    (0.4124, 0.3576, 0.1805),
    (0.2126, 0.7152, 0.0722),
    (0.0193, 0.1192, 0.9505),
)
_D65 = (0.95047, 1.0, 1.08883)


def lab(colour: str) -> tuple[float, float, float]:
    """CIELAB (L*, a*, b*) of a #RRGGBB colour, D65."""
    linear = [_linear(v) for v in _rgb(colour)]
    xyz = [sum(m * c for m, c in zip(row, linear)) for row in _XYZ]

    def f(t: float) -> float:
        delta = 6 / 29
        return t ** (1 / 3) if t > delta**3 else t / (3 * delta**2) + 4 / 29

    fx, fy, fz = (f(v / n) for v, n in zip(xyz, _D65))
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e_2000_lab(lab1: tuple[float, float, float], lab2: tuple[float, float, float]) -> float:
    """CIEDE2000 difference of two CIELAB colours (kL = kC = kH = 1), as Sharma, Wu and
    Dalal give it (Color Research and Application 30, 2005)."""
    l1, a1, b1 = lab1
    l2, a2, b2 = lab2
    c_mean = (math.hypot(a1, b1) + math.hypot(a2, b2)) / 2
    g = 0.5 * (1 - math.sqrt(c_mean**7 / (c_mean**7 + 25**7)))
    a1, a2 = (1 + g) * a1, (1 + g) * a2
    c1, c2 = math.hypot(a1, b1), math.hypot(a2, b2)
    h1 = math.degrees(math.atan2(b1, a1)) % 360 if c1 else 0.0
    h2 = math.degrees(math.atan2(b2, a2)) % 360 if c2 else 0.0

    dh = 0.0
    if c1 * c2:
        dh = h2 - h1
        if dh > 180:
            dh -= 360
        elif dh < -180:
            dh += 360
    d_l = l2 - l1
    d_c = c2 - c1
    d_h = 2 * math.sqrt(c1 * c2) * math.sin(math.radians(dh / 2))

    l_mean = (l1 + l2) / 2
    c_mean = (c1 + c2) / 2
    if not c1 * c2:
        h_mean = h1 + h2
    elif abs(h1 - h2) <= 180:
        h_mean = (h1 + h2) / 2
    elif h1 + h2 < 360:
        h_mean = (h1 + h2 + 360) / 2
    else:
        h_mean = (h1 + h2 - 360) / 2

    def cos(degrees: float) -> float:
        return math.cos(math.radians(degrees))

    t = (
        1
        - 0.17 * cos(h_mean - 30)
        + 0.24 * cos(2 * h_mean)
        + 0.32 * cos(3 * h_mean + 6)
        - 0.20 * cos(4 * h_mean - 63)
    )
    s_l = 1 + 0.015 * (l_mean - 50) ** 2 / math.sqrt(20 + (l_mean - 50) ** 2)
    s_c = 1 + 0.045 * c_mean
    s_h = 1 + 0.015 * c_mean * t
    rotation = math.radians(60 * math.exp(-(((h_mean - 275) / 25) ** 2)))
    r_t = -math.sin(rotation) * 2 * math.sqrt(c_mean**7 / (c_mean**7 + 25**7))
    lightness, chroma, hue = d_l / s_l, d_c / s_c, d_h / s_h
    return math.sqrt(lightness**2 + chroma**2 + hue**2 + r_t * chroma * hue)


def delta_e_2000(a: str, b: str) -> float:
    """CIEDE2000 difference of two #RRGGBB colours: about 1 is just noticeable side by side;
    the status words of v2.0.0's Calibration table, mustard and red, were 40.7 apart."""
    return delta_e_2000_lab(lab(a), lab(b))
