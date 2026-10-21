"""Colour tokens of the RRR themes: role name -> (light, dark).

app.qss.tmpl names every colour by its role, as ${bg.surface}; build_qss.py renders the
template once per theme with these values into app-light.qss and app-dark.qss. A role says
what a colour is for (bg.surface: cards, tables, menus), not what it looks like, so a new
palette is a change of values here, not of the template. Two roles may hold the same
colour (bg.page and bg.inset do): they still say different things.

The palette is the robust-contrast one (palette B, v2.1.0): a grey page, white cards and
fields, borders that show, and the same structure in the dark theme. Its steps stay visible
on a monitor that clips or washes out the Pi's HDMI signal (contrast.py has the models).

Three things read the roles:
- the stylesheet template, through its ${role} placeholders;
- the QPalette StyleManager sets before the stylesheet (qt_palette.py), through QPALETTE and
  QPALETTE_DISABLED below. It colours what the stylesheet does not reach: the window, plain
  containers, placeholders, alternate rows, rich-text links, calendar popups;
- the Help tab's HTML (Project/utils/help_content_manager.py), through HELP_HTML below.

Project/tests/unit/test_theme_contrast.py checks every pair of roles the UI draws together,
in both themes. A pair that fails is fixed by changing a colour here, never its threshold.

Data and one lookup, nothing else: build_qss.py, qt_palette.py, help_content_manager.py and
the tests load this file by path, without importing the ui package. After editing it, run
python3 Project/ui/style/build_qss.py and commit it with both regenerated stylesheets.
"""

from __future__ import annotations

THEMES = ("light", "dark")

# name: (light, dark)
TOKENS: dict[str, tuple[str, str]] = {
    # ---- Backgrounds -------------------------------------------------------------------
    # The page (QPalette.Window): windows and dialogs, tab panes and the selected tab that
    # joins its pane, the help sidebar, #WizardStepContent
    "bg.page": ("#DADDE2", "#1F242B"),
    # Cards and other raised surfaces: Card, the login prompt, group boxes, tables, lists,
    # menus, the combo popup, QPushButton, an idle drop area, #TrackerHeader,
    # #MaterialCard, #RelayTerminal, #InteractiveCard, #ScheduleCard, the wizard's step
    # circles and Back button, the help panes (QPalette.Button)
    "bg.surface": ("#FFFFFF", "#30373F"),
    # Editable fields, focused or not; checkbox and radio indicators; #CageNameEdit,
    # #SchedulesHubSearch (QPalette.Base)
    "bg.field": ("#FFFFFF", "#30373F"),
    # Sunken areas inside a surface: a nested group box, the table header band and its
    # corner, #WizardLog, #RelayNumber, #StatusLabel[status="closed"]; inline code in Help
    "bg.inset": ("#DADDE2", "#1F242B"),
    # Unselected tabs
    "bg.rail": ("#C3C7CD", "#30373F"),
    # An unselected tab under the pointer
    "bg.rail.hover": ("#CFD2D7", "#3A424C"),
    # Under the pointer: QPushButton, table, list and help-tree items, #RelayTerminal,
    # #InteractiveCard, #ScheduleCard, #WizardBackButton. Darker than both table row
    # colours in each theme, so a zebra row still changes under the pointer.
    "bg.hover": ("#E6E9ED", "#282E36"),
    # QPushButton pressed
    "bg.pressed": ("#C3C7CD", "#1F242B"),
    # Progress bar and slider grooves (#TrackerProgress's too)
    "bg.track": ("#DADDE2", "#1F242B"),
    # Alternate table rows (QPalette.AlternateBase)
    "bg.alt": ("#F1F3F5", "#373E48"),
    # Disabled inputs, buttons (default, primary, danger, #WizardNextButton) and checkbox
    # indicators (QPalette Disabled Base and Button)
    "bg.disabled": ("#ECEEF1", "#262B33"),
    # Selected items and selected text: a solid fill under text.on-accent (combo popup,
    # tables, lists, menus, the help tree, inputs; QPalette.Highlight)
    "bg.selected": ("#0F766E", "#2DD4BF"),
    # A Help search hit
    "bg.highlight": ("#FDE68A", "#92400E"),
    # QToolTip (QPalette.ToolTipBase)
    "bg.tooltip": ("#1A1D1F", "#E5E9EF"),
    # ---- Text --------------------------------------------------------------------------
    # Body text (QPalette WindowText, Text, ButtonText): titles, typed input, labels,
    # buttons, tables, lists, menus, the selected tab, the help tree and Help pages; the
    # value written in a #TrackerProgress bar
    "text.primary": ("#1A1D1F", "#E5E9EF"),
    # Subtitles, help text, tab labels, table headers, nested group-box titles, the combo
    # arrow, #StatusLabel, form labels, #RelayNumber, the step-circle number, the Back
    # button, card and step descriptions, #ScheduleCardMeta, #SchedulesHubEmptyTitle, the
    # help breadcrumb, #GroupDescription, the Calibration tab's description; muted words
    # in Help
    "text.secondary": ("#2E3A4B", "#CBD5E1"),
    # Captions, placeholders (QPalette.PlaceholderText), #BoardTitle, #ColumnHeader,
    # #UnassignedLabel, #HealthIndicator, #TimeRemaining, #ScheduleCardHint,
    # #SchedulesHubEmptyText, the hint on a schedule's drag pixmap, #DeliveryStatus
    # (Waiting and other words), a pending step, step titles, the help result count,
    # #SlackStatus before any message, the dashes of an uncalibrated row and a missing CV
    # in the Calibration table
    "text.muted": ("#475366", "#B8C1CC"),
    # Disabled controls only (QPalette Disabled WindowText, Text and ButtonText)
    "text.disabled": ("#7B8490", "#6B7480"),
    # Teal text: #InfoBanner, #ElapsedTime, the current step, a completed step title,
    # #CardIcon, #CardBadge, #StepIcon, #ScheduleCardCreated, the name on a schedule's drag
    # pixmap, #DeliveryStatus[status="delivering"]; Help headings
    "text.accent": ("#115E59", "#5EEAD4"),
    # Links: #LinkLabel, Help links (underlined: they differ from body text by colour
    # less than 3:1) (QPalette Link, LinkVisited)
    "text.link": ("#115E59", "#5EEAD4"),
    # Text on accent.fill and bg.selected: the primary button, #InfoButton, #CageBadge,
    # #StatusLabel[status="open"], a completed step circle, #WizardNextButton, the
    # Staggered badge, selected items and text (QPalette.HighlightedText)
    "text.on-accent": ("#FFFFFF", "#042F2E"),
    # The danger button's label
    "text.on-danger": ("#FFFFFF", "#FFFFFF"),
    # The Instant badge's label, on instant.fill
    "text.on-instant": ("#FFFFFF", "#1E1B4B"),
    # QToolTip (QPalette.ToolTipText)
    "text.tooltip": ("#FFFFFF", "#1A1D1F"),
    # ---- Borders -----------------------------------------------------------------------
    # Decorative outlines: cards, tab panes and tabs, group boxes, tables, lists, menus,
    # the combo popup, the table header rule, #TrackerHeader, #MaterialCard,
    # #TrackerProgress, #RelayTerminal, #WizardLog, #InteractiveCard, #ScheduleCard,
    # #WizardConnector, the help panes; disabled inputs, buttons and indicators
    "border.subtle": ("#AAB2BE", "#4F5865"),
    # Table grid lines and row rules, #WizardSeparator; the rule above Help's related
    # topics
    "border.divider": ("#CDD1D7", "#4B5461"),
    # A boundary that identifies a control: inputs, QPushButton, checkbox and radio
    # rings, scrollbar handles, an idle drop area, #CageNameEdit, #SchedulesHubSearch,
    # #SchedulesHubSelect, the wizard's step circles and Back button
    "border.control": ("#626E7E", "#848E9B"),
    # A control boundary under the pointer or pressed; #RelayTerminal, #InteractiveCard
    # and #ScheduleCard under the pointer
    "border.control.hover": ("#475569", "#A3ADB9"),
    # ---- Focus -------------------------------------------------------------------------
    # The 2px focus border of inputs and QPushButton; the 1px one of #SchedulesHubSearch
    "focus.ring": ("#0F766E", "#2DD4BF"),
    # A focused primary button's border, around its accent.fill
    "focus.ring.primary": ("#042F2E", "#FFFFFF"),
    # ---- Accent (teal) -----------------------------------------------------------------
    # The primary button, #InfoButton, #StatusLabel[status="open"], #CageBadge, the
    # Staggered badge, checked checkboxes and radios, a completed step circle,
    # #WizardNextButton
    "accent.fill": ("#0F766E", "#2DD4BF"),
    # The primary button, #InfoButton, the slider handle and #WizardNextButton under the
    # pointer
    "accent.fill.hover": ("#115E59", "#5EEAD4"),
    # The primary button and #InfoButton pressed
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
    # #SlackStatus[status="ok"], [OK] and a CV under 3 % in the Calibration table
    "success.text": ("#065F46", "#6EE7B7"),
    # QLabel[variant="warning"]; #MasterTerminal under the pointer and selected
    "warning.tint": ("#FEF3C7", "#78350F"),
    # #MasterTerminal
    "warning.tint.master-terminal": ("#FFFBEB", "#451A03"),
    "warning.on-tint": ("#92400E", "#FDE68A"),
    # QLabel[variant="warning"]'s stripe, #MasterTerminal's stripe
    "warning.indicator": ("#F59E0B", "#F59E0B"),
    # #MasterTerminal's outline
    "warning.indicator.master-terminal": ("#FCD34D", "#78350F"),
    # #MasterStatusDot
    "warning.indicator.status-dot": ("#F59E0B", "#FBBF24"),
    # A selected #MasterTerminal's border: its selected state, 3:1 or more against the
    # card and its own fill (amber-700 in light: today's amber-500 was 2.15:1)
    "warning.indicator.selected": ("#B45309", "#FBBF24"),
    # #MasterLabel; #DeliveryStatus[status="paused"] (today's #D97706 gave 3.19:1),
    # #SlackStatus[status="warn"], Stale and a CV under 5 % in the Calibration table
    "warning.text": ("#92400E", "#FCD34D"),
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
    # table
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
