"""The colour contract of both themes: every pair of roles the UI draws together.

The palette before v2.1.0 failed quietly for years: cards 1.05:1 against the page, outlines
1.18:1, captions 3.16:1, teal text 3.74:1, and on a monitor that clips the Pi's HDMI signal
the cards vanished altogether. This test recomputes each pair below from tokens.py with the
WCAG 2.x formula, unrounded (4.499 fails 4.5), in the light and the dark theme:

- text (WCAG 1.4.3): 4.5:1, or a higher target the palette was designed to (7:1 for body
  and secondary text on the main surfaces);
- nontext (WCAG 1.4.11): 3:1 for a boundary that identifies a control, for a mark that
  shows a state (selected, checked, the selected tab, the focus ring) or a value (the
  progress chunk);
- step: a surface against the one around it (a card on the page). WCAG asks nothing here;
  the floors are the robust-contrast palette's (1.30:1 light, 1.25:1 dark for a card);
- line: a decorative outline or divider, 1.5:1;
- cue: a hover or zebra fill, which only supports another cue; it must differ from the
  fills around it (hover from both row colours);
- info: reported by tools, not asserted (the reason is in each pair's note).

A pair is asserted in both themes unless its `themes` say otherwise. Many pairs also have
floors under the display-chain models of contrast.py (clip, wash, hicon, flare, APCA),
which the palette's neutral and teal roles were chosen to meet. The status colours keep
today's hue families, so they are held to WCAG alone.

A pair that fails is fixed by changing a colour in tokens.py, never by lowering its
threshold. Pure Python: tokens.py, contrast.py and shadow.py are loaded by path.

The light theme's structure changed in v2.1.0, so its surface steps changed contract.
Palette B met S1-S4 with a grey page (#DADDE2, L* 88), which the owner rejected on the lab
monitor as dated, and chose Fluent 2 / WinUI's layers instead: a near-white page (the base
layer) under white tab panes (the content layer) and white cards. A white card on a
near-white page is a tint step of 1.05:1, and no near-white step survives a monitor that
clips the HDMI signal (it shows every channel of 235 or more as 255), so no light colour
can meet S1-S3 without the grey page. In light a card's, a pane's and a box's edge is its
stroke instead, held to the line floors on every display model (D1, D2, D1p: 1.5:1, 1.3
clipped, 1.4 washed out). So S1-S3 stay asserted in dark, where tint steps still carry the
structure, and are reported in light (S1i-S3i), each note naming what replaced it. S4 is
reported in both themes: unselected tabs lie flat on the page in both (WinUI's TabView),
and the separator between two of them (D3), the selected tab's stroke and its bar (D1p,
M1p) mark them.

The card shadows (tokens.SHADOWS) have a contract of their own, below the pairs: the first
pixel row under a card must read as a shadow on every display model (E1), and the row
beside it as a halo on a correct display (E2).
"""

from __future__ import annotations

import importlib.util
import math
import re
from pathlib import Path
from typing import NamedTuple, Optional

import pytest

STYLE_DIR = Path(__file__).resolve().parents[2] / "ui" / "style"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"rrr_style_{name}", STYLE_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tokens = _load("tokens")
contrast = _load("contrast")
shadow = _load("shadow")

KINDS = ("text", "nontext", "step", "line", "cue", "info")


class Pair(NamedTuple):
    id: str
    fg: str
    bg: str
    kind: str
    need: float
    why: str
    robust: Optional[dict] = None  # display-model floors, both themes unless robust_dark
    need_dark: Optional[float] = None
    robust_dark: Optional[dict] = None
    themes: tuple = ("light", "dark")  # the themes it is asserted in (info: reported only)

    def threshold(self, theme):
        return self.need_dark if theme == "dark" and self.need_dark is not None else self.need

    def models(self, theme):
        if theme == "dark" and self.robust_dark is not None:
            return self.robust_dark
        return self.robust or {}


# Display-model floors, as the palette was designed (contrast.py has the models)
TEXT_ROBUST = {"clip": 4.5, "wash": 4.5}
MARK_ROBUST = {"clip": 3, "wash": 3}
CARD_STEP = {"clip": 1.15, "wash": 1.25, "hicon": 1.15, "apca": 15}
CARD_STEP_DARK = {"clip": 1.15, "wash": 1.15}
LINE_ROBUST = {"clip": 1.3, "wash": 1.4}


def fusion_frame(theme):
    """The frame Fusion draws round a control no stylesheet rule styles (a QDateTimeEdit):
    its palette's Window, bg.page, made darker(140), i.e. each channel times 100/140."""
    channels = contrast._rgb(tokens.value("bg.page", theme))
    return "#" + "".join(f"{round(c * 100 / 140):02X}" for c in channels)


# Colours Qt derives from a token where no rule reaches, named like roles for the pairs below
DERIVED = {"qt.fusion-frame": fusion_frame}


def colour(role, theme):
    """A role's colour in `theme`: a token, or a colour Qt derives from one (DERIVED)."""
    return DERIVED[role](theme) if role in DERIVED else tokens.value(role, theme)


def _text_on(pid, fg, backgrounds, need, why, robust=TEXT_ROBUST):
    return [Pair(f"{pid}:{bg}", fg, bg, "text", need, why, robust) for bg in backgrounds]


# fmt: off
PAIRS = [
    # ---- Surfaces: a step in dark; in light the edges are strokes (see the docstring) ---
    Pair("S1", "bg.surface", "bg.page", "step", 1.30,
         "A card, group box, table or list on the page", CARD_STEP, 1.25, CARD_STEP_DARK,
         themes=("dark",)),
    Pair("S2", "bg.field", "bg.page", "step", 1.30,
         "An input placed straight on the page", CARD_STEP, 1.25, CARD_STEP_DARK,
         themes=("dark",)),
    Pair("S3", "bg.inset", "bg.surface", "step", 1.30,
         "A nested group box, the table header band, a relay number or the closed priming "
         "status inside a card", CARD_STEP, 1.25, CARD_STEP_DARK, themes=("dark",)),
    Pair("S1i", "bg.surface", "bg.page", "info", 1.30,
         "Light: a white card on the near-white page, a tint hint only (1.00 clipped). Its "
         "edge is its outline (D1, D2)"),
    Pair("S2i", "bg.field", "bg.page", "info", 1.30,
         "Light: an input on a dialog's page: its 3:1 boundary identifies it (N2)"),
    Pair("S3i", "bg.inset", "bg.surface", "info", 1.30,
         "Light: a well inside a card is a tint hint: it keeps its outline (D5) or its words"),
    Pair("S4", "bg.rail", "bg.page", "info", 1.20,
         "Unselected tabs are flat on the base layer in both themes (WinUI's TabView): the "
         "separator between them is their boundary (D3), and the selected tab's stroke and "
         "bar mark it (D1p, M1p)"),
    Pair("S5", "bg.track", "bg.surface", "step", 1.30,
         "A tracker bar's groove on its card (a slider's too)",
         {"clip": 1.15, "wash": 1.25}, 1.25, {"clip": 1.15, "wash": 1.15}),
    Pair("D1", "border.subtle", "bg.page", "line", 1.5,
         "A card, group box, table or tab-pane outline, outside edge; the outline of a "
         "progress bar or the wizard log on the page (I12, I13); the login prompt's edge",
         LINE_ROBUST),
    Pair("D1p", "border.subtle", "bg.pane", "line", 1.5,
         "A card, group box or table outline on a tab pane; the selected tab's stroke "
         "against its pane", LINE_ROBUST),
    Pair("D2", "border.subtle", "bg.surface", "line", 1.5,
         "The same outline, inside edge", LINE_ROBUST),
    Pair("D3", "border.subtle", "bg.rail", "line", 1.2,
         "The separator between two unselected tabs, on their flat fill", {"clip": 1.15}, 1.5,
         {"clip": 1.3}),
    Pair("D4", "border.divider", "bg.surface", "line", 1.5,
         "Table grid lines and row rules, separators", {"clip": 1.3}),
    Pair("D5", "border.subtle", "bg.inset", "line", 1.5,
         "A nested group box's outline on its own fill", LINE_ROBUST),
    Pair("D6", "warning.indicator", "bg.page", "line", 1.5,
         "The edge of the schedule wizard's limit banner against the page"),
    # ---- Supplemental fills: hover and zebra rows ----------------------------------
    Pair("C1", "bg.hover", "bg.surface", "cue", 1.10,
         "A row, item or button under the pointer, on a card"),
    Pair("C2", "bg.hover", "bg.alt", "cue", 1.08,
         "A zebra row under the pointer: hover had the zebra colour in the dark draft"),
    Pair("C3", "bg.alt", "bg.surface", "cue", 1.05,
         "Zebra rows: an alternate row against a plain one"),
    Pair("C4", "danger.tint.strong", "danger.tint", "cue", 1.10,
         "The Schedules hub's Cancel under the pointer, and its edge, against its tint"),
    # A tracker bar writes its value inside it, in one colour over the fill and the groove:
    # with these grooves, no fill is 3:1 from its groove and 4.5:1 from that text. The
    # value is the text (and the volume under the bar), so the fill is held to a step.
    Pair("C5", "progress.fill", "bg.track", "cue", 1.25,
         "A tracker bar's fill against its groove, while a delivery runs"),
    Pair("C6", "progress.fill.complete", "success.tint", "cue", 1.25,
         "The same, Complete"),
    Pair("C7", "progress.fill.failed", "danger.tint", "cue", 1.25,
         "The same, Failed"),
    Pair("C8", "bg.highlight", "bg.surface", "cue", 1.20,
         "A Help search hit against the page it marks (the hit's hue helps it too)"),
    # ---- Control boundaries (WCAG 1.4.11) ------------------------------------------
    Pair("N1", "border.control", "bg.surface", "nontext", 3,
         "An input, button, checkbox or radio ring, scrollbar handle on a card",
         {"clip": 3, "wash": 3, "flare10": 3}, robust_dark=MARK_ROBUST),
    Pair("N1b", "border.control", "bg.surface", "nontext", 4.5,
         "A 1px control boundary on a white card: 4.5:1 below 3px (W3C low-vision draft)",
         None, 3),
    Pair("N2", "border.control", "bg.page", "nontext", 3,
         "The same controls on the page; page-level scrollbars", MARK_ROBUST),
    Pair("N2p", "border.control", "bg.pane", "nontext", 3,
         "The same controls straight on a tab pane", MARK_ROBUST),
    Pair("N3", "border.control", "bg.inset", "nontext", 3,
         "The same controls inside a nested group box", MARK_ROBUST),
    Pair("N4", "border.control", "bg.field", "nontext", 3,
         "An input's border against its own fill", MARK_ROBUST),
    Pair("N5", "border.control", "bg.alt", "nontext", 3,
         "A button in a zebra row (the Calibration table)"),
    Pair("N6", "border.control.hover", "bg.surface", "nontext", 3,
         "A control's boundary under the pointer, on a card", {"clip": 3}),
    Pair("N7", "border.control.hover", "bg.hover", "nontext", 3,
         "A hovered button's boundary against its own hover fill"),
    Pair("N8", "border.control.hover", "bg.page", "nontext", 3,
         "A hovered control on the page; a schedule card's border under the pointer"),
    Pair("N9", "border.control", "bg.hover", "nontext", 3,
         "An unchecked checkbox on a schedule card under the pointer (select mode)",
         MARK_ROBUST),
    # ---- State and value marks (WCAG 1.4.11) ---------------------------------------
    Pair("M1", "accent.indicator", "bg.page", "nontext", 3,
         "The selected tab's 3px bar against the tab strip; a progress chunk on the page; "
         "the cage valve's dot in the Cages tab's legend", MARK_ROBUST),
    Pair("M1p", "accent.indicator", "bg.pane", "nontext", 3,
         "The selected tab's 3px bar against its pane", MARK_ROBUST),
    Pair("M2", "accent.indicator", "bg.rail", "nontext", 3,
         "The selected tab's bar where it meets an unselected tab", {"clip": 3}),
    Pair("M3", "accent.indicator", "bg.surface", "nontext", 3,
         "A progress chunk, slider, status dot, terminal stripe or selected-terminal border "
         "on a card", MARK_ROBUST),
    Pair("M4", "accent.indicator", "bg.track", "nontext", 3,
         "The progress chunk or slider fill against its groove", MARK_ROBUST),
    Pair("M5", "accent.indicator", "accent.tint", "nontext", 3,
         "A selected terminal's, a drop target's or a checked card's border on its tint; the "
         "current step's ring", MARK_ROBUST),
    Pair("M6", "bg.selected", "bg.surface", "nontext", 3,
         "A selected row, item or menu entry against unselected ones", MARK_ROBUST),
    Pair("M7", "bg.selected", "bg.alt", "nontext", 3,
         "A selected row next to a zebra row", MARK_ROBUST),
    Pair("M8", "accent.fill", "bg.surface", "nontext", 3,
         "A checked checkbox or radio on a card", MARK_ROBUST),
    Pair("M9", "accent.fill", "bg.page", "nontext", 3,
         "A checked checkbox or radio on the page", MARK_ROBUST),
    Pair("M12", "accent.fill", "accent.tint", "nontext", 3,
         "The checked checkbox of a selected schedule card", MARK_ROBUST),
    Pair("M13", "text.on-accent", "accent.fill.pressed", "nontext", 3,
         "The splash screen's progress chunk against its groove", MARK_ROBUST),
    Pair("M10", "warning.indicator.selected", "bg.surface", "nontext", 3,
         "A selected master terminal's border, against the card"),
    Pair("M11", "warning.indicator.selected", "warning.tint", "nontext", 3,
         "A selected master terminal's border, against its own fill"),
    Pair("M14", "warning.indicator.status-dot", "bg.page", "nontext", 3,
         "The master valve's dot in the Cages tab's legend, on the page"),
    Pair("M15", "warning.indicator.status-dot", "warning.tint.master-terminal", "nontext", 3,
         "The master terminal's dot"),
    Pair("M16", "warning.indicator.status-dot", "warning.tint", "nontext", 3,
         "The master terminal's dot, hovered or selected"),
    Pair("F1", "focus.ring", "bg.field", "nontext", 3,
         "The 2px focus border of an input or button against the control's fill",
         MARK_ROBUST),
    Pair("F2", "focus.ring", "bg.surface", "nontext", 3,
         "The focus border against the card around the control", MARK_ROBUST),
    Pair("F3", "focus.ring", "bg.page", "nontext", 3,
         "The focus border against the page around the control", MARK_ROBUST),
    Pair("F3p", "focus.ring", "bg.pane", "nontext", 3,
         "The focus border against a tab pane around the control", MARK_ROBUST),
    Pair("F4", "focus.ring", "bg.inset", "nontext", 3,
         "The focus border inside a nested group box", MARK_ROBUST),
    Pair("F5", "focus.ring", "bg.hover", "nontext", 3,
         "The cage-name editor's edge on its relay terminal under the pointer", MARK_ROBUST),
    Pair("F6", "focus.ring", "accent.tint", "nontext", 3,
         "The cage-name editor's edge on a selected relay terminal", MARK_ROBUST),
    # ---- Text (WCAG 1.4.3) ---------------------------------------------------------
    *_text_on("T1", "text.primary",
              ["bg.page", "bg.surface", "bg.field", "bg.inset", "bg.alt", "bg.hover",
               "bg.pressed", "bg.rail.hover", "accent.tint", "bg.track"], 7,
              "Body text, values, titles, typed input; the selected tab's label; the value "
              "in a tracker bar, over its groove; a calendar popup's month and year, on its "
              "inset navigation bar, and its weekday row (7:1 target)"),
    *_text_on("T1p", "text.primary", ["bg.pane"], 7,
              "Body text, titles and labels straight on a tab pane; the selected tab's label "
              "(7:1 target)"),
    *_text_on("T2p", "text.secondary", ["bg.pane"], 7,
              "Help text, form labels and subtitles on a tab pane (7:1 target)"),
    *_text_on("T3p", "text.muted", ["bg.pane"], 4.5, "Captions and hints on a tab pane"),
    *_text_on("T4p", "text.accent", ["bg.pane"], 4.5, "Teal text on a tab pane"),
    *_text_on("T1h", "text.primary", ["success.tint", "danger.tint", "bg.highlight",
                                      "warning.tint"], 4.5,
              "Text inside a Help tip or warning; a Help search hit; the ⚠ of the schedule "
              "wizard's limit banner"),
    *_text_on("T2", "text.secondary", ["bg.page", "bg.surface", "bg.field", "bg.inset",
                                       "bg.alt"], 7,
              "Subtitles, help text, form labels, table headers, the combo arrow, secondary "
              "words in a zebra row (7:1 target)"),
    *_text_on("T2r", "text.secondary", ["bg.rail", "bg.hover", "accent.tint", "bg.highlight"],
              4.5,
              "An unselected tab's label; a card description in a hovered or checked card; "
              "Help's related topics under a search hit"),
    *_text_on("T3", "text.muted", ["bg.page", "bg.surface", "bg.field", "bg.inset",
                                   "bg.hover", "accent.tint", "bg.alt"], 4.5,
              "Captions, placeholders, column headers, pending steps, an unassigned relay; "
              "a schedule card's hint, on a selected card and on its drag pixmap too; the "
              "dashes of an uncalibrated row in the Calibration table, on a zebra row too"),
    *_text_on("T4", "text.accent", ["bg.page", "bg.surface", "bg.hover", "accent.tint",
                                    "bg.highlight"], 4.5,
              "Teal text: the info banner, elapsed time, the current and completed steps, "
              "card icons and badges, a schedule card's date (hovered or selected too) and "
              "its drag pixmap, Help headings (under a search hit too)"),
    *_text_on("T5", "text.link", ["bg.page", "bg.surface", "accent.tint", "success.tint",
                                  "danger.tint", "bg.highlight"], 4.5,
              "Links: Show password, and Help links, in callouts and under a search hit too"),
    *_text_on("T6", "text.on-accent", ["accent.fill", "accent.fill.hover",
                                       "accent.fill.pressed", "bg.selected"], 4.5,
              "Labels on teal fills: buttons, badges, the open status, selected items and "
              "text; the splash screen's title and status on both ends of its gradient"),
    Pair("T7", "text.tooltip", "bg.tooltip", "text", 7, "Tooltips", TEXT_ROBUST),
    # Status colours: today's hue families, held to WCAG
    *_text_on("T8", "text.on-danger", ["danger.fill", "danger.fill.hover",
                                       "danger.fill.pressed"], 4.5,
              "The danger button's label (CLOSE ALL RELAYS, Log Out)", robust=None),
    Pair("T9", "danger.on-alert", "danger.alert", "text", 4.5,
         "The Animals tab's bright red cell: bold white on red, as the owner asked"),
    Pair("T10s", "success.on-tint", "success.tint", "text", 4.5, "A success banner"),
    Pair("T10w", "warning.on-tint", "warning.tint", "text", 4.5, "A warning banner"),
    Pair("T10d", "danger.on-tint", "danger.tint", "text", 4.5,
         "An error banner; Cancel in the Schedules hub's select mode"),
    Pair("T10dh", "danger.on-tint", "danger.tint.strong", "text", 4.5,
         "That Cancel under the pointer"),
    Pair("T10i", "info.on-tint", "info.tint", "text", 4.5, "An info banner"),
    Pair("T11", "warning.on-tint.master-terminal", "warning.tint.master-terminal", "text", 4.5,
         "MASTER SOLENOID on the master terminal"),
    Pair("T11h", "warning.on-tint.master-terminal", "warning.tint", "text", 4.5,
         "MASTER SOLENOID on a hovered or selected master terminal"),
    # The delivery modes' badges (Staggered's is text.on-accent on accent.fill, T6)
    Pair("T12", "text.on-instant", "instant.fill", "text", 4.5,
         "Instant on a schedule card's mode badge"),
    # The progress tracker: the value in a bar where the fill passes under it (over a
    # complete or failed bar's groove: T1h), and the status words on a card
    *_text_on("T13", "text.primary", ["progress.fill", "progress.fill.complete",
                                      "progress.fill.failed"], 4.5,
              "The value written in a tracker bar, over its fill"),
    Pair("T14w", "warning.text", "bg.surface", "text", 4.5,
         "Paused on a progress card; Stale and an acceptable CV in the Calibration table; "
         "a failed Slack message"),
    Pair("T14s", "success.text", "bg.surface", "text", 4.5,
         "Complete on a progress card; [OK] and a good CV in the Calibration table; a "
         "delivered Slack message"),
    Pair("T14d", "danger.text", "bg.surface", "text", 4.5,
         "Failed on a progress card; Invalid, Not Calibrated and a poor CV in the "
         "Calibration table"),
    # The Calibration table's status words on a zebra row and on a row under the pointer
    # (a selected row writes them in text.on-accent, T6)
    *_text_on("T15s", "success.text", ["bg.alt", "bg.hover"], 4.5,
              "[OK] and a good CV in the Calibration table", robust=None),
    *_text_on("T15w", "warning.text", ["bg.alt", "bg.hover"], 4.5,
              "Stale and an acceptable CV in the Calibration table", robust=None),
    *_text_on("T15d", "danger.text", ["bg.alt", "bg.hover"], 4.5,
              "Invalid, Not Calibrated and a poor CV in the Calibration table", robust=None),
    # A calendar popup's weekend: Qt's red, a shade that reads, held to WCAG like the words
    *_text_on("T16", "text.weekend", ["bg.surface", "bg.alt"], 4.5,
              "A calendar popup's weekend dates, and their names in the weekday row",
              robust=None),
    # ---- Reported, not asserted ----------------------------------------------------
    Pair("I1", "text.disabled", "bg.disabled", "info", 3,
         "Disabled labels: WCAG exempts a control that is really disabled"),
    Pair("I2", "text.link", "text.primary", "info", 3,
         "Links against body text: under 3:1, so Help links are underlined"),
    Pair("I3", "focus.ring.primary", "accent.fill", "info", 3,
         "A focused primary button's border against its fill: the focus-ring follow-up"),
    Pair("I4", "focus.ring", "border.control", "info", 3,
         "Focus change over a control's own border (WCAG 2.4.13, AAA): focus follow-up"),
    Pair("I5", "danger.fill", "bg.surface", "info", 3,
         "A danger button against a card: a labelled button needs no 3:1 boundary"),
    Pair("I6", "danger.alert", "bg.alt", "info", 3,
         "The red cell against a zebra row: its status word carries the meaning"),
    Pair("I7", "warning.indicator", "warning.tint", "info", 3,
         "A warning banner's stripe: decorative, the text carries the warning"),
    Pair("I9", "text.secondary", "text.muted", "info", 1.45,
         "Secondary against muted text (the light step was 1.33:1 in the draft)"),
    Pair("I10", "border.divider", "bg.alt", "info", 1.5,
         "Grid lines on a zebra row"),
    Pair("I11", "danger.tint.strong", "bg.page", "info", 3,
         "The edge of the Schedules hub's Cancel against the page: a labelled button needs "
         "no 3:1 boundary"),
    Pair("I12", "bg.track", "bg.page", "info", 1.25,
         "A progress bar's groove on the page (the calibration wizard's run, the Stopping "
         "dialog): a step darker than the page in light, the same colour in dark; the bar's "
         "outline (D1) shows its length"),
    Pair("I13", "bg.inset", "bg.page", "info", 1.25,
         "The calibration wizard's log on its dialog's page: the same colour; its outline "
         "(D1) shows its edge"),
    # A known failure, left for a follow-up: QDateTimeEdit is not in the input rule (adding
    # it changes the field's drop-down and size), so Fusion draws its frame
    Pair("I14", "qt.fusion-frame", "bg.surface", "info", 3,
         "A date field's frame on a card (wizard step 3, the schedule edit dialog)"),
    Pair("I15", "qt.fusion-frame", "bg.page", "info", 3,
         "A date field's frame on a dialog's page (Add and Edit Animal)"),
]
# fmt: on

ASSERTED = [p for p in PAIRS if p.kind != "info"]


def measure(model, fg, bg):
    """A pair's ratio under one model of contrast.py ('nominal', 'clip', 'wash', 'hicon',
    'flare10', or 'apca' for the smaller |Lc| of the two polarities)."""
    if model == "apca":
        return contrast.apca_step(fg, bg)
    if model == "flare10":
        return contrast.contrast_ratio_flare(fg, bg, 0.10)
    return contrast.contrast_ratio(fg, bg, model)


def failures(pair, theme, value=colour):
    """What `pair` misses in `theme`: [] when it meets every floor.

    `value(role, theme)` gives a role's colour; colour() unless a test passes another.
    """
    fg, bg = value(pair.fg, theme), value(pair.bg, theme)
    found = []
    nominal = contrast.contrast_ratio(fg, bg)
    if nominal < pair.threshold(theme):
        found.append(f"{nominal:.3f} < {pair.threshold(theme)}")
    for model, minimum in pair.models(theme).items():
        if model == "apca" and theme == "dark":
            continue  # APCA's soft black clamp reads every dark surface step as Lc 0
        got = measure(model, fg, bg)
        if got < minimum:
            found.append(f"{model} {got:.3f} < {minimum}")
    return found


# ---- The formula ---------------------------------------------------------------------


# Ratios W3C prints, as it prints them: mostly cut to the digits shown (3.657 is printed 3.6,
# 9.398 is 9.39, 15.609 is 15), once rounded (1.185 is 1.2)
W3C_RATIOS = [
    # ACT rule afw4f7, "Text has minimum contrast"
    ("#333333", "#FFFFFF", "12.6"),  # Passed Example 1
    ("#000000", "#666666", "3.6"),  # Passed Example 5
    ("#0000EE", "#FFFFFF", "9.39"),  # Passed Example 10
    ("#AAAAAA", "#FFFFFF", "2.3"),  # Failed Example 1
    ("#777777", "#EEEEEE", "3.85"),  # Failed Example 9
    # Understanding WCAG 2.2, Success Criterion 1.4.11 "Non-text Contrast"
    ("#949494", "#FFFFFF", "3"),  # Figure 1
    ("#E5E5E5", "#6221EA", "5.6"),  # Figure 4
    ("#FFF000", "#FFFFFF", "1.2"),  # Figure 7
    ("#CCCCCC", "#FFFFFF", "1.6"),  # Figure 33
    ("#FFFFFF", "#6E747B", "4.7"),  # Figure 36
    ("#000000", "#DEDEDE", "15"),  # Figure 40
    ("#9D9D9D", "#FFFFFF", "2.7"),  # Figure 42
]


@pytest.mark.parametrize("fg, bg, printed", W3C_RATIOS)
def test_the_formula_gives_the_ratios_w3c_prints(fg, bg, printed):
    ratio = contrast.contrast_ratio(fg, bg)
    digits = len(printed.partition(".")[2])
    cut = math.floor(ratio * 10**digits) / 10**digits
    assert float(printed) in (cut, round(ratio, digits)), f"{fg} on {bg}: {ratio:.4f}"


def test_the_formula_at_its_ends():
    assert contrast.contrast_ratio("#FFFFFF", "#000000") == pytest.approx(21.0)
    assert contrast.contrast_ratio("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert contrast.contrast_ratio("#FFFFFF", "#FFFFFF") == pytest.approx(1.0)
    assert contrast.contrast_ratio("#FFF", "#000") == pytest.approx(21.0)
    # The lightest grey that passes 4.5:1 on white (#777777, 4.478, fails: see below)
    assert round(contrast.contrast_ratio("#767676", "#FFFFFF"), 2) == 4.54


def test_a_ratio_is_never_rounded():
    # #777777 on white shows as "4.5:1" to one decimal, but is 4.478: it fails 4.5
    ratio = contrast.contrast_ratio("#777777", "#FFFFFF")
    assert round(ratio, 1) == 4.5 and ratio < 4.5
    grey = Pair("x", "text.primary", "bg.surface", "text", 4.5, "")
    colours = {"text.primary": "#777777", "bg.surface": "#FFFFFF"}
    assert failures(grey, "light", lambda role, theme: colours[role]) == ["4.478 < 4.5"]
    colours["text.primary"] = "#767676"  # 4.54
    assert failures(grey, "light", lambda role, theme: colours[role]) == []


def test_apca_gives_its_reference_values():
    # APCA-W3 0.0.98G-4g README
    assert round(contrast.apca_lc("#888888", "#FFFFFF"), 2) == 63.06
    assert round(contrast.apca_lc("#FFFFFF", "#888888"), 2) == -68.54
    assert round(contrast.apca_lc("#000000", "#AAAAAA"), 2) == 58.15
    assert round(contrast.apca_lc("#AAAAAA", "#000000"), 2) == -56.24
    assert contrast.apca_step("#888888", "#FFFFFF") == pytest.approx(63.06, abs=0.005)


# CIEDE2000's reference data: Sharma, Wu and Dalal, "The CIEDE2000 color-difference formula",
# Color Research and Application 30 (2005), table 1: (L*, a*, b*) twice, then the difference
SHARMA_2005 = [
    ((50.0000, 2.6772, -79.7751), (50.0000, 0.0000, -82.7485), 2.0425),
    ((50.0000, 3.1571, -77.2803), (50.0000, 0.0000, -82.7485), 2.8615),
    ((50.0000, 2.8361, -74.0200), (50.0000, 0.0000, -82.7485), 3.4412),
    ((50.0000, -1.3802, -84.2814), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, -1.1848, -84.8006), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, -0.9009, -85.5211), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, 0.0000, 0.0000), (50.0000, -1.0000, 2.0000), 2.3669),
    ((50.0000, -1.0000, 2.0000), (50.0000, 0.0000, 0.0000), 2.3669),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0009), 7.1792),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0010), 7.1792),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0011), 7.2195),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0012), 7.2195),
    ((50.0000, -0.0010, 2.4900), (50.0000, 0.0009, -2.4900), 4.8045),
    ((50.0000, -0.0010, 2.4900), (50.0000, 0.0010, -2.4900), 4.8045),
    ((50.0000, -0.0010, 2.4900), (50.0000, 0.0011, -2.4900), 4.7461),
    ((50.0000, 2.5000, 0.0000), (50.0000, 0.0000, -2.5000), 4.3065),
    ((50.0000, 2.5000, 0.0000), (73.0000, 25.0000, -18.0000), 27.1492),
    ((50.0000, 2.5000, 0.0000), (61.0000, -5.0000, 29.0000), 22.8977),
    ((50.0000, 2.5000, 0.0000), (56.0000, -27.0000, -3.0000), 31.9030),
    ((50.0000, 2.5000, 0.0000), (58.0000, 24.0000, 15.0000), 19.4535),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.1736, 0.5854), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.2972, 0.0000), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 1.8634, 0.5757), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.2592, 0.3350), 1.0000),
    ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644),
    ((63.0109, -31.0961, -5.8663), (62.8187, -29.7946, -4.0864), 1.2630),
    ((61.2901, 3.7196, -5.3901), (61.4292, 2.2480, -4.9620), 1.8731),
    ((35.0831, -44.1164, 3.7933), (35.0232, -40.0716, 1.5901), 1.8645),
    ((22.7233, 20.0904, -46.6940), (23.0331, 14.9730, -42.5619), 2.0373),
    ((36.4612, 47.8580, 18.3852), (36.2715, 50.5065, 21.2231), 1.4146),
    ((90.8027, -2.0831, 1.4410), (91.1528, -1.6435, 0.0447), 1.4441),
    ((90.9257, -0.5406, -0.9208), (88.6381, -0.8985, -0.7239), 1.5381),
    ((6.7747, -0.2908, -2.4247), (5.8714, -0.0985, -2.2286), 0.6377),
    ((2.0776, 0.0795, -1.1350), (0.9033, -0.0636, -0.5514), 0.9082),
]


@pytest.mark.parametrize("lab1, lab2, difference", SHARMA_2005)
def test_ciede2000_gives_its_reference_data(lab1, lab2, difference):
    assert round(contrast.delta_e_2000_lab(lab1, lab2), 4) == difference
    assert round(contrast.delta_e_2000_lab(lab2, lab1), 4) == difference


def test_lab_of_srgb_colours():
    for got, want in zip(contrast.lab("#FFFFFF"), (100.0, 0.0, 0.0)):
        assert got == pytest.approx(want, abs=0.02)
    assert contrast.lab("#000000") == pytest.approx((0.0, 0.0, 0.0))
    # sRGB red (Lindbloom: 53.2408, 80.0925, 67.2032; the IEC matrix here is rounded)
    for got, want in zip(contrast.lab("#FF0000"), (53.2408, 80.0925, 67.2032)):
        assert got == pytest.approx(want, abs=0.03)
    assert contrast.delta_e_2000("#C89600", "#C89600") == 0.0


def test_the_display_models():
    clip, wash, hicon = (contrast.MODELS[m] for m in ("clip", "wash", "hicon"))
    assert clip(235) == 255 and clip(16) == 0 and clip(255) == 255 and clip(0) == 0
    assert wash(0) == 16 and wash(255) == 235
    assert hicon(240) == 255 and hicon(0) == 0
    # Every light grey from #EB (235) up clips to white: the old page step vanished
    assert contrast.contrast_ratio("#EBEBEB", "#FFFFFF", "clip") == pytest.approx(1.0)
    assert contrast.contrast_ratio("#F8FAFB", "#FFFFFF", "clip") == pytest.approx(1.0)
    # A higher flare term lowers every ratio
    assert contrast.contrast_ratio_flare("#767676", "#FFFFFF") < contrast.contrast_ratio(
        "#767676", "#FFFFFF"
    )
    with pytest.raises(ValueError):
        contrast.contrast_ratio("#12345", "#FFFFFF")


# ---- The pairs -----------------------------------------------------------------------


def test_every_pair_names_real_tokens_and_a_known_kind():
    named = {n for p in PAIRS for n in (p.fg, p.bg)}
    known = set(tokens.TOKENS) | set(DERIVED)
    assert named <= known, sorted(named - known)
    assert {p.kind for p in PAIRS} <= set(KINDS)
    ids = [p.id for p in PAIRS]
    assert len(ids) == len(set(ids)), "pair ids must be unique"
    for pair in PAIRS:
        assert pair.themes and set(pair.themes) <= set(tokens.THEMES), pair.id
        for theme in tokens.THEMES:
            assert set(pair.models(theme)) <= {"clip", "wash", "hicon", "flare10", "apca"}


def _roles_the_template_writes_in():
    """Every role of a `color: ${role}` declaration in the template: text, or a glyph."""
    template = (STYLE_DIR / "app.qss.tmpl").read_text(encoding="utf-8")
    return set(re.findall(r"(?<![\w-])color\s*:\s*\$\{([^}]+)\}", template))


def test_every_text_role_has_its_pairs():
    """A role that colours text is checked against at least one background, and so is
    every role the template writes in: a glyph such as a status dot is a mark, so its pair
    may be text or nontext."""
    text_roles = {name for name in tokens.TOKENS if name.startswith("text.")}
    text_roles |= {name for name in tokens.TOKENS if ".on-" in name or name.endswith(".text")}
    checked = {p.fg for p in ASSERTED if p.kind == "text"}
    unchecked = text_roles - checked - {"text.disabled"}  # exempt; reported as I1
    assert not unchecked, f"text roles with no asserted pair: {sorted(unchecked)}"

    written = _roles_the_template_writes_in()
    assert {"text.primary", "accent.indicator"} <= written, "the template's color: rules"
    marked = {p.fg for p in ASSERTED if p.kind in ("text", "nontext")}
    unmarked = written - text_roles - marked
    assert not unmarked, f"roles the template writes in with no asserted pair: {sorted(unmarked)}"


CHECKS = [(pair, theme) for pair in ASSERTED for theme in pair.themes]


@pytest.mark.parametrize(
    ("pair", "theme"), CHECKS, ids=[f"{pair.id}-{theme}" for pair, theme in CHECKS]
)
def test_pair_meets_its_threshold(pair, theme):
    missed = failures(pair, theme)
    fg, bg = colour(pair.fg, theme), colour(pair.bg, theme)
    assert not missed, (
        f"{pair.id} ({pair.kind}) {pair.fg} {fg} on {pair.bg} {bg}, {theme}: {missed}. "
        f"{pair.why}. Change the colour in tokens.py, not the threshold."
    )


# Status words that share a column and say different things: [OK] or a good CV, Stale or an
# acceptable CV, Invalid or a poor CV in the Calibration table; Complete, Paused and Failed.
STATUS_WORDS = ("success.text", "warning.text", "danger.text")
# CIEDE2000 between any two. v2.0.0's tracker words, Paused and Failed, were 24.8 apart and
# its Calibration table's mustard and red 40.7; the brown and red of the first palette B
# draft were 13.2, and looked alike.
STATUS_WORDS_APART = 25


@pytest.mark.parametrize("theme", tokens.THEMES)
def test_status_words_differ_in_colour_not_only_in_their_words(theme):
    """The words carry the meaning, and their colour is the cue at a glance: two status
    colours that look alike lose it, whatever their contrast with the row."""
    for i, first in enumerate(STATUS_WORDS):
        for second in STATUS_WORDS[i + 1 :]:
            apart = contrast.delta_e_2000(tokens.value(first, theme), tokens.value(second, theme))
            assert apart >= STATUS_WORDS_APART, f"{first} and {second}, {theme}: {apart:.1f}"


def test_the_judges_fixes_hold():
    """The palette's review asked for these; they are not WCAG, so they are kept here."""
    # Hover had the zebra colour in the dark draft, so a zebra row did not change under
    # the pointer: C2 asserts the step, and the colours must differ outright.
    for theme in tokens.THEMES:
        assert tokens.value("bg.hover", theme) != tokens.value("bg.alt", theme), theme
    # Secondary and muted text were 1.33:1 apart in the light draft
    light = contrast.contrast_ratio(
        tokens.value("text.secondary", "light"), tokens.value("text.muted", "light")
    )
    assert light >= 1.45, f"light secondary vs muted text {light:.3f}"


# ---- The shadow contract (E1, E2) -----------------------------------------------------------
# tokens.SHADOWS holds CSS box-shadow recipes (shadow.py has the geometry), ELEVATION names
# one per theme. The first pixel row past a card's edge is what reads as its shadow: E1 holds
# the bottom row to the shadow band of the display models (a step that survives a clipping
# HDMI chain), E2 the side row to a visible halo on a correct display. Every recipe is held
# to them, as the lab monitor's A/B may give a card any of them (RRR_SHADOW).

SHADOW_GROUNDS = ("bg.pane", "bg.page")  # a card on a tab pane, or straight on the page
E1_BOTTOM = {"nominal": 1.30, "clip": 1.15, "wash": 1.25}
E2_SIDE = {"nominal": 1.20}


def _first_row(layers, edge, ground):
    background = tokens.value(ground, "light")
    pixel = shadow.over(
        background, tokens.value("shadow.ink", "light"), shadow.edge_alpha(layers, edge, 0)
    )
    return pixel, background


@pytest.mark.parametrize("name", sorted(tokens.SHADOWS))
@pytest.mark.parametrize("ground", SHADOW_GROUNDS)
def test_a_card_shadow_shows_under_the_card(name, ground):
    """E1 (bottom row) and E2 (side row) for every recipe, on a pane and on the page."""
    layers = tokens.SHADOWS[name]
    for edge, floors in (("bottom", E1_BOTTOM), ("left", E2_SIDE), ("right", E2_SIDE)):
        pixel, background = _first_row(layers, edge, ground)
        for model, floor in floors.items():
            got = contrast.contrast_ratio(pixel, background, model)
            assert got >= floor, f"{name} {edge} row on {ground}: {model} {got:.3f} < {floor}"


def test_the_elevation_table():
    """Every level names a recipe in light and none in dark: the dark theme separates its
    surfaces by tint and stroke, and a shadow barely registers on its page. Each recipe is
    a tuple of (x, y, blur, spread, alpha) layers with an alpha a shadow can have."""
    assert tokens.ELEVATION, "no elevation level"
    for level, (light, dark) in tokens.ELEVATION.items():
        assert light in tokens.SHADOWS, level
        assert dark is None, f"{level}: the dark theme paints no shadow"
    for name, layers in tokens.SHADOWS.items():
        assert layers and all(len(layer) == 5 for layer in layers), name
        assert all(0 < layer[4] <= 0.4 and layer[2] > 0 for layer in layers), name


def test_the_shadow_maths_matches_css():
    """Fluent 2's shadow4 as CSS draws it (sigma = blur / 2): 14.1 % in the first row under
    the card, 9.1 % beside it; it reaches 6, 4, 6 and 8 px (left, top, right, bottom); the
    room every card reserves is the union of the recipes' reach."""
    layers = tokens.SHADOWS["fluent.shadow4"]
    assert shadow.edge_alpha(layers, "bottom", 0) == pytest.approx(0.1413, abs=0.0005)
    assert shadow.edge_alpha(layers, "left", 0) == pytest.approx(0.0911, abs=0.0005)
    assert shadow.extent(layers) == shadow.Extent(6, 4, 6, 8)
    room = shadow.reserved(tokens)
    for layers in tokens.SHADOWS.values():
        reach = shadow.extent(layers)
        assert all(getattr(room, side) >= getattr(reach, side) for side in reach._fields)
    assert shadow.over("#FFFFFF", "#000000", 0.1413) == "#DBDBDB"
