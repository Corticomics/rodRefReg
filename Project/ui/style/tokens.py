"""Colour tokens of the RRR themes: role name -> (light, dark).

app.qss.tmpl names every colour by its role, as ${bg.surface}; build_qss.py renders the
template once per theme with these values into app-light.qss and app-dark.qss. A role says
what a colour is for (bg.surface: cards, tables, menus), not what it looks like, so a new
palette is a change of values here, not of the template. Two roles may hold the same
colour (bg.page and bg.inset do): they still say different things.

The light palette (v2.1.0) follows Fluent 2 and WinUI: a near-white page (the base
layer) under white tab panes (the content layer), and white cards, all outlined by one
hairline stroke; Fluent's resting shadow under the primary cards (SHADOWS and ELEVATION
below); rules between the sections inside a card, never a box in a box. The edges are
strokes, not tints, so they stay visible on a monitor that clips or washes out the Pi's HDMI
signal (contrast.py has the models). The dark theme keeps the robust-contrast palette's
values (palette B), but for its unselected tabs, flat as in light: it separates its surfaces
by tint and stroke, and paints no shadow.

Four things read the roles:
- the stylesheet template, through its ${role} placeholders;
- the QPalette StyleManager sets before the stylesheet (qt_palette.py), through QPALETTE and
  QPALETTE_DISABLED below. It colours what the stylesheet does not reach: the window, plain
  containers, placeholders, alternate rows, rich-text links, the days of a calendar popup
  (its navigation bar has a rule);
- the Help tab's HTML (Project/utils/help_content_manager.py), through HELP_HTML below;
- UI code that paints itself, which asks for a role by name when it paints: theme_colour()
  in theme.py, and theme.tone_weekend for a calendar's weekend dates (text.weekend).

Project/tests/unit/test_theme_contrast.py checks every pair of roles the UI draws together,
in both themes. A pair that fails is fixed by changing a colour here, never its threshold.

Data and one lookup, nothing else: build_qss.py, qt_palette.py, help_content_manager.py and
the tests load this file by path, without importing the ui package. After editing it, run
python3 Project/ui/style/build_qss.py and commit it with both regenerated stylesheets.
"""

from __future__ import annotations

THEMES = ("light", "dark")

# The theme RRR shows without a saved one (v2.1.0: dark; it was light). The settings'
# default is SystemController.DEFAULT_THEME, which test_dark_default.py keeps equal to it.
DEFAULT_THEME = "dark"

# name: (light, dark)
TOKENS: dict[str, tuple[str, str]] = {
    # ---- Backgrounds -------------------------------------------------------------------
    # The page, the base layer (QPalette.Window): windows and dialogs, the strip the tabs
    # stand on (unselected tabs show it), the help sidebar
    "bg.page": ("#F8FAFB", "#1F242B"),
    # The content layer: tab panes, and the selected tab that joins its pane (WinUI's two
    # layers: a lighter content layer on the base; in dark the panes keep the page's colour)
    "bg.pane": ("#FFFFFF", "#1F242B"),
    # Cards and other raised surfaces: Card, the login prompt, group boxes, tables, lists,
    # menus, the combo popup, QPushButton, an idle drop area, #MaterialCard,
    # #RelayTerminal, #InteractiveCard, #ScheduleCard (under the pointer too), the wizard's
    # step circles and Back button, the help content pane (QPalette.Button)
    "bg.surface": ("#FFFFFF", "#30373F"),
    # Editable fields, focused or not; checkbox and radio indicators; #CageNameEdit,
    # #SchedulesHubSearch (QPalette.Base)
    "bg.field": ("#FFFFFF", "#30373F"),
    # Wells inside a white surface: #WizardLog, #RelayNumber, #StatusLabel[status="closed"],
    # a calendar popup's navigation bar; inline code in Help. The page's tint, a hint only:
    # each of them keeps its outline or its words
    "bg.inset": ("#F8FAFB", "#1F242B"),
    # Unselected tabs: the page's colour in both themes, flat on the base layer as WinUI's
    # TabView draws them; a separator between two of them keeps their boundary
    "bg.rail": ("#F8FAFB", "#1F242B"),
    # An unselected tab under the pointer
    "bg.rail.hover": ("#E6E9ED", "#3A424C"),
    # Under the pointer: QPushButton, table, list and help-tree items, #RelayTerminal,
    # #InteractiveCard, #WizardBackButton. Darker than both table row
    # colours in each theme, so a zebra row still changes under the pointer.
    "bg.hover": ("#E6E9ED", "#282E36"),
    # QPushButton pressed
    "bg.pressed": ("#C3C7CD", "#1F242B"),
    # Progress bar and slider grooves (#TrackerProgress's too): in light a step darker than
    # the page and the cards, in dark the page's colour; inside a border.subtle outline, which
    # shows a bar's whole length on the page
    "bg.track": ("#DADDE2", "#1F242B"),
    # Alternate table rows (QPalette.AlternateBase)
    "bg.alt": ("#F1F3F5", "#373E48"),
    # Disabled inputs, buttons (default, primary, danger, #WizardNextButton) and checkbox
    # indicators (QPalette Disabled Base and Button)
    "bg.disabled": ("#ECEEF1", "#262B33"),
    # Selected items and selected text: a solid fill under text.on-accent (combo popup,
    # tables, lists, menus, the help tree, inputs; QPalette.Highlight)
    "bg.selected": ("#0F766E", "#2DD4BF"),
    # A Help search hit, under whatever text it lands on: body text, a heading, a link or the
    # muted related-topics line (amber-900 in dark: today's amber-800 #92400E gave teal
    # headings and links 4.79:1, 4.0:1 washed out)
    "bg.highlight": ("#FDE68A", "#78350F"),
    # QToolTip (QPalette.ToolTipBase)
    "bg.tooltip": ("#1A1D1F", "#E5E9EF"),
    # ---- Text --------------------------------------------------------------------------
    # Body text (QPalette WindowText, Text, ButtonText): titles, typed input, labels,
    # buttons, tables, lists, menus, the selected tab, the help tree and Help pages; the
    # value written in a #TrackerProgress bar, #WizardSummaryValue, #CagesTitle, the month
    # and year of a calendar popup
    "text.primary": ("#1A1D1F", "#E5E9EF"),
    # Subtitles, help text, tab labels, table headers, nested group-box titles, the combo
    # arrow, #StatusLabel, form labels, #RelayNumber, the step-circle number, the Back
    # button, card and step descriptions, #ScheduleCardMeta, #SchedulesHubEmptyTitle, the
    # help breadcrumb, #GroupDescription, the Calibration tab's description,
    # #WizardSummaryLabel, #CagesSubtitle; muted words in Help
    "text.secondary": ("#2E3A4B", "#CBD5E1"),
    # Captions, placeholders (QPalette.PlaceholderText), #BoardTitle, #ColumnHeader,
    # #UnassignedLabel, #HealthIndicator, #TimeRemaining, #ScheduleCardHint,
    # #SchedulesHubEmptyText, the hint on a schedule's drag pixmap, #DeliveryStatus
    # (Waiting and other words), a pending step, step titles, the help result count,
    # #SlackStatus before any message, the dashes of an uncalibrated row and a missing CV
    # in the Calibration table, #WizardSelectionCounter (none selected), #WizardEmptyState,
    # #CagesBoardPlaceholder
    "text.muted": ("#475366", "#B8C1CC"),
    # Disabled controls only (QPalette Disabled WindowText, Text and ButtonText)
    "text.disabled": ("#7B8490", "#6B7480"),
    # A calendar popup's weekend dates and weekday names (theme.tone_weekend): Qt's red, a
    # shade that reads (its #FF0000 gave 4.0:1 on the light card and 3.0:1 on the dark one)
    "text.weekend": ("#B91C1C", "#FCA5A5"),
    # Teal text: #InfoBanner, #ElapsedTime, the current step, a completed step title,
    # #CardIcon, #CardBadge, #StepIcon, #ScheduleCardCreated, the name on a schedule's drag
    # pixmap, #DeliveryStatus[status="delivering"], #WizardSummarySection; Help headings
    "text.accent": ("#115E59", "#5EEAD4"),
    # Links (QPalette Link, LinkVisited): Help links, underlined because they differ from
    # body text by colour less than 3:1, and #LinkLabel (Show password), underlined only
    # under the pointer
    "text.link": ("#115E59", "#5EEAD4"),
    # Text on accent.fill and bg.selected: the primary button, #InfoButton, #CageBadge,
    # #StatusLabel[status="open"], a completed step circle, #WizardNextButton, the
    # Staggered badge, selected items and text (QPalette.HighlightedText); the splash
    # screen's #SplashTitle and #SplashStatus, and its bar's chunk
    "text.on-accent": ("#FFFFFF", "#042F2E"),
    # The danger button's label
    "text.on-danger": ("#FFFFFF", "#FFFFFF"),
    # The Instant badge's label, on instant.fill
    "text.on-instant": ("#FFFFFF", "#1E1B4B"),
    # QToolTip (QPalette.ToolTipText)
    "text.tooltip": ("#FFFFFF", "#1A1D1F"),
    # ---- Borders -----------------------------------------------------------------------
    # The one structural stroke (Fluent's colorNeutralStroke1): cards, tab panes and the
    # selected tab, the separator between unselected tabs, group boxes, tables and the rule
    # under their header, lists, menus, the combo popup, the login prompt, #MaterialCard,
    # progress bars (#TrackerProgress too), #RelayTerminal, #WizardLog, #InteractiveCard,
    # #ScheduleCard, #WizardConnector, the Help sidebar's edge; disabled inputs, buttons and
    # indicators
    "border.subtle": ("#C8CED6", "#4F5865"),
    # Rules inside a card, a step lighter than the outline (Fluent's colorNeutralStroke2):
    # table row rules, a section's rule (a group box inside a group box or a card), the rule
    # under a card's header (QFrame#Divider), #WizardSeparator, the rule under #TrackerHeader,
    # an #AnimalConfigRow, a nested tab strip and #WizardSummarySection; the rule above
    # Help's related topics. A decorative rule, not a control's boundary, so WCAG 1.4.11
    # asks nothing of it: the light one has a floor of its own, 1.30:1 and 1.10 clipped, and
    # stays a step under border.subtle (D4L and H1 in test_theme_contrast.py)
    "border.divider": ("#D9DEE5", "#4B5461"),
    # A boundary that identifies a control: inputs, QPushButton, checkbox and radio
    # rings, scrollbar handles, an idle drop area, #SchedulesHubSearch,
    # #SchedulesHubSelect, the wizard's step circles, Back and Start Over buttons
    "border.control": ("#626E7E", "#848E9B"),
    # A control boundary under the pointer or pressed; #RelayTerminal, #InteractiveCard
    # and #ScheduleCard under the pointer (a schedule card also lifts)
    "border.control.hover": ("#475569", "#A3ADB9"),
    # ---- Shadows -----------------------------------------------------------------------
    # The ink of every card shadow (SHADOWS below): black, as Fluent 2 and Material 3 draw
    # theirs; a layer's alpha says how much of it shows. The dark theme paints no shadow.
    "shadow.ink": ("#000000", "#000000"),
    # ---- Focus -------------------------------------------------------------------------
    # The 2px focus border of inputs and QPushButton; the 1px one of #SchedulesHubSearch and
    # of #CageNameEdit, which shows only while it has the focus. Fluent 2's focus stroke
    # (colorStrokeFocus2): black in light, white in dark. A focused control swaps its
    # border.control edge for it, a change of 4.05:1 in light and 3.32:1 in dark (F7);
    # palette B's teal ring had nearly the edge's luminance (1.06 and 1.78:1)
    "focus.ring": ("#000000", "#FFFFFF"),
    # A focused primary button's border, around its accent.fill: the same focus stroke. In
    # light it is 3.84:1 over the button's own accent edge (F8; palette B's #042F2E was
    # 2.64); in dark no one colour is 3:1 from the light teal fill and from the page (I3)
    "focus.ring.primary": ("#000000", "#FFFFFF"),
    # ---- Accent (teal) -----------------------------------------------------------------
    # The primary button, #InfoButton, #StatusLabel[status="open"], #CageBadge, the
    # Staggered badge, checked checkboxes and radios, a completed step circle,
    # #WizardNextButton; the splash screen's gradient, which ends in accent.fill.hover
    "accent.fill": ("#0F766E", "#2DD4BF"),
    # The primary button, #InfoButton, the slider handle and #WizardNextButton under the
    # pointer
    "accent.fill.hover": ("#115E59", "#5EEAD4"),
    # The primary button and #InfoButton pressed; the groove of #SplashProgress
    "accent.fill.pressed": ("#134E4A", "#99F6E4"),
    # Marks that carry a state or a value: the selected tab's top bar, the progress chunk,
    # the slider, the drop-target border, the stripes of #InfoBanner and #RelayTerminal, a
    # selected #RelayTerminal's or #ScheduleCard's border, the border of a schedule's
    # drag pixmap, #StatusDot, the current step's ring, a completed connector, a checked
    # #InteractiveCard's border; Help note stripes
    "accent.indicator": ("#0F766E", "#2DD4BF"),
    # A teal wash: the drop target, #InfoBanner, #ElapsedTime, a selected #RelayTerminal
    # or #ScheduleCard, a schedule's drag pixmap, the current step, a checked
    # #InteractiveCard, #CardIcon, #CardBadge; Help notes
    "accent.tint": ("#CCFBF1", "#11463F"),
    # ---- The Instant delivery mode (indigo; Staggered's colour is the accent) ----------
    # The Instant badge on a schedule card. Today's indigo, a shade darker in light so its
    # white label reads (#6366F1 gave 4.47:1), and in dark a light indigo under dark text,
    # as accent.fill is
    "instant.fill": ("#4F46E5", "#A5B4FC"),
    # ---- The progress tracker's bars (#TrackerProgress) ------------------------------
    # A bar writes its value inside it, in text.primary over the groove and the fill
    # alike, so each fill is a shade that text reads on (4.5:1 or more): light in the
    # light theme, dark in the dark one. A fill stays under 3:1 against its groove
    # (1.3 to 2.3:1): the value is the text in the bar and the volume under it, and the
    # fill only supports them.
    # A running delivery (teal-500 in light, the light end of today's gradient)
    "progress.fill": ("#14B8A6", "#115E59"),
    # Complete, on the success.tint groove
    "progress.fill.complete": ("#10B981", "#065F46"),
    # Failed, on the danger.tint groove
    "progress.fill.failed": ("#F87171", "#B91C1C"),
    # ---- Status: today's hue families; a shade changes only where a pair fails WCAG ----
    # QLabel[variant="success"]; Help tips; the tint is a complete #TrackerProgress's
    # groove
    "success.tint": ("#D1FAE5", "#064E3B"),
    "success.on-tint": ("#065F46", "#A7F3D0"),
    "success.indicator": ("#10B981", "#10B981"),
    # A success word: #DeliveryStatus[status="complete"] (today's #059669 gave 3.77:1),
    # #SlackStatus[status="ok"], [OK] and a CV under 3 % in the Calibration table,
    # #WizardSelectionCounter[count="some"]
    "success.text": ("#065F46", "#6EE7B7"),
    # QLabel[variant="warning"]; #MasterTerminal under the pointer and selected;
    # #WizardLimitBanner, with its text (#WizardLimitText) in warning.on-tint
    "warning.tint": ("#FEF3C7", "#78350F"),
    # #MasterTerminal
    "warning.tint.master-terminal": ("#FFFBEB", "#451A03"),
    "warning.on-tint": ("#92400E", "#FDE68A"),
    # #MasterLabel: MASTER SOLENOID on the master terminal's fills
    "warning.on-tint.master-terminal": ("#92400E", "#FCD34D"),
    # QLabel[variant="warning"]'s stripe, #MasterTerminal's stripe, #WizardLimitBanner's
    # edge
    "warning.indicator": ("#F59E0B", "#F59E0B"),
    # #MasterTerminal's outline
    "warning.indicator.master-terminal": ("#FCD34D", "#78350F"),
    # #MasterStatusDot: on the master terminal, and in the Cages tab's legend on the page,
    # where it keys the master's colour: 3:1 or more there (amber-700 in light: today's
    # amber-500 was 1.58:1 on the page)
    "warning.indicator.status-dot": ("#B45309", "#FBBF24"),
    # A selected #MasterTerminal's border: its selected state, 3:1 or more against the
    # card and its own fill (amber-700 in light: today's amber-500 was 2.15:1)
    "warning.indicator.selected": ("#B45309", "#FBBF24"),
    # A warning word: #DeliveryStatus[status="paused"] (today's #D97706 gave 3.19:1),
    # #SlackStatus[status="warn"], Stale and a CV under 5 % in the Calibration table. In
    # light, today's mustard there, (200, 150, 0) at 2.69:1, a shade darker: it keeps its
    # hue, so it stays apart from danger.text (CIEDE2000 32.4; amber-800 #92400E gave 13.2)
    "warning.text": ("#7A5C00", "#FCD34D"),
    # QPushButton[variant="danger"]; white reads on these in both themes (today's dark
    # #EF4444, #F87171 gave it 3.76:1 and 2.77:1)
    "danger.fill": ("#DC2626", "#DC2626"),
    "danger.fill.hover": ("#B91C1C", "#B91C1C"),
    "danger.fill.pressed": ("#991B1B", "#991B1B"),
    # QLabel[variant="error"]; Help warnings; Cancel in the Schedules hub's select mode
    # (#SchedulesHubSelect[selecting="true"]); the tint is a failed #TrackerProgress's
    # groove
    "danger.tint": ("#FEE2E2", "#7F1D1D"),
    "danger.on-tint": ("#991B1B", "#FECACA"),
    "danger.indicator": ("#EF4444", "#EF4444"),
    # A deeper danger tint: the edge of that Cancel button, and its fill under the pointer
    "danger.tint.strong": ("#FECACA", "#991B1B"),
    # A danger word: #DeliveryStatus[status="failed"] (today's #DC2626 would give 2.49:1 on
    # the dark card); Invalid, Not Calibrated and a CV of 5 % or more in the Calibration
    # table, #WizardSelectionCounter[count="over"], the calibration wizard's "Before
    # proceeding, ensure:"
    "danger.text": ("#B91C1C", "#FCA5A5"),
    # The Animals tab's bright red cell for a run that ended short, and its bold text
    # (QWidget#AnimalsTab qproperty-alertFill / qproperty-alertText)
    "danger.alert": ("#DC2626", "#DC2626"),
    "danger.on-alert": ("#FFFFFF", "#FFFFFF"),
    # QLabel[variant="info"]
    "info.tint": ("#E0F2FE", "#0C4A6E"),
    "info.on-tint": ("#0C4A6E", "#BAE6FD"),
    "info.indicator": ("#0284C7", "#0284C7"),
}

# Card shadows. A recipe is CSS box-shadow layers (x, y, blur, spread, alpha), in px, in
# shadow.ink; ui.style.elevation paints it from a cached tile into the room the card
# reserves (QFrame[elevation="card"] in app.qss.tmpl, whose margin build_qss.py writes from
# the union of every recipe's reach: any recipe can stand in for another without moving a
# widget). ELEVATION below names the one a card paints. Kept out of TOKENS, which holds
# opaque colours only.
SHADOWS: dict[str, tuple[tuple[float, float, float, float, float], ...]] = {
    # Fluent 2 shadow4, its resting card: 0 0 2px rgba(0,0,0,.12), 0 2px 4px rgba(0,0,0,.14)
    # (fluentui packages/tokens/src/utils/shadows.ts; alias/lightColor.ts)
    "fluent.shadow4": ((0, 0, 2, 0, 0.12), (0, 2, 4, 0, 0.14)),
    # The same with Fluent's Darker shadow alphas (colorNeutralShadowAmbientDarker .20,
    # colorNeutralShadowKeyDarker .24): one step more lift, should a card need it
    "fluent.shadow4.darker": ((0, 0, 2, 0, 0.20), (0, 2, 4, 0, 0.24)),
    # Material 3 level 1: 0 1px 2px 0 rgba(0,0,0,.3), 0 1px 3px 1px rgba(0,0,0,.15)
    # (material-web elevation/internal/_elevation.scss), the crisp end
    "m3.level1": ((0, 1, 2, 0, 0.30), (0, 1, 3, 1, 0.15)),
}

# Elevation levels: level -> (light recipe, dark recipe), names in SHADOWS; None paints no
# shadow. "card" is every elevated card's (ui.style.elevation.ElevatedMixin); the dark theme
# separates its surfaces by tint and stroke instead. The one source of a card's shadow:
# nothing else (no setting, no environment variable) picks another recipe.
ELEVATION: dict[str, tuple[str | None, str | None]] = {
    "card": ("fluent.shadow4", None),
}

# The QPalette StyleManager applies before the stylesheet (qt_palette.py): QPalette colour
# role name -> token, for the Active, Inactive and Disabled groups alike.
QPALETTE: dict[str, str] = {
    "Window": "bg.page",
    "WindowText": "text.primary",
    "Base": "bg.field",
    "AlternateBase": "bg.alt",
    "Text": "text.primary",
    "PlaceholderText": "text.muted",
    "Button": "bg.surface",
    "ButtonText": "text.primary",
    "Highlight": "bg.selected",
    "HighlightedText": "text.on-accent",
    "Link": "text.link",
    "LinkVisited": "text.link",
    "ToolTipBase": "bg.tooltip",
    "ToolTipText": "text.tooltip",
}

# The roles whose Disabled group differs from QPALETTE
QPALETTE_DISABLED: dict[str, str] = {
    "WindowText": "text.disabled",
    "Text": "text.disabled",
    "ButtonText": "text.disabled",
    "Base": "bg.disabled",
    "Button": "bg.disabled",
}

# The Help tab's HTML palette (Project/utils/help_content_manager.py): CSS slot -> token
HELP_HTML: dict[str, str] = {
    "page_bg": "bg.surface",
    "text": "text.primary",
    "h1": "text.accent",
    "h2": "text.primary",
    "muted": "text.secondary",
    "link": "text.link",
    "code_bg": "bg.inset",
    "rule": "border.divider",
    "note_bg": "accent.tint",
    "note_border": "accent.indicator",
    "warn_bg": "danger.tint",
    "warn_border": "danger.indicator",
    "tip_bg": "success.tint",
    "tip_border": "success.indicator",
    "hl_bg": "bg.highlight",
}


def value(name: str, theme: str) -> str:
    """The colour of role `name` in `theme` ("light" or "dark").

    KeyError for an unknown role, ValueError for an unknown theme.
    """
    light, dark = TOKENS[name]
    if theme == "light":
        return light
    if theme == "dark":
        return dark
    raise ValueError(f"unknown theme {theme!r}: expected one of {THEMES}")
