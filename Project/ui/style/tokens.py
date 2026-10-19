"""Colour tokens of the RRR stylesheets: role name -> (light, dark).

app.qss.tmpl names every colour by its role, as ${bg.surface}; build_qss.py renders the
template once per theme with these values into app-light.qss and app-dark.qss. A role says
what a colour is for (bg.surface: cards, tables, menus), not what it looks like, so a new
palette is a change of values here, not of the template.

- Two roles may hold the same colour: bg.page and bg.rail do today, and so do
  border.subtle and border.control.
- "<role>.<qualifier>" is a variant: today's stylesheets give some uses of a role a colour
  of their own (the wizard's Back button, the InfoButton's dark-theme hover). The variants
  keep the generated files as they were; a palette that drops the difference gives a
  variant its role's value. A variant's name starts with its role, except
  border.control.pressed (the pressed button's border), a variant of border.control.hover.
- Values are spelled as the stylesheets spell them: #RRGGBB, or white where today's
  stylesheet writes the keyword.

Data and one lookup, nothing else: build_qss.py and the tests load this file by path,
without importing the ui package. After editing it, run python3 Project/ui/style/build_qss.py
and commit it with both regenerated stylesheets.
"""

from __future__ import annotations

THEMES = ("light", "dark")

# name: (light, dark)
TOKENS: dict[str, tuple[str, str]] = {
    # ---- Backgrounds -------------------------------------------------------------------
    # The page: QWidget's default background, the help sidebar, #WizardStepContent
    "bg.page": ("#F8FAFB", "#1A2028"),
    # QTabWidget::pane, and the selected tab that joins it (today the colour of a card)
    "bg.page.tab-pane": ("#FFFFFF", "#1E2530"),
    # QMainWindow: the rule never matches (the main window is a QWidget)
    "bg.page.main-window": ("#F1F4F6", "#0F1419"),
    # Cards, the login prompt, the combo popup, QPushButton, tables, group boxes, lists,
    # an idle drop area, #MaterialCard, #RelayTerminal, the menu bar, menus,
    # #InteractiveCard, the help tree
    "bg.surface": ("#FFFFFF", "#1E2530"),
    # #TrackerHeader, #WizardStepCircle (default and pending)
    "bg.surface.secondary": ("#F8FAFB", "#242C38"),
    # #WizardBackButton
    "bg.surface.wizard-back": ("#FFFFFF", "#242C38"),
    # #HelpContentPane, #HelpContent (the dark theme uses the page colour)
    "bg.surface.help": ("#FFFFFF", "#1A2028"),
    # Editable fields: line edits, text edits, spin boxes, combo boxes; checkbox and
    # radio indicators
    "bg.field": ("#FFFFFF", "#1E2530"),
    # A field with focus; #CageNameEdit, which shows only while a name is edited
    "bg.field.focus": ("#FFFFFF", "#242C38"),
    # Sunken areas inside a surface: a nested group box, #WizardLog
    "bg.inset": ("#F8FAFB", "#242C38"),
    # The table header band (QHeaderView::section)
    "bg.inset.table-header": ("#F8FAFB", "#1A2028"),
    # Small sunken badges: #StatusLabel[status="closed"], #RelayNumber
    "bg.inset.badge": ("#F1F4F6", "#2D3748"),
    # Unselected tabs
    "bg.rail": ("#F8FAFB", "#1A2028"),
    # An unselected tab under the pointer
    "bg.rail.hover": ("#FFFFFF", "#1E2530"),
    # QPushButton, table items and list items under the pointer
    "bg.hover": ("#F8FAFB", "#242C38"),
    # A teal wash under the pointer: #RelayTerminal, #InteractiveCard, help-tree items
    "bg.hover.accent": ("#F0FDFA", "#134E4A"),
    # #WizardBackButton under the pointer
    "bg.hover.wizard-back": ("#F8FAFB", "#2D3748"),
    # #MaterialCard under the pointer
    "bg.hover.material-card": ("#FAFCFD", "#242C38"),
    # QPushButton pressed
    "bg.pressed": ("#F1F4F6", "#2A3441"),
    # Progress bar and slider grooves
    "bg.track": ("#E2E8F0", "#2D3748"),
    # Disabled inputs, a disabled checkbox indicator
    "bg.disabled": ("#F1F4F6", "#1A2028"),
    # A disabled QPushButton, default or danger
    "bg.disabled.button": ("#F8FAFB", "#1A2028"),
    # A disabled primary button, fill and border
    "bg.disabled.primary": ("#99D5D0", "#134E4A"),
    # A disabled #WizardNextButton
    "bg.disabled.wizard-next": ("#A0AEC0", "#4A5568"),
    # Selected items: the combo popup, tables, lists, menus, the help tree
    "bg.selected": ("#E6FFFA", "#134E4A"),
    # Selected text inside an input
    "bg.selected.input": ("#0D9488", "#14B8A6"),
    # The menu-bar item under the pointer or open
    "bg.selected.menubar": ("#F8FAFB", "#242C38"),
    # QToolTip
    "bg.tooltip": ("#1A1D1F", "#F0F4F8"),
    # ---- Text --------------------------------------------------------------------------
    # Body text (QWidget), titles, typed input, button labels, group-box titles, checkbox
    # and radio labels, step and card titles; in the dark theme also tables, group boxes,
    # lists, menus, the wizard log, the help tree and the help content
    "text.primary": ("#1A1D1F", "#F0F4F8"),
    # Combo popup items
    "text.primary.combo-item": ("#1A1D1F", "#E2E8F0"),
    # The selected tab's label (teal today)
    "text.primary.selected-tab": ("#0D9488", "#14B8A6"),
    # Subtitles, help text, tab labels, table headers, nested group-box titles, the combo
    # arrow, #StatusLabel, form labels, the Back button, card and step descriptions,
    # the help breadcrumb
    "text.secondary": ("#4E5D6C", "#A0AEC0"),
    # #RelayNumber
    "text.secondary.relay-number": ("#4E5D6C", "#E2E8F0"),
    # The number in a #WizardStepCircle
    "text.secondary.step-circle": ("#4E5D6C", "#8492A6"),
    # Captions, placeholders, #BoardTitle, #ColumnHeader, #HealthIndicator,
    # #TimeRemaining, a pending step, step titles, the help result count
    "text.muted": ("#8492A6", "#718096"),
    # #UnassignedLabel
    "text.muted.unassigned": ("#A0AEC0", "#718096"),
    # Disabled inputs and buttons (default and danger)
    "text.disabled": ("#A0AEC0", "#4A5568"),
    # A disabled primary button
    "text.disabled.primary": ("#FFFFFF", "#5EEAD4"),
    # A disabled #WizardNextButton
    "text.disabled.wizard-next": ("#F8FAFB", "#718096"),
    # Text on accent.fill: the primary button, #StatusLabel[status="open"],
    # #DeliveryProgress
    "text.on-accent": ("#FFFFFF", "#042F2E"),
    # Selected text inside an input (on bg.selected.input)
    "text.on-accent.input": ("#FFFFFF", "#1A1D1F"),
    # Selected items' text (on bg.selected)
    "text.on-accent.selected": ("#0D9488", "#2DD4BF"),
    # The #InfoButton's "?"
    "text.on-accent.info-button": ("white", "white"),
    # #CageBadge
    "text.on-accent.cage-badge": ("white", "#042F2E"),
    # A completed #WizardStepCircle, #WizardNextButton
    "text.on-accent.wizard": ("#FFFFFF", "#1A2028"),
    # The danger button's label
    "text.on-danger": ("#FFFFFF", "#FFFFFF"),
    # Teal text: #InfoBanner, #ElapsedTime, the current step, #CardIcon, #CardBadge,
    # #StepIcon
    "text.accent": ("#0D9488", "#2DD4BF"),
    # A completed #WizardStepTitle
    "text.accent.step-title": ("#0D9488", "#14B8A6"),
    # #LinkLabel
    "text.link": ("#0D9488", "#2DD4BF"),
    # #LinkLabel under the pointer
    "text.link.hover": ("#0F766E", "#5EEAD4"),
    # QToolTip
    "text.tooltip": ("#FFFFFF", "#1A1D1F"),
    # ---- Borders -----------------------------------------------------------------------
    # Decorative outlines: cards, the combo popup, tab pane and tabs, the table header
    # rule, tables, group boxes, lists, #TrackerHeader, #MaterialCard, #RelayTerminal,
    # #WizardLog, the menu bar, menus, #InteractiveCard, the help panes (and
    # #HelpContent:focus, which keeps it), disabled inputs, buttons and checkboxes
    "border.subtle": ("#E2E8F0", "#2D3748"),
    # The #WizardConnector line between steps
    "border.subtle.wizard-connector": ("#CBD5E0", "#4A5568"),
    # Table grid lines and row rules
    "border.divider": ("#F1F4F6", "#242C38"),
    # #WizardSeparator
    "border.divider.wizard-separator": ("#E2E8F0", "#2D3748"),
    # The boundary of inputs and QPushButton
    "border.control": ("#E2E8F0", "#2D3748"),
    # Checkbox and radio rings, scrollbar handles, an idle drop area, #WizardStepCircle
    "border.control.strong": ("#CBD5E0", "#4A5568"),
    # #CageNameEdit
    "border.control.cage-name-edit": ("#0D9488", "#14B8A6"),
    # #WizardBackButton
    "border.control.wizard-back": ("#E2E8F0", "#4A5568"),
    # Inputs, QPushButton and #RelayTerminal under the pointer; the Card and
    # #MaterialCard hover outline
    "border.control.hover": ("#CBD5E0", "#4A5568"),
    # QPushButton pressed
    "border.control.pressed": ("#A0AEC0", "#4A5568"),
    # Scrollbar handles under the pointer
    "border.control.hover.strong": ("#A0AEC0", "#718096"),
    # Checkbox and radio rings, #InteractiveCard under the pointer
    "border.control.hover.accent": ("#0D9488", "#14B8A6"),
    # #WizardBackButton under the pointer
    "border.control.hover.wizard-back": ("#CBD5E0", "#718096"),
    # ---- Focus -------------------------------------------------------------------------
    # The 2px focus border of inputs and QPushButton
    "focus.ring": ("#0D9488", "#14B8A6"),
    # A focused primary button
    "focus.ring.primary": ("#115E59", "#5EEAD4"),
    # ---- Accent (teal) -----------------------------------------------------------------
    # The primary button, #InfoButton, #StatusLabel[status="open"], #CageBadge, checked
    # checkboxes and radios, a completed step circle, #WizardNextButton
    "accent.fill": ("#0D9488", "#14B8A6"),
    # The primary button, the slider handle and #WizardNextButton under the pointer
    "accent.fill.hover": ("#0F766E", "#2DD4BF"),
    # #InfoButton under the pointer
    "accent.fill.hover.info-button": ("#0F766E", "#0D9488"),
    # The primary button pressed
    "accent.fill.pressed": ("#115E59", "#5EEAD4"),
    # #InfoButton pressed
    "accent.fill.pressed.info-button": ("#115E59", "#0F766E"),
    # The progress chunk, the drop-target border, #InfoBanner's stripe, #RelayTerminal's
    # stripe and selected border, the slider, the current step's ring, a completed
    # connector, a checked #InteractiveCard's border
    "accent.indicator": ("#0D9488", "#14B8A6"),
    # #StatusDot
    "accent.indicator.status-dot": ("#0D9488", "#2DD4BF"),
    # The #DeliveryProgress chunk's gradient (no widget has that objectName)
    "accent.indicator.gradient-start": ("#0D9488", "#0D9488"),
    "accent.indicator.gradient-end": ("#14B8A6", "#14B8A6"),
    # A teal wash: the drop target, #InfoBanner, #ElapsedTime, a selected #RelayTerminal,
    # the current step, a checked #InteractiveCard, #CardIcon, #CardBadge
    "accent.tint": ("#E6FFFA", "#134E4A"),
    # ---- Status: QLabel[variant=...] banners, the master terminal, the danger button ----
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
    # #MasterLabel
    "warning.text": ("#92400E", "#FCD34D"),
    # A selected #MasterTerminal's border
    "warning.text.master-terminal": ("#F59E0B", "#FBBF24"),
    # QPushButton[variant="danger"]
    "danger.fill": ("#DC2626", "#EF4444"),
    "danger.fill.hover": ("#B91C1C", "#F87171"),
    "danger.fill.pressed": ("#991B1B", "#DC2626"),
    # QLabel[variant="error"]
    "danger.tint": ("#FEE2E2", "#7F1D1D"),
    "danger.on-tint": ("#991B1B", "#FECACA"),
    "danger.indicator": ("#EF4444", "#EF4444"),
    # The Animals tab's cell for a run that ended short, and its text
    # (QWidget#AnimalsTab qproperty-alertFill / qproperty-alertText)
    "danger.alert": ("#DC2626", "#DC2626"),
    "danger.on-alert": ("#FFFFFF", "#FFFFFF"),
    # QLabel[variant="info"]
    "info.tint": ("#E0F2FE", "#0C4A6E"),
    "info.on-tint": ("#0C4A6E", "#BAE6FD"),
    "info.indicator": ("#0284C7", "#0284C7"),
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
