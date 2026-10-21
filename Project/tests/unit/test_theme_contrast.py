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

Many pairs also have floors under the display-chain models of contrast.py (clip, wash,
hicon, flare, APCA), which the palette's neutral and teal roles were chosen to meet. The
status colours keep today's hue families, so they are held to WCAG alone.

A pair that fails is fixed by changing a colour in tokens.py, never by lowering its
threshold. Pure Python: tokens.py and contrast.py are loaded by path.
"""

from __future__ import annotations

import importlib.util
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


def _text_on(pid, fg, backgrounds, need, why, robust=TEXT_ROBUST):
    return [Pair(f"{pid}:{bg}", fg, bg, "text", need, why, robust) for bg in backgrounds]


# fmt: off
PAIRS = [
    # ---- Surfaces: palette B's grey page, white cards ------------------------------
    Pair("S1", "bg.surface", "bg.page", "step", 1.30,
         "A card, group box, table or list on the page", CARD_STEP, 1.25, CARD_STEP_DARK),
    Pair("S2", "bg.field", "bg.page", "step", 1.30,
         "An input placed straight on the page", CARD_STEP, 1.25, CARD_STEP_DARK),
    Pair("S3", "bg.inset", "bg.surface", "step", 1.30,
         "A nested group box, the table header band or the wizard log inside a card",
         CARD_STEP, 1.25, CARD_STEP_DARK),
    Pair("S4", "bg.rail", "bg.page", "step", 1.20,
         "Unselected tabs against the selected tab and its pane",
         {"clip": 1.15, "wash": 1.15}, 1.25),
    Pair("S5", "bg.track", "bg.surface", "step", 1.30,
         "A progress or slider groove on a card",
         {"clip": 1.15, "wash": 1.25}, 1.25, {"clip": 1.15, "wash": 1.15}),
    Pair("D1", "border.subtle", "bg.page", "line", 1.5,
         "A card, group box, table or tab-pane outline, outside edge", LINE_ROBUST),
    Pair("D2", "border.subtle", "bg.surface", "line", 1.5,
         "The same outline, inside edge", LINE_ROBUST),
    Pair("D3", "border.subtle", "bg.rail", "line", 1.2,
         "A tab's outline on the unselected-tab fill", {"clip": 1.15}, 1.5, {"clip": 1.3}),
    Pair("D4", "border.divider", "bg.surface", "line", 1.5,
         "Table grid lines and row rules, separators", {"clip": 1.3}),
    Pair("D5", "border.subtle", "bg.inset", "line", 1.5,
         "A nested group box's outline on its own fill", LINE_ROBUST),
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
    # ---- Control boundaries (WCAG 1.4.11) ------------------------------------------
    Pair("N1", "border.control", "bg.surface", "nontext", 3,
         "An input, button, checkbox or radio ring, scrollbar handle on a card",
         {"clip": 3, "wash": 3, "flare10": 3}, robust_dark=MARK_ROBUST),
    Pair("N1b", "border.control", "bg.surface", "nontext", 4.5,
         "A 1px control boundary on a white card: 4.5:1 below 3px (W3C low-vision draft)",
         None, 3),
    Pair("N2", "border.control", "bg.page", "nontext", 3,
         "The same controls on the page; page-level scrollbars", MARK_ROBUST),
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
         "The selected tab's 3px bar against its pane; a progress chunk on the page",
         MARK_ROBUST),
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
    Pair("M10", "warning.indicator.selected", "bg.surface", "nontext", 3,
         "A selected master terminal's border, against the card"),
    Pair("M11", "warning.indicator.selected", "warning.tint", "nontext", 3,
         "A selected master terminal's border, against its own fill"),
    Pair("F1", "focus.ring", "bg.field", "nontext", 3,
         "The 2px focus border of an input or button against the control's fill",
         MARK_ROBUST),
    Pair("F2", "focus.ring", "bg.surface", "nontext", 3,
         "The focus border against the card around the control", MARK_ROBUST),
    Pair("F3", "focus.ring", "bg.page", "nontext", 3,
         "The focus border against the page around the control", MARK_ROBUST),
    Pair("F4", "focus.ring", "bg.inset", "nontext", 3,
         "The focus border inside a nested group box", MARK_ROBUST),
    # ---- Text (WCAG 1.4.3) ---------------------------------------------------------
    *_text_on("T1", "text.primary",
              ["bg.page", "bg.surface", "bg.field", "bg.inset", "bg.alt", "bg.hover",
               "bg.pressed", "bg.rail.hover", "accent.tint", "bg.track"], 7,
              "Body text, values, titles, typed input; the selected tab's label; the value "
              "in a tracker bar, over its groove (7:1 target)"),
    *_text_on("T1h", "text.primary", ["success.tint", "danger.tint", "bg.highlight"], 4.5,
              "Text inside a Help tip or warning; a Help search hit"),
    *_text_on("T2", "text.secondary", ["bg.page", "bg.surface", "bg.field", "bg.inset",
                                       "bg.alt"], 7,
              "Subtitles, help text, form labels, table headers, the combo arrow, secondary "
              "words in a zebra row (7:1 target)"),
    *_text_on("T2r", "text.secondary", ["bg.rail", "bg.hover", "accent.tint"], 4.5,
              "An unselected tab's label; a card description in a hovered or checked card"),
    *_text_on("T3", "text.muted", ["bg.page", "bg.surface", "bg.field", "bg.inset",
                                   "bg.hover", "accent.tint", "bg.alt"], 4.5,
              "Captions, placeholders, column headers, pending steps, an unassigned relay; "
              "a schedule card's hint, on a selected card and on its drag pixmap too; the "
              "dashes of an uncalibrated row in the Calibration table, on a zebra row too"),
    *_text_on("T4", "text.accent", ["bg.page", "bg.surface", "bg.hover", "accent.tint"], 4.5,
              "Teal text: the info banner, elapsed time, the current and completed steps, "
              "card icons and badges, a schedule card's date (hovered or selected too) and "
              "its drag pixmap, Help headings"),
    *_text_on("T5", "text.link", ["bg.page", "bg.surface", "accent.tint", "success.tint",
                                  "danger.tint"], 4.5,
              "Links: Show password, and Help links, in callouts too"),
    *_text_on("T6", "text.on-accent", ["accent.fill", "accent.fill.hover",
                                       "accent.fill.pressed", "bg.selected"], 4.5,
              "Labels on teal fills: buttons, badges, the open status, selected items and text"),
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
    Pair("T11", "warning.text", "warning.tint.master-terminal", "text", 4.5,
         "MASTER SOLENOID on the master terminal"),
    Pair("T11h", "warning.text", "warning.tint", "text", 4.5,
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
    Pair("I8", "warning.indicator.status-dot", "warning.tint.master-terminal", "info", 3,
         "The master terminal's dot: decorative, MASTER SOLENOID names it"),
    Pair("I9", "text.secondary", "text.muted", "info", 1.45,
         "Secondary against muted text (the light step was 1.33:1 in the draft)"),
    Pair("I10", "border.divider", "bg.alt", "info", 1.5,
         "Grid lines on a zebra row"),
    Pair("I11", "danger.tint.strong", "bg.page", "info", 3,
         "The edge of the Schedules hub's Cancel against the page: a labelled button needs "
         "no 3:1 boundary"),
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


def failures(pair, theme, value=tokens.value):
    """What `pair` misses in `theme`: [] when it meets every floor.

    `value(role, theme)` gives a role's colour; tokens.value unless a test passes another.
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


def test_the_formula_gives_w3cs_published_ratios():
    # W3C, Understanding SC 1.4.3 and 1.4.11
    assert round(contrast.contrast_ratio("#767676", "#FFFFFF"), 2) == 4.54
    assert round(contrast.contrast_ratio("#949494", "#FFFFFF"), 2) == 3.03
    assert round(contrast.contrast_ratio("#CCCCCC", "#FFFFFF"), 2) == 1.61
    assert contrast.contrast_ratio("#FFFFFF", "#000000") == pytest.approx(21.0)
    assert contrast.contrast_ratio("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert contrast.contrast_ratio("#FFFFFF", "#FFFFFF") == pytest.approx(1.0)
    assert contrast.contrast_ratio("#FFF", "#000") == pytest.approx(21.0)


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
    assert named <= set(tokens.TOKENS), sorted(named - set(tokens.TOKENS))
    assert {p.kind for p in PAIRS} <= set(KINDS)
    ids = [p.id for p in PAIRS]
    assert len(ids) == len(set(ids)), "pair ids must be unique"
    for pair in PAIRS:
        for theme in tokens.THEMES:
            assert set(pair.models(theme)) <= {"clip", "wash", "hicon", "flare10", "apca"}


def test_every_text_role_has_its_pairs():
    """A role that colours text is checked against at least one background."""
    text_roles = {name for name in tokens.TOKENS if name.startswith("text.")}
    text_roles |= {name for name in tokens.TOKENS if ".on-" in name or name.endswith(".text")}
    checked = {p.fg for p in ASSERTED if p.kind == "text"}
    unchecked = text_roles - checked - {"text.disabled"}  # exempt; reported as I1
    assert not unchecked, f"text roles with no asserted pair: {sorted(unchecked)}"


@pytest.mark.parametrize("theme", tokens.THEMES)
@pytest.mark.parametrize("pair", ASSERTED, ids=lambda p: p.id)
def test_pair_meets_its_threshold(pair, theme):
    missed = failures(pair, theme)
    fg, bg = tokens.value(pair.fg, theme), tokens.value(pair.bg, theme)
    assert not missed, (
        f"{pair.id} ({pair.kind}) {pair.fg} {fg} on {pair.bg} {bg}, {theme}: {missed}. "
        f"{pair.why}. Change the colour in tokens.py, not the threshold."
    )


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
