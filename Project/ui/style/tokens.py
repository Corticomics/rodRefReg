"""Colour tokens of the RRR themes: role name -> (light, dark).

app.qss.tmpl names every colour by its role, as ${bg.surface}; build_qss.py renders the
template once per theme with these values into app-light.qss and app-dark.qss. A role says
what a colour is for (bg.surface: cards, tables, menus), not what it looks like, so a new
palette is a change of values here, not of the template. Two roles may hold the same
colour (bg.page and bg.inset do): they still say different things.

The palette is the robust-contrast one (palette B, v2.1.0): a grey page, white cards and
fields, borders that show, and the same structure in the dark theme. Its steps stay visible
on a monitor that clips or washes out the Pi's HDMI signal (contrast.py has the models).

Two things read the roles:
- the stylesheet template, through its ${role} placeholders;
- the QPalette StyleManager sets before the stylesheet (qt_palette.py), through QPALETTE and
  QPALETTE_DISABLED below. It colours what the stylesheet does not reach: the window, plain
  containers, placeholders, alternate rows, rich-text links, calendar popups.

Project/tests/unit/test_theme_contrast.py checks every pair of roles the UI draws together,
in both themes. A pair that fails is fixed by changing a colour here, never its threshold.

Data and one lookup, nothing else: build_qss.py, qt_palette.py and the tests load this file
by path, without importing the ui package. After editing it, run
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
    # #MaterialCard, #RelayTerminal, #InteractiveCard, the wizard's step circles and Back
    # button, the help panes (QPalette.Button)
    "bg.surface": ("#FFFFFF", "#30373F"),
    # Editable fields, focused or not; checkbox and radio indicators; #CageNameEdit
    # (QPalette.Base)
    "bg.field": ("#FFFFFF", "#30373F"),
    # Sunken areas inside a surface: a nested group box, the table header band and its
    # corner, #WizardLog, #RelayNumber, #StatusLabel[status="closed"]
    "bg.inset": ("#DADDE2", "#1F242B"),
    # Unselected tabs
    "bg.rail": ("#C3C7CD", "#30373F"),
    # An unselected tab under the pointer
    "bg.rail.hover": ("#CFD2D7", "#3A424C"),
    # Under the pointer: QPushButton, table, list and help-tree items, #RelayTerminal,
    # #InteractiveCard, #WizardBackButton. Darker than both table row colours in each
    # theme, so a zebra row still changes under the pointer.
    "bg.hover": ("#E6E9ED", "#282E36"),
    # QPushButton pressed
    "bg.pressed": ("#C3C7CD", "#1F242B"),
    # Progress bar and slider grooves
    "bg.track": ("#DADDE2", "#1F242B"),
    # Alternate table rows (QPalette.AlternateBase)
    "bg.alt": ("#F1F3F5", "#373E48"),
    # Disabled inputs, buttons (default, primary, danger, #WizardNextButton) and checkbox
    # indicators (QPalette Disabled Base and Button)
    "bg.disabled": ("#ECEEF1", "#262B33"),
    # Selected items and selected text: a solid fill under text.on-accent (combo popup,
    # tables, lists, menus, the help tree, inputs; QPalette.Highlight)
    "bg.selected": ("#0F766E", "#2DD4BF"),
    # QToolTip (QPalette.ToolTipBase)
    "bg.tooltip": ("#1A1D1F", "#E5E9EF"),
    # ---- Text --------------------------------------------------------------------------
    # Body text (QPalette WindowText, Text, ButtonText): titles, typed input, labels,
    # buttons, tables, lists, menus, the selected tab, the help tree
    "text.primary": ("#1A1D1F", "#E5E9EF"),
    # Subtitles, help text, tab labels, table headers, nested group-box titles, the combo
    # arrow, #StatusLabel, form labels, #RelayNumber, the step-circle number, the Back
    # button, card and step descriptions, the help breadcrumb
    "text.secondary": ("#2E3A4B", "#CBD5E1"),
    # Captions, placeholders (QPalette.PlaceholderText), #BoardTitle, #ColumnHeader,
    # #UnassignedLabel, #HealthIndicator, #TimeRemaining, a pending step, step titles, the
    # help result count
    "text.muted": ("#475366", "#B8C1CC"),
    # Disabled controls only (QPalette Disabled WindowText, Text and ButtonText)
    "text.disabled": ("#7B8490", "#6B7480"),
    # Teal text: #InfoBanner, #ElapsedTime, the current step, a completed step title,
    # #CardIcon, #CardBadge, #StepIcon
    "text.accent": ("#115E59", "#5EEAD4"),
    # Links: #LinkLabel (QPalette Link, LinkVisited)
    "text.link": ("#115E59", "#5EEAD4"),
    # Text on accent.fill and bg.selected: the primary button, #InfoButton, #CageBadge,
    # #StatusLabel[status="open"], a completed step circle, #WizardNextButton, selected
    # items and text (QPalette.HighlightedText)
    "text.on-accent": ("#FFFFFF", "#042F2E"),
    # The danger button's label
    "text.on-danger": ("#FFFFFF", "#FFFFFF"),
    # QToolTip (QPalette.ToolTipText)
    "text.tooltip": ("#FFFFFF", "#1A1D1F"),
    # ---- Borders -----------------------------------------------------------------------
    # Decorative outlines: cards, tab panes and tabs, group boxes, tables, lists, menus,
    # the combo popup, the table header rule, #TrackerHeader, #MaterialCard,
    # #RelayTerminal, #WizardLog, #InteractiveCard, #WizardConnector, the help panes;
    # disabled inputs, buttons and indicators
    "border.subtle": ("#AAB2BE", "#4F5865"),
    # Table grid lines and row rules, #WizardSeparator
    "border.divider": ("#CDD1D7", "#4B5461"),
    # A boundary that identifies a control: inputs, QPushButton, checkbox and radio
    # rings, scrollbar handles, an idle drop area, #CageNameEdit, the wizard's step
    # circles and Back button
    "border.control": ("#626E7E", "#848E9B"),
    # A control boundary under the pointer or pressed; #RelayTerminal and #InteractiveCard
    # under the pointer
    "border.control.hover": ("#475569", "#A3ADB9"),
    # ---- Focus -------------------------------------------------------------------------
    # The 2px focus border of inputs and QPushButton
    "focus.ring": ("#0F766E", "#2DD4BF"),
    # A focused primary button's border, around its accent.fill
    "focus.ring.primary": ("#042F2E", "#FFFFFF"),
    # ---- Accent (teal) -----------------------------------------------------------------
    # The primary button, #InfoButton, #StatusLabel[status="open"], #CageBadge, checked
    # checkboxes and radios, a completed step circle, #WizardNextButton
    "accent.fill": ("#0F766E", "#2DD4BF"),
    # The primary button, #InfoButton, the slider handle and #WizardNextButton under the
    # pointer
    "accent.fill.hover": ("#115E59", "#5EEAD4"),
    # The primary button and #InfoButton pressed
    "accent.fill.pressed": ("#134E4A", "#99F6E4"),
    # Marks that carry a state or a value: the selected tab's top bar, the progress chunk,
    # the slider, the drop-target border, the stripes of #InfoBanner and #RelayTerminal, a
    # selected #RelayTerminal's border, #StatusDot, the current step's ring, a completed
    # connector, a checked #InteractiveCard's border
    "accent.indicator": ("#0F766E", "#2DD4BF"),
    # A teal wash: the drop target, #InfoBanner, #ElapsedTime, a selected #RelayTerminal,
    # the current step, a checked #InteractiveCard, #CardIcon, #CardBadge
    "accent.tint": ("#CCFBF1", "#11463F"),
    # ---- Status: today's hue families; a shade changes only where a pair fails WCAG ----
    # QLabel[variant="success"]
    "success.tint": ("#D1FAE5", "#064E3B"),
    "success.on-tint": ("#065F46", "#A7F3D0"),
    "success.indicator": ("#10B981", "#10B981"),
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
    # #MasterLabel
    "warning.text": ("#92400E", "#FCD34D"),
    # QPushButton[variant="danger"]; white reads on these in both themes (today's dark
    # #EF4444, #F87171 gave it 3.76:1 and 2.77:1)
    "danger.fill": ("#DC2626", "#DC2626"),
    "danger.fill.hover": ("#B91C1C", "#B91C1C"),
    "danger.fill.pressed": ("#991B1B", "#991B1B"),
    # QLabel[variant="error"]
    "danger.tint": ("#FEE2E2", "#7F1D1D"),
    "danger.on-tint": ("#991B1B", "#FECACA"),
    "danger.indicator": ("#EF4444", "#EF4444"),
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
