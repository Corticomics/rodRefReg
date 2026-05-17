# help_content_manager.py
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote, unquote

# ---------------------------------------------------------------------------
# Palette — used by _format_content and get_landing_page / get_topic_not_found
# ---------------------------------------------------------------------------
_PALETTE = {
    'light': {
        'page_bg':      '#FFFFFF',
        'text':         '#1A1D1F',
        'h1':           '#0D9488',
        'h2':           '#1A1D1F',
        'muted':        '#4E5D6C',
        'link':         '#0D9488',
        'note_bg':      '#E6FFFA',
        'note_border':  '#0D9488',
        'warn_bg':      '#FEE2E2',
        'warn_border':  '#EF4444',
        'tip_bg':       '#D1FAE5',
        'tip_border':   '#10B981',
        'hl_bg':        '#FDE68A',
    },
    'dark': {
        'page_bg':      '#1A2028',
        'text':         '#F0F4F8',
        'h1':           '#2DD4BF',
        'h2':           '#F0F4F8',
        'muted':        '#A0AEC0',
        'link':         '#5EEAD4',
        'note_bg':      '#134E4A',
        'note_border':  '#2DD4BF',
        'warn_bg':      '#7F1D1D',
        'warn_border':  '#EF4444',
        'tip_bg':       '#064E3B',
        'tip_border':   '#10B981',
        'hl_bg':        '#92400E',
    },
}

def _css(theme: str) -> str:
    p = _PALETTE.get(theme, _PALETTE['light'])
    return f"""
body, .help-section {{
    font-family: "IBM Plex Sans", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    line-height: 1.6;
    color: {p['text']};
    background-color: {p['page_bg']};
    margin: 0;
    padding: 20px 24px 32px 24px;
}}
h1 {{
    color: {p['h1']};
    font-size: 22px;
    font-weight: 700;
    margin-top: 0;
    margin-bottom: 12px;
}}
h2 {{
    color: {p['h2']};
    font-size: 16px;
    font-weight: 600;
    margin-top: 20px;
    margin-bottom: 8px;
}}
p {{
    margin: 8px 0 12px 0;
}}
ul, ol {{
    margin: 8px 0 12px 0;
    padding-left: 24px;
}}
li {{
    margin-bottom: 4px;
}}
a {{
    color: {p['link']};
    text-decoration: none;
}}
a:hover {{
    text-decoration: underline;
}}
strong {{
    font-weight: 600;
}}
code {{
    font-family: "IBM Plex Mono", "Courier New", monospace;
    font-size: 12px;
    background: rgba(128,128,128,0.12);
    padding: 1px 4px;
    border-radius: 3px;
}}
.help-section {{
    padding: 0;
}}
.help-note, .help-warning, .help-tip {{
    padding: 12px 16px;
    border-radius: 6px;
    margin: 14px 0;
    border-left: 4px solid;
}}
.help-note {{
    background-color: {p['note_bg']};
    border-left-color: {p['note_border']};
}}
.help-warning {{
    background-color: {p['warn_bg']};
    border-left-color: {p['warn_border']};
}}
.help-tip {{
    background-color: {p['tip_bg']};
    border-left-color: {p['tip_border']};
}}
.related-topics {{
    margin-top: 28px;
    padding-top: 14px;
    border-top: 1px solid rgba(128,128,128,0.2);
    font-size: 12px;
    color: {p['muted']};
}}
.related-topics a {{
    color: {p['link']};
    margin-right: 14px;
}}
mark, .search-hl {{
    background-color: {p['hl_bg']};
    border-radius: 2px;
    padding: 0 2px;
}}
"""


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class HelpContent:
    title: str
    summary: str
    content: str            # HTML body fragment — no <style>
    keywords: List[str]
    related_topics: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Information Architecture
# ---------------------------------------------------------------------------
# category -> ordered list of topic keys.  Every key must have an entry below.
_IA: Dict[str, List[str]] = {
    "Getting Started": [
        "System Overview",
        "First Time Setup",
        "Basic Operations",
    ],
    "Animals": [
        "Adding & Managing Animals",
    ],
    "Water Delivery": [
        "Creating Schedules",
        "Safety Features",
    ],
    "Hardware": [
        "Hardware Setup & Maintenance",
        "Hardware Specifications",
    ],
    "Support": [
        "Troubleshooting",
    ],
}

# ---------------------------------------------------------------------------
# Content definitions  (single source of truth — IA and content together)
# ---------------------------------------------------------------------------
def _build_content() -> Dict[str, HelpContent]:
    return {
        # ----------------------------------------------------------------
        # GETTING STARTED
        # ----------------------------------------------------------------
        "System Overview": HelpContent(
            title="System Overview and Architecture",
            summary="Understand how the RRR components work together to deliver water.",
            content="""
<div class='help-section'>
  <h1>Understanding the RRR System</h1>
  <p>The Rodent Refreshment Regulator (RRR) is designed to automatically deliver water to
  your research animals with high precision and safety.  It integrates hardware, software,
  and scheduling so every animal receives the correct volume at the right time.</p>
  <h2>Main Components</h2>
  <ul>
    <li><strong>Animals Tab:</strong> Register and monitor research subjects.</li>
    <li><strong>Schedules Tab:</strong> Create and manage water delivery schedules.</li>
    <li><strong>Hardware Interface:</strong> Controls pumps and relay units for precise delivery.</li>
    <li><strong>Monitoring Dashboard:</strong> Provides real-time system status and alerts.</li>
    <li><strong>Settings Tab:</strong> Adjust calibration, pump volume, and safety limits.</li>
  </ul>
  <h2>How It Works</h2>
  <p>The system calculates the number of pump triggers required for each animal based on
  its weight and your chosen water volume.  It then schedules those triggers according to
  the selected delivery mode (Instant or Staggered), ensuring safe and accurate delivery.</p>
  <h2>Quick Start</h2>
  <ol>
    <li><strong>Log In or Use Guest Mode</strong> — sign in to access full features or use
    guest mode for testing (saving schedules requires an account).</li>
    <li><strong>Register Your Animals</strong> — provide unique IDs, names, and weights.</li>
    <li><strong>Create a Schedule</strong> — choose Instant or Staggered delivery mode.</li>
    <li><strong>Check Your Hardware</strong> — verify pumps, relay units, and relay hats are
    connected and pass the hardware test.</li>
    <li><strong>Run Your Experiment</strong> — press <strong>Run</strong> and monitor the
    System Messages for real-time updates.</li>
  </ol>
  <div class='help-note'>
    <strong>Tip for New Users:</strong> Familiarise yourself with each component before starting
    a full experiment — the First Time Setup guide walks you through every step.
  </div>
</div>
""",
            keywords=["system overview", "architecture", "components", "workflow", "quick start",
                      "introduction", "getting started"],
            related_topics=["First Time Setup", "Basic Operations"],
        ),

        "First Time Setup": HelpContent(
            title="First Time Setup Guide",
            summary="Step-by-step guide for hardware checks, account creation, and calibration.",
            content="""
<div class='help-section'>
  <h1>First Time Setup for RRR</h1>
  <p>Follow this guide before running your first experiment to ensure every component is
  configured and tested correctly.</p>
  <h2>1 — Hardware Check</h2>
  <ul>
    <li>Verify that all pump units, relay units, and relay hats are connected properly.</li>
    <li>Ensure all cables and power supplies are secure.</li>
  </ul>
  <h2>2 — User Account Setup</h2>
  <ul>
    <li>Create an administrator account if you haven't already.</li>
    <li>Configure user roles to control access and permissions.</li>
  </ul>
  <h2>3 — Calibration and Testing</h2>
  <ul>
    <li>Open the <strong>Settings</strong> tab and run the pump calibration test to confirm
    each pump delivers the expected volume (default: 50 µL per trigger).</li>
    <li>Use the <em>Change Relay Hats</em> feature to verify all relay units are working.</li>
  </ul>
  <h2>4 — Full System Test</h2>
  <ul>
    <li>Create a short trial schedule and run it.</li>
    <li>Check that water is delivered accurately and that System Messages report no errors.</li>
  </ul>
  <div class='help-warning'>
    <strong>Warning:</strong> Do not start a full experiment until every component passes its
    hardware test.
  </div>
</div>
""",
            keywords=["first time setup", "initial setup", "calibration", "hardware test",
                      "account setup"],
            related_topics=["System Overview", "Hardware Setup & Maintenance", "Basic Operations"],
        ),

        "Basic Operations": HelpContent(
            title="Basic Daily Operations",
            summary="The everyday tasks needed to run the RRR smoothly.",
            content="""
<div class='help-section'>
  <h1>Basic System Operations</h1>
  <p>This guide covers the day-to-day tasks you need to keep RRR running smoothly.</p>
  <h2>System Startup</h2>
  <ol>
    <li>Power on your RRR system.</li>
    <li>Log in with your credentials (or use guest mode for testing).</li>
    <li>Check the <strong>System Messages</strong> for any startup errors.</li>
  </ol>
  <h2>Animal and Data Management</h2>
  <ol>
    <li>Update animal weights and other data in the <strong>Animals</strong> tab.</li>
    <li>Ensure the recommended water volumes are recalculated based on updated weights.</li>
    <li>Review the animal list for any discrepancies.</li>
  </ol>
  <h2>Schedule Verification</h2>
  <ol>
    <li>Open the <strong>Schedules</strong> tab to view active and upcoming water delivery
    schedules.</li>
    <li>Monitor delivery logs and System Messages during water delivery.</li>
  </ol>
  <div class='help-tip'>
    <strong>Pro Tip:</strong> Use the dashboard view to get a quick status update on all
    active schedules.
  </div>
</div>
""",
            keywords=["basic operations", "daily tasks", "startup", "monitoring", "schedule"],
            related_topics=["First Time Setup", "Creating Schedules"],
        ),

        # ----------------------------------------------------------------
        # ANIMALS
        # ----------------------------------------------------------------
        "Adding & Managing Animals": HelpContent(
            title="Adding and Managing Research Subjects",
            summary="How to add animals, update records, and maintain accurate weight data.",
            content="""
<div class='help-section'>
  <h1>Adding and Managing Animals</h1>
  <p>Accurate animal records are essential for calculating safe water delivery volumes.  This
  guide explains how to register new animals and keep their data up to date.</p>
  <h2>Steps to Add an Animal</h2>
  <ol>
    <li>Go to the <strong>Animals</strong> tab.</li>
    <li>Click the <strong>Add Animal</strong> button.</li>
    <li>Fill in the required fields:
      <ul>
        <li><strong>Lab Animal ID:</strong> A unique identifier (e.g., "A001").</li>
        <li><strong>Name:</strong> The animal's name or code.</li>
        <li><strong>Initial Weight:</strong> Weight at registration (in grams).</li>
        <li><strong>Last Weight:</strong> Most recent weight, if available.</li>
        <li><strong>Time Stamps:</strong> When the animal was last weighed and watered.</li>
      </ul>
    </li>
    <li>Click <strong>Save</strong> to register the animal.</li>
  </ol>
  <h2>Editing and Monitoring</h2>
  <p>To update an animal's data, select it from the table and click <strong>Edit</strong>.
  Update weights daily so the system can calculate water volumes accurately.</p>
  <div class='help-warning'>
    <strong>Important:</strong> Inaccurate weight entries can lead to incorrect water volumes
    and compromise animal health.  Consistent, accurate measurements are critical for
    experimental reliability.
  </div>
</div>
""",
            keywords=["add animal", "manage animal", "edit animal", "health monitoring",
                      "data collection", "animal management", "weight"],
            related_topics=["Basic Operations", "Creating Schedules"],
        ),

        # ----------------------------------------------------------------
        # WATER DELIVERY
        # ----------------------------------------------------------------
        "Creating Schedules": HelpContent(
            title="Creating Water Delivery Schedules",
            summary="Set up Instant or Staggered delivery schedules and best practices.",
            content="""
<div class='help-section'>
  <h1>Water Delivery Scheduling</h1>
  <p>Schedules determine when and how much water is delivered.  RRR offers two delivery modes:</p>
  <ul>
    <li><strong>Instant Delivery:</strong> All animals receive water simultaneously.  Use for
    brief, synchronised hydration events.</li>
    <li><strong>Staggered Delivery:</strong> Water is dispensed gradually over a set period,
    spacing out pump triggers to minimise stress and hardware load.</li>
  </ul>
  <h2>How to Create a Schedule</h2>
  <ol>
    <li>Go to the <strong>Schedules</strong> tab and click <strong>Create New Schedule</strong>.</li>
    <li>Enter a descriptive schedule name and specify the total water volume.</li>
    <li>For <strong>Instant Delivery</strong>: choose specific delivery times for each animal.</li>
    <li>For <strong>Staggered Delivery</strong>: set the start and end times to define a
    delivery window.</li>
    <li>Assign animals to relay units — the system will calculate the number of pump triggers
    based on each animal's weight and calibration settings.</li>
    <li>Review your settings and click <strong>Save</strong>.</li>
  </ol>
  <h2>Best Practices</h2>
  <ul>
    <li>Double-check all time and volume settings before activation.</li>
    <li>Start with a short test schedule to verify delivery accuracy.</li>
    <li>Monitor System Messages during the experiment.</li>
  </ul>
  <div class='help-tip'>
    <strong>Tip:</strong> Use the suggestion feature to automatically generate optimal
    parameters based on historical data.  Always perform a test run before starting your
    full experiment.
  </div>
</div>
""",
            keywords=["schedule creation", "creating schedules", "water delivery", "instant",
                      "staggered", "setup", "schedule setup"],
            related_topics=["Safety Features", "Basic Operations", "Hardware Setup & Maintenance"],
        ),

        "Safety Features": HelpContent(
            title="Safety Features and Emergency Procedures",
            summary="Built-in volume limits, trigger spacing, emergency stop, and alerts.",
            content="""
<div class='help-section'>
  <h1>Safety Features and Emergency Procedures</h1>
  <p>The safety of your animals and equipment is the top priority.  RRR has several built-in
  mechanisms to prevent over-delivery and hardware damage.</p>
  <h2>Built-In Safety Mechanisms</h2>
  <ul>
    <li><strong>Volume Limits:</strong> The system calculates a maximum safe water volume based
    on each animal's weight and will not exceed it.</li>
    <li><strong>Trigger Spacing:</strong> Enforces a minimum interval between pump activations
    to prevent hardware overload.</li>
    <li><strong>Emergency Stop:</strong> Press the <strong>Stop</strong> button at any time to
    immediately halt all water delivery.</li>
  </ul>
  <h2>Alerts and Notifications</h2>
  <ul>
    <li>All errors and important system events are displayed in the
    <strong>System Messages</strong> area.</li>
    <li>If configured, Slack notifications will alert you of critical issues.</li>
  </ul>
  <h2>Emergency Procedures</h2>
  <ol>
    <li>Press the <strong>Stop</strong> button to abort any running schedule.</li>
    <li>Confirm that all relay units are deactivated.</li>
    <li>If necessary, manually override the system by disconnecting the power supply.</li>
  </ol>
  <div class='help-warning'>
    <strong>Important:</strong> Follow all emergency procedures carefully.  Only override
    safety settings if absolutely necessary and with full awareness of the consequences.
  </div>
</div>
""",
            keywords=["safety", "emergency", "stop", "alerts", "volume limits",
                      "trigger spacing", "notifications", "slack"],
            related_topics=["Creating Schedules", "Hardware Setup & Maintenance",
                            "Troubleshooting"],
        ),

        # ----------------------------------------------------------------
        # HARDWARE
        # ----------------------------------------------------------------
        "Hardware Setup & Maintenance": HelpContent(
            title="Hardware Setup and Maintenance",
            summary="Physical components, initial configuration, and maintenance procedures.",
            content="""
<div class='help-section'>
  <h1>Hardware Setup and Maintenance</h1>
  <p>This section details the physical components of RRR and how to keep them in good
  working order.</p>
  <h2>Components Overview</h2>
  <ul>
    <li><strong>Pump Units:</strong> Deliver water with high precision.  The default setting
    is 50 µL per trigger.</li>
    <li><strong>Relay Units and Hats:</strong> Control the pumps.  Each unit is assigned to
    specific animals.</li>
  </ul>
  <h2>Initial Hardware Configuration</h2>
  <ol>
    <li>Ensure all relay hats are properly installed and all relays are in the off state.</li>
    <li>Run the hardware test in the <strong>Settings</strong> tab to verify proper operation.</li>
  </ol>
  <h2>Maintenance Procedures</h2>
  <ul>
    <li><strong>Daily Checks:</strong> Visually inspect connections and verify no relays are
    inadvertently active.</li>
    <li><strong>Weekly Maintenance:</strong> Clean relay hats, recalibrate pumps, and check for
    any signs of wear or damage.</li>
  </ul>
  <div class='help-warning'>
    <strong>Critical:</strong> Always perform a full hardware test after any maintenance or
    configuration changes.
  </div>
</div>
""",
            keywords=["hardware setup", "maintenance", "pump calibration", "relay units",
                      "relay hats", "daily checks", "weekly maintenance"],
            related_topics=["First Time Setup", "Safety Features", "Hardware Specifications"],
        ),

        "Hardware Specifications": HelpContent(
            title="Hardware Specifications",
            summary="Detailed specs for the Raspberry Pi, relay HATs, pumps, and tubing.",
            content="""
<div class='help-section'>
    <h1>Hardware Configuration</h1>
    <p>The RRR system is built around specific hardware components chosen for their reliability
    and precision in laboratory settings.</p>

    <h2>Core Components</h2>
    <ul>
        <li><strong>Computer:</strong> Raspberry Pi 4B (or newer)
            <ul>
                <li>Recommended: 4 GB RAM or higher</li>
                <li>Running Raspberry Pi OS (formerly Raspbian)</li>
            </ul>
        </li>
        <li><strong>Relay Control:</strong> Sequent Microsystems 8-Layer Stackable HAT
            <ul>
                <li>Up to 8 layers per Pi</li>
                <li>16 relays per layer</li>
                <li>Operating voltage: 3.3 V (logic) / 12 V (pump control)</li>
            </ul>
        </li>
        <li><strong>Pumps:</strong> LeeCo 50 µL Precision Pumps
            <ul>
                <li>Model: LPMX Series</li>
                <li>Calibrated volume: 50 µL per trigger</li>
                <li>Operating voltage: 12 V DC</li>
            </ul>
        </li>
    </ul>

    <h2>Custom Hardware</h2>
    <ul>
        <li><strong>3D Printed Components:</strong>
            <ul>
                <li>Pump mounting brackets</li>
                <li>Water delivery cup holders</li>
                <li>Cable management systems</li>
                <li>Reservoir support structures</li>
            </ul>
        </li>
        <li><strong>Water Delivery System:</strong>
            <ul>
                <li>2 mm internal diameter tubing</li>
                <li>Custom water delivery cups</li>
                <li>20 L main reservoir</li>
            </ul>
        </li>
    </ul>

    <div class='help-note'>
        <strong>Note:</strong> 3D printing files for custom components are available in the
        project repository.
    </div>

    <h2>Laboratory Setup</h2>
    <p>The system is designed for standard laboratory rack systems with the following
    configuration:</p>
    <ul>
        <li>Rack-mounted pump arrays</li>
        <li>Gravity-fed water distribution</li>
        <li>Individual cage mounting brackets</li>
        <li>Central control cabinet</li>
    </ul>

    <div class='help-warning'>
        <strong>Important:</strong> Always ensure proper grounding and water-tight connections
        before operation.
    </div>
</div>
""",
            keywords=["hardware", "raspberry pi", "pumps", "relay", "setup", "3d printing",
                      "specifications", "hardware details"],
            related_topics=["Hardware Setup & Maintenance", "Safety Features", "Troubleshooting"],
        ),

        # ----------------------------------------------------------------
        # SUPPORT
        # ----------------------------------------------------------------
        "Troubleshooting": HelpContent(
            title="Troubleshooting Common Issues",
            summary="Diagnose hardware, schedule, software, and notification problems.",
            content="""
<div class='help-section'>
  <h1>Troubleshooting and Common Issues</h1>
  <p>If you encounter problems while using RRR, this guide will help you diagnose and resolve
  them.</p>
  <h2>Hardware Connection Issues</h2>
  <ul>
    <li><strong>Cable and Connector Check:</strong> Ensure all cables are securely connected
    and relay hats are properly installed.</li>
    <li><strong>Pump Calibration:</strong> If water volumes are off, re-run the calibration
    test in the <strong>Settings</strong> tab.</li>
  </ul>
  <h2>Schedule and Software Errors</h2>
  <ul>
    <li><strong>Invalid Schedule Settings:</strong> Check that start/end times, animal
    assignments, and water volumes are entered correctly.</li>
    <li><strong>System Messages:</strong> Review terminal output for error messages that
    indicate what might be wrong.</li>
  </ul>
  <h2>Notification Issues</h2>
  <ul>
    <li>Ensure your Slack credentials and channel ID are correct in the Notifications
    settings.</li>
    <li>Verify that your internet connection is stable.</li>
  </ul>
  <div class='help-tip'>
    <strong>Tip:</strong> Always use the <strong>Stop</strong> button to abort a schedule
    before restarting the system.  Note any error messages and consult this guide for
    potential fixes.
  </div>
</div>
""",
            keywords=["troubleshooting", "errors", "issues", "problem solving",
                      "hardware connection", "pump calibration", "notifications", "slack"],
            related_topics=["Safety Features", "Hardware Setup & Maintenance", "Basic Operations"],
        ),
    }


# ---------------------------------------------------------------------------
# Manager class
# ---------------------------------------------------------------------------
class HelpContentManager:
    def __init__(self) -> None:
        self._content: Dict[str, HelpContent] = _build_content()
        self._ia: Dict[str, List[str]] = _IA
        # Validate — every IA key must have content
        for cat, topics in self._ia.items():
            for key in topics:
                assert key in self._content, (
                    f"IA topic '{key}' under '{cat}' has no HelpContent entry."
                )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_categories(self) -> Dict[str, List[str]]:
        """Returns the category -> topic-keys mapping (insertion-ordered)."""
        return dict(self._ia)

    def get_topic(self, key: str) -> Optional[HelpContent]:
        """Returns the HelpContent for *key*, or None if not found."""
        return self._content.get(key)

    def get_content(self, topic_key: str, theme: str = 'light') -> str:
        """Full standalone HTML document for QTextBrowser."""
        hc = self._content.get(topic_key)
        if hc is None:
            return self.get_topic_not_found(theme)
        related_html = self._related_html(topic_key, theme)
        body = hc.content + related_html
        return self._format_content(body, theme)

    def get_landing_page(self, theme: str = 'light') -> str:
        """Welcoming Help Center home page with category/topic links."""
        p = _PALETTE.get(theme, _PALETTE['light'])
        rows = []
        for cat, topics in self._ia.items():
            topic_links = "".join(
                f"<li><a href='topic://{quote(k)}'>{k}</a></li>"
                for k in topics
            )
            rows.append(
                f"<div class='lp-cat'>"
                f"<h2>{cat}</h2>"
                f"<ul>{topic_links}</ul>"
                f"</div>"
            )
        categories_html = "\n".join(rows)
        body = f"""
<div class='help-section'>
  <h1>Help Center</h1>
  <p>Welcome to the Rodent Refreshment Regulator help documentation.  Select a topic from
  the list on the left, or browse the categories below.</p>
  <div class='lp-grid'>
    {categories_html}
  </div>
</div>
"""
        extra_css = f"""
.lp-grid {{ display: block; margin-top: 16px; }}
.lp-cat {{ margin-bottom: 20px; }}
.lp-cat h2 {{ color: {p['h1']}; font-size: 14px; font-weight: 600; margin-bottom: 4px; }}
.lp-cat ul {{ margin: 0; padding-left: 20px; }}
.lp-cat li {{ margin-bottom: 3px; }}
"""
        return self._format_content(body, theme, extra_css=extra_css)

    def get_topic_not_found(self, theme: str = 'light') -> str:
        """Graceful fallback page."""
        body = """
<div class='help-section'>
  <h1>Topic Not Found</h1>
  <p>The requested help topic could not be found.  Please select a topic from the panel on
  the left, or use the search bar to find what you are looking for.</p>
</div>
"""
        return self._format_content(body, theme)

    def search(self, query: str) -> List[Tuple[str, str]]:
        """
        Case-insensitive ranked search.
        Returns [(topic_key, snippet), ...].
        Rank: title match > keyword match > body text match.
        Empty query -> empty list.
        """
        q = query.strip()
        if not q:
            return []
        ql = q.lower()

        title_hits: List[Tuple[str, str]] = []
        kw_hits:    List[Tuple[str, str]] = []
        body_hits:  List[Tuple[str, str]] = []

        for key, hc in self._content.items():
            if ql in hc.title.lower():
                title_hits.append((key, hc.summary))
                continue
            if any(ql in kw.lower() for kw in hc.keywords):
                kw_hits.append((key, hc.summary))
                continue
            plain = _strip_html(hc.content)
            idx = plain.lower().find(ql)
            if idx >= 0:
                start = max(0, idx - 60)
                end   = min(len(plain), idx + 80)
                snippet = ("…" if start > 0 else "") + plain[start:end].strip() + "…"
                body_hits.append((key, snippet))

        return title_hits + kw_hits + body_hits

    def get_related(self, topic_key: str) -> List[str]:
        """Related topic keys filtered to only those that exist in the IA."""
        hc = self._content.get(topic_key)
        if hc is None:
            return []
        all_keys = {k for topics in self._ia.values() for k in topics}
        return [k for k in hc.related_topics if k in all_keys]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _related_html(self, topic_key: str, theme: str) -> str:
        related = self.get_related(topic_key)
        if not related:
            return ""
        p = _PALETTE.get(theme, _PALETTE['light'])
        links = "".join(
            f"<a href='topic://{quote(k)}'>{k}</a>"
            for k in related
        )
        return f"<div class='related-topics'><strong>Related topics:</strong> {links}</div>"

    def _format_content(self, html_body: str, theme: str,
                        extra_css: str = "") -> str:
        """Wrap html_body in a full HTML document with appropriate <style>."""
        css = _css(theme) + extra_css
        p = _PALETTE.get(theme, _PALETTE['light'])
        return (
            f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<style>{css}</style></head>"
            f"<body style='background-color:{p['page_bg']};'>{html_body}</body></html>"
        )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
_TAG_RE = re.compile(r'<[^>]+>')

def _strip_html(html: str) -> str:
    """Remove HTML tags and collapse whitespace for snippet/search use."""
    text = _TAG_RE.sub(' ', html)
    return re.sub(r'\s+', ' ', text).strip()
