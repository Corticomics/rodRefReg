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
        'page_bg': '#FFFFFF',
        'text': '#1A1D1F',
        'h1': '#0D9488',
        'h2': '#1A1D1F',
        'muted': '#4E5D6C',
        'link': '#0D9488',
        'note_bg': '#E6FFFA',
        'note_border': '#0D9488',
        'warn_bg': '#FEE2E2',
        'warn_border': '#EF4444',
        'tip_bg': '#D1FAE5',
        'tip_border': '#10B981',
        'hl_bg': '#FDE68A',
    },
    'dark': {
        'page_bg': '#1A2028',
        'text': '#F0F4F8',
        'h1': '#2DD4BF',
        'h2': '#F0F4F8',
        'muted': '#A0AEC0',
        'link': '#5EEAD4',
        'note_bg': '#134E4A',
        'note_border': '#2DD4BF',
        'warn_bg': '#7F1D1D',
        'warn_border': '#EF4444',
        'tip_bg': '#064E3B',
        'tip_border': '#10B981',
        'hl_bg': '#92400E',
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
    content: str  # HTML body fragment — no <style>
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
    "Animals & Cages": [
        "Adding & Managing Animals",
        "Cages",
    ],
    "Water Delivery": [
        "Creating Schedules",
        "Schedule Wizard",
        "Execution Monitor",
        "Safety Features",
    ],
    "Hardware": [
        "Hardware Setup & Maintenance",
        "Hardware Modes",
        "Valve Calibration",
        "Priming",
        "Flow Sensor",
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
            title="System Overview",
            summary="UI map and workflow summary for the Rodent Refreshment Regulator.",
            content="""
<div class='help-section'>
  <h1>System Overview</h1>
  <p>The <strong>Rodent Refreshment Regulator (RRR)</strong> automates precise water delivery
  to laboratory animals.  It integrates relay hardware, flow sensing, scheduling, and
  real-time monitoring in a single PyQt5 desktop application.</p>

  <h2>UI Layout</h2>
  <p>The window is split into two vertical panes:</p>
  <ul>
    <li><strong>Left pane</strong>
      <ul>
        <li><strong>Terminal tab</strong> — System Messages log (always visible).</li>
        <li><strong>Execution Monitor tab</strong> — per-animal progress cards; appears
        automatically when a schedule starts, hides ~10 seconds after completion.</li>
        <li>Below the tabbed area: a <strong>Projects</strong> section with four tabs:
          <strong>Schedules, Animals, Wizard, Cages</strong>.</li>
      </ul>
    </li>
    <li><strong>Right pane</strong>
      <ul>
        <li>A tab widget with three tabs: <strong>Profile, Settings, Help</strong>.</li>
        <li>Below the tabs: the <strong>Run/Stop</strong> control section (schedule queue,
        Run and Stop buttons, time window inputs).</li>
      </ul>
    </li>
  </ul>

  <h2>Access Control</h2>
  <p>The app starts in <strong>guest mode</strong>.  The <strong>Settings</strong> and
  <strong>Help</strong> tabs are disabled until you log in on the <strong>Profile</strong>
  tab.  In guest mode the Animals tab shows all animals; after login it shows only your
  own animals (or all animals in Super Mode).</p>

  <h2>Quick Start</h2>
  <ol>
    <li>Open the <strong>Profile</strong> tab and log in.</li>
    <li>Go to <strong>Settings → Delivery</strong> and confirm the hardware mode matches
    your physical setup (<code>solenoid</code> or <code>pump</code>).</li>
    <li>Add animals in the <strong>Animals</strong> tab.</li>
    <li>Calibrate valves in <strong>Settings → Calibration</strong>.</li>
    <li>Create a schedule via the <strong>Wizard</strong> tab or the <strong>Schedules</strong>
    tab.</li>
    <li>Press <strong>Run</strong> in the Run/Stop section and watch the
    <strong>Execution Monitor</strong>.</li>
  </ol>

  <div class='help-note'>
    <strong>Note:</strong> All important system events appear in the
    <strong>System Messages</strong> terminal on the left pane.  Check it whenever
    something unexpected occurs.
  </div>
</div>
""",
            keywords=[
                "overview",
                "ui layout",
                "interface",
                "panes",
                "tabs",
                "guest mode",
                "login",
                "workflow",
                "getting started",
                "introduction",
                "map",
            ],
            related_topics=["First Time Setup", "Basic Operations", "Execution Monitor"],
        ),
        "First Time Setup": HelpContent(
            title="First Time Setup",
            summary="Log in, choose hardware mode, configure the flow sensor, calibrate, and test.",
            content="""
<div class='help-section'>
  <h1>First Time Setup</h1>
  <p>Complete these steps before running your first experiment.  They only need to be done
  once per installation (or after significant hardware changes).</p>

  <h2>1 — Log In</h2>
  <p>Open the <strong>Profile</strong> tab and log in.  This unlocks the
  <strong>Settings</strong> and <strong>Help</strong> tabs.</p>

  <h2>2 — Choose Hardware Mode</h2>
  <p>Go to <strong>Settings → Delivery</strong> and set the <strong>Hardware Mode</strong>
  to match your physical hardware: <code>solenoid</code> (default) or <code>pump</code>.
  See the <em>Hardware Modes</em> topic for details.</p>

  <div class='help-warning'>
    <strong>Warning:</strong> The mode must match what is physically installed.  A mismatch
    will cause incorrect delivery or hardware damage.
  </div>

  <h2>3 — Configure the Flow Sensor (Solenoid Mode)</h2>
  <ul>
    <li>In <strong>Settings → Delivery → Flow Sensor (Teensy Bridge)</strong>, enter the
    serial port for the Teensy microcontroller (default: <code>/dev/teensy_flow</code>).</li>
    <li>Click <strong>Auto-Detect</strong> to let the app find the port automatically, or
    enter it manually.</li>
    <li>Click <strong>Test</strong> to verify the connection.</li>
    <li>If the flow sensor is not always connected, enable
    <em>Allow schedules without flow sensor</em> so deliveries fall back to calibration
    values.</li>
  </ul>

  <h2>4 — Calibrate Valves / Pumps</h2>
  <p>Open <strong>Settings → Calibration</strong>.  Click <strong>Calibrate</strong> for
  each cage (or <em>Calibrate All Uncalibrated</em> for a batch run).  Follow the on-screen
  wizard — you will need a lab scale accurate to ±0.001 g.  Calibration data is saved to
  the database and used for all future deliveries.</p>

  <h2>5 — Test Run</h2>
  <ul>
    <li>Add at least one animal in the <strong>Animals</strong> tab.</li>
    <li>Create a short schedule using the <strong>Wizard</strong> tab.</li>
    <li>Press <strong>Run</strong> and confirm that the
    <strong>Execution Monitor</strong> appears and progress cards advance.</li>
    <li>Check the <strong>System Messages</strong> terminal for any errors.</li>
  </ul>

  <div class='help-tip'>
    <strong>Tip:</strong> Run the Priming procedure (<strong>Settings → Priming</strong>)
    before your very first water delivery to flush air from the lines.
  </div>
</div>
""",
            keywords=[
                "first time",
                "initial setup",
                "login",
                "hardware mode",
                "solenoid",
                "pump",
                "flow sensor",
                "teensy",
                "calibration",
                "priming",
                "setup",
                "configure",
            ],
            related_topics=[
                "System Overview",
                "Hardware Modes",
                "Valve Calibration",
                "Priming",
                "Flow Sensor",
                "Basic Operations",
            ],
        ),
        "Basic Operations": HelpContent(
            title="Basic Daily Operations",
            summary="Daily workflow: log in, check messages, update animals, build and run a schedule.",
            content="""
<div class='help-section'>
  <h1>Basic Daily Operations</h1>
  <p>Follow this routine each day to keep experiments running smoothly.</p>

  <h2>1 — Log In and Check System Messages</h2>
  <ol>
    <li>Open the <strong>Profile</strong> tab and log in.</li>
    <li>Glance at the <strong>System Messages</strong> terminal (left pane) for any errors
    or warnings from previous sessions.</li>
  </ol>

  <h2>2 — Update Animal Records</h2>
  <ol>
    <li>Go to the <strong>Animals</strong> tab in the Projects section.</li>
    <li>Select each animal and click <strong>Edit</strong> to update its current weight
    and last-watered timestamp.</li>
    <li>Accurate weights are used to compute target delivery volumes.</li>
  </ol>

  <h2>3 — Create or Load a Schedule</h2>
  <ol>
    <li>Use the <strong>Wizard</strong> tab for a guided 4-step setup, or open the
    <strong>Schedules</strong> tab to load a saved schedule.</li>
    <li>Select the <strong>Delivery Mode</strong> (Staggered or Instant) in the Schedules
    tab if building manually.</li>
    <li>Assign animals to cages, set volumes and time windows, then save.</li>
  </ol>

  <h2>4 — Run the Schedule</h2>
  <ol>
    <li>In the Run/Stop section (right pane, below the tabs), select the schedule and set
    the execution window.</li>
    <li>Click <strong>Run</strong>.  The <strong>Execution Monitor</strong> tab
    automatically appears in the left pane with a progress card for each animal.</li>
    <li>Monitor the <strong>System Messages</strong> terminal for real-time status.</li>
    <li>After completion, cards show final status for ~10 seconds, then the tab hides.</li>
  </ol>

  <h2>5 — Stop If Needed</h2>
  <p>Press <strong>Stop</strong> at any time to immediately halt all water delivery.
  All relay units are deactivated and the event is logged in System Messages.</p>

  <div class='help-tip'>
    <strong>Tip:</strong> Switch to <strong>Super Mode</strong> (Settings → General →
    User Mode) to view and manage all animals and schedules across all users.
  </div>
</div>
""",
            keywords=[
                "daily operations",
                "workflow",
                "run",
                "stop",
                "login",
                "animals",
                "schedule",
                "execution monitor",
                "system messages",
                "super mode",
                "normal mode",
            ],
            related_topics=[
                "First Time Setup",
                "Creating Schedules",
                "Execution Monitor",
                "Safety Features",
            ],
        ),
        # ----------------------------------------------------------------
        # ANIMALS & CAGES
        # ----------------------------------------------------------------
        "Adding & Managing Animals": HelpContent(
            title="Adding and Managing Animals",
            summary="Use the Animals tab to register subjects, update weights, and search records.",
            content="""
<div class='help-section'>
  <h1>Adding and Managing Animals</h1>
  <p>The <strong>Animals</strong> tab (Projects section, left pane) is the central registry
  for all research subjects.  Accurate records are essential for computing safe delivery
  volumes.</p>

  <h2>Animal Table Columns</h2>
  <ul>
    <li><strong>Lab Animal ID</strong> — unique identifier (e.g., ear-tag number).</li>
    <li><strong>Name</strong> — a descriptive label.</li>
    <li><strong>Sex</strong> — male, female, or unspecified.</li>
    <li><strong>Initial Weight (g)</strong> — body weight at registration.</li>
    <li><strong>Last Weight (g)</strong> — most recent measured weight.</li>
    <li><strong>Last Weighted</strong> — timestamp of last weighing (shown as relative
    time, e.g., "2 days ago").</li>
    <li><strong>Last Watering</strong> — timestamp of the most recent water delivery.</li>
  </ul>

  <h2>Adding an Animal</h2>
  <ol>
    <li>Click <strong>Add Animal</strong>.</li>
    <li>Fill in: Lab Animal ID (required), Name (required), Initial Weight (required),
    Last Weight, Last Weighted, Last Watering, and Sex.</li>
    <li>Click <strong>Save</strong>.  The animal appears in the table immediately.</li>
  </ol>

  <h2>Editing an Animal</h2>
  <ol>
    <li>Select the animal row in the table.</li>
    <li>Click <strong>Edit</strong> to open the edit dialog.</li>
    <li>Update the fields and save.  The Schedules tab refreshes automatically.</li>
  </ol>

  <h2>Removing an Animal</h2>
  <p>Select the row and click <strong>Remove</strong>.  Confirm the prompt.  Removal
  is permanent.</p>

  <h2>Filtering</h2>
  <p>Use the <strong>Search</strong> field above the table to filter animals by any
  column value in real time.</p>

  <h2>Access and Modes</h2>
  <ul>
    <li>In <strong>guest mode</strong>, all animals are visible (read-only).</li>
    <li>When logged in (<strong>Normal Mode</strong>), you see only your own animals.</li>
    <li>In <strong>Super Mode</strong>, all animals across all users are shown.</li>
  </ul>

  <div class='help-warning'>
    <strong>Warning:</strong> Keep weights current.  Stale or incorrect weights lead to
    inaccurate volume calculations and can compromise animal welfare.
  </div>
</div>
""",
            keywords=[
                "add animal",
                "edit animal",
                "remove animal",
                "weight",
                "lab animal id",
                "sex",
                "filter",
                "search",
                "guest mode",
                "super mode",
                "animals tab",
            ],
            related_topics=["Basic Operations", "Creating Schedules", "Cages"],
        ),
        "Cages": HelpContent(
            title="Cages",
            summary="The Cages tab shows the relay board layout and lets you name each cage.",
            content="""
<div class='help-section'>
  <h1>Cages</h1>
  <p>The <strong>Cages</strong> tab (Projects section, left pane) provides a visual
  representation of the physical relay HAT board, mapping each relay terminal to a cage.</p>

  <h2>Board Layout</h2>
  <p>The tab shows a diagram of the relay board flanked by two columns of relay terminals:</p>
  <ul>
    <li><strong>Left column (R1–R8)</strong> — left-side terminals on the HAT.</li>
    <li><strong>Right column (R16–R9)</strong> — right-side terminals, with R16 reserved
    as the master solenoid.</li>
  </ul>
  <p>Each terminal badge shows the relay number and the custom cage name.</p>

  <h2>Renaming a Cage</h2>
  <ol>
    <li>Double-click on any non-master terminal.</li>
    <li>Type the new name directly in the inline editor.</li>
    <li>Press <strong>Enter</strong> or click elsewhere to save.  Press
    <strong>Escape</strong> to cancel.</li>
  </ol>
  <p>Names are saved to the database immediately and reflected in the
  <strong>Calibration</strong> table and the wizard's cage-assignment dropdowns.</p>

  <h2>Master Solenoid (R16)</h2>
  <p>Relay 16 is the master solenoid that controls the shared water supply line.  It is
  always reserved and cannot be assigned to a cage.  The Priming panel requires the master
  solenoid to be open before individual cage relays can be opened.</p>

  <div class='help-tip'>
    <strong>Tip:</strong> Name cages after their physical location (e.g., "Rack A Row 1")
    to make schedule setup and calibration much faster.
  </div>
</div>
""",
            keywords=[
                "cages",
                "relay board",
                "cage name",
                "rename cage",
                "relay terminal",
                "master solenoid",
                "r16",
                "hat",
                "layout",
                "visualization",
            ],
            related_topics=[
                "Adding & Managing Animals",
                "Valve Calibration",
                "Priming",
                "Hardware Setup & Maintenance",
            ],
        ),
        # ----------------------------------------------------------------
        # WATER DELIVERY
        # ----------------------------------------------------------------
        "Creating Schedules": HelpContent(
            title="Creating Schedules",
            summary="Use the Schedules tab to assign animals to cages and choose Staggered or Instant mode.",
            content="""
<div class='help-section'>
  <h1>Creating Schedules</h1>
  <p>The <strong>Schedules</strong> tab (Projects section) is a three-column view for
  building and managing water delivery schedules without the step-by-step wizard.</p>

  <h2>Delivery Modes</h2>
  <p>Select a mode with the <strong>Delivery Mode</strong> selector at the top of the
  Available Animals column:</p>
  <ul>
    <li><strong>Staggered</strong> (default, recommended) — deliveries are spaced evenly
    across a time window.  Each animal has a start time, end time, and target volume.
    The system distributes triggers automatically within that window.</li>
    <li><strong>Instant</strong> — each animal receives water at a specific point in time
    you define.  Use for synchronised hydration events.</li>
  </ul>

  <h2>Building a Schedule Manually</h2>
  <ol>
    <li>Select the <strong>Delivery Mode</strong>.</li>
    <li>Drag an animal from the <strong>Available Animals</strong> list (left column) onto
    a relay unit slot in the <strong>Relay Units</strong> column (centre).</li>
    <li>Configure the time window and volume for each relay unit slot.</li>
    <li>Click <strong>Save Current Assignments</strong> to name and save the schedule.</li>
  </ol>

  <h2>Loading a Saved Schedule</h2>
  <p>Saved schedules appear in the <strong>Saved Schedules</strong> column (right).
  Click a schedule to load its assignments back into the relay unit slots.  You can also
  drag a saved schedule to the Run/Stop section to execute it directly.</p>

  <h2>Clearing Assignments</h2>
  <p>Click <strong>Clear All Assignments</strong> to reset all relay unit slots without
  deleting saved schedules.</p>

  <div class='help-note'>
    <strong>Note:</strong> For guided schedule creation, use the <strong>Wizard</strong>
    tab instead.  The Wizard enforces hardware limits and cage assignments at each step.
  </div>
</div>
""",
            keywords=[
                "schedules",
                "staggered",
                "instant",
                "delivery mode",
                "relay unit",
                "assign animals",
                "save schedule",
                "load schedule",
                "water delivery",
                "drag drop",
                "time window",
                "volume",
            ],
            related_topics=[
                "Schedule Wizard",
                "Safety Features",
                "Execution Monitor",
                "Adding & Managing Animals",
            ],
        ),
        "Schedule Wizard": HelpContent(
            title="Schedule Wizard",
            summary="A 4-step guided flow for creating schedules: Type, Animals, Parameters, Review.",
            content="""
<div class='help-section'>
  <h1>Schedule Wizard</h1>
  <p>The <strong>Wizard</strong> tab (Projects section) walks you through schedule creation
  in four steps, enforcing hardware constraints at each stage.  You can also reach it by
  clicking <em>+ New Schedule</em> in the Schedules tab.</p>

  <h2>Step 1 — Select Schedule Type</h2>
  <p>Choose between <strong>Staggered Delivery</strong> (recommended — evenly distributed
  over a time window) and <strong>Instant Delivery</strong> (water at a precise point in
  time).  Click the card that matches your experiment design.</p>

  <h2>Step 2 — Select Animals</h2>
  <p>Choose which animals will receive water.  The wizard shows all animals available to
  you and enforces the hardware limit (up to 15 per relay HAT — relay 16 is reserved for
  the master solenoid).  Use <em>Select All</em> to fill available slots, or tick
  individual animals.</p>

  <h2>Step 3 — Configure Parameters</h2>
  <p>Set delivery parameters per animal:</p>
  <ul>
    <li><strong>Schedule Name</strong> — a descriptive label saved to the database.</li>
    <li><strong>Cage assignment</strong> — a filterable dropdown pre-populated with your
    cage names; defaults to sequential assignment.</li>
    <li><strong>Staggered mode</strong>: start time, end time, and volume (mL) per animal.
    Use <em>Apply to All</em> to set a global window, then fine-tune individually.</li>
    <li><strong>Instant mode</strong>: delivery datetime and volume per animal.</li>
  </ul>
  <p>The wizard validates that start is before end, volumes are positive, and no two animals
  share the same cage.</p>

  <h2>Step 4 — Review and Save</h2>
  <p>A summary shows the schedule type, name, and per-animal cage/time/volume settings.
  Click <strong>Finish</strong> to save to the database.  The Schedules tab refreshes
  automatically and you are returned to it.</p>

  <div class='help-tip'>
    <strong>Tip:</strong> You can navigate <em>Back</em> to any previous step to change
    your selections — the wizard preserves all entered values on back navigation.
  </div>
</div>
""",
            keywords=[
                "wizard",
                "schedule wizard",
                "guided",
                "4 step",
                "staggered",
                "instant",
                "cage assignment",
                "parameters",
                "review",
                "save schedule",
            ],
            related_topics=[
                "Creating Schedules",
                "Adding & Managing Animals",
                "Cages",
                "Execution Monitor",
            ],
        ),
        "Execution Monitor": HelpContent(
            title="Execution Monitor",
            summary="Real-time per-animal progress cards that appear automatically when a schedule runs.",
            content="""
<div class='help-section'>
  <h1>Execution Monitor</h1>
  <p>The <strong>Execution Monitor</strong> tab lives in the left pane alongside the
  System Messages terminal.  It is hidden when no schedule is running and appears
  automatically the moment you press <strong>Run</strong>.</p>

  <h2>What You See</h2>
  <p>Each animal in the running schedule gets its own <strong>progress card</strong>
  displayed in a grid (up to 4 cards per row).  Each card shows:</p>
  <ul>
    <li><strong>Animal ID</strong> and <strong>Cage badge</strong>.</li>
    <li>A <strong>progress bar</strong> (0–100%) reflecting volume delivered vs target.</li>
    <li><strong>Volume delivered / target</strong> in mL (e.g., <code>0.150 / 1.000 mL</code>).</li>
    <li><strong>Status</strong> — Waiting, Delivering, Paused, Complete, or Failed.</li>
  </ul>
  <p>A header shows the schedule name and an elapsed-time counter that updates every
  second.</p>

  <h2>Loading State</h2>
  <p>When you press Run, the tab becomes visible immediately with a "Loading…" message
  while database queries complete.  Cards are then populated progressively to keep the
  UI responsive.</p>

  <h2>Auto-Hide Behaviour</h2>
  <p>When the schedule completes (or is stopped), the view switches back to the Terminal
  tab.  The Execution Monitor tab remains visible for approximately 10 seconds so you
  can review final card statuses, then it hides and the cards are cleared.</p>

  <h2>Stopping a Schedule</h2>
  <p>Press <strong>Stop</strong> in the Run/Stop section at any time.  The monitor
  updates card statuses immediately and the 10-second hide timer begins.</p>

  <div class='help-note'>
    <strong>Note:</strong> All delivery events and errors are also logged in the
    <strong>System Messages</strong> terminal for a permanent text record.
  </div>
</div>
""",
            keywords=[
                "execution monitor",
                "progress",
                "cards",
                "run",
                "real time",
                "status",
                "delivering",
                "complete",
                "failed",
                "animal progress",
                "elapsed time",
                "auto hide",
                "monitoring",
            ],
            related_topics=[
                "Creating Schedules",
                "Schedule Wizard",
                "Safety Features",
                "Basic Operations",
            ],
        ),
        "Safety Features": HelpContent(
            title="Safety Features",
            summary="Volume limits, valve timeouts, the Stop button, alerts, and Slack notifications.",
            content="""
<div class='help-section'>
  <h1>Safety Features</h1>
  <p>RRR has several layers of protection to prevent over-delivery, hardware damage, and
  undetected failures.</p>

  <h2>Volume Limits</h2>
  <p>Schedules enforce a maximum volume per animal per delivery event.  The system will
  not exceed the configured target volume.</p>

  <h2>Solenoid Mode Safety (Settings → Delivery)</h2>
  <ul>
    <li><strong>Max Valve Open Time</strong> — emergency cutoff: valve closes automatically
    if open longer than this duration (default 20 s).</li>
    <li><strong>No-Flow Timeout</strong> — delivery aborts if the flow sensor detects no
    flow within this period (default 3.5 s), preventing an empty-line hang.</li>
    <li><strong>Predictive Close Lag</strong> — compensates for valve close latency to
    reduce overshoot (default 10 ms).</li>
  </ul>

  <h2>Stop Button</h2>
  <p>The <strong>Stop</strong> button in the Run/Stop section immediately halts all
  hardware activity.  All relay outputs are driven to off.  Use it whenever an
  unexpected situation arises.</p>

  <h2>System Messages Alerts</h2>
  <p>Every error, warning, and key event is timestamped and logged to the
  <strong>System Messages</strong> terminal.  Review this log after any abnormal run.</p>

  <h2>Slack Notifications (Optional)</h2>
  <p>Configure a Slack Bot Token and Channel ID in <strong>Settings → General →
  Slack Integration</strong>.  When configured, critical system events are sent as
  Slack messages, allowing remote monitoring.</p>

  <h2>Priming Safety Interlocks</h2>
  <p>In the Priming panel, individual cage relays cannot be opened unless the master
  solenoid is open first.  The <em>Close All Relays</em> emergency button closes
  every relay immediately.</p>

  <div class='help-warning'>
    <strong>Warning:</strong> If the Stop button does not respond, disconnect power from
    the relay HAT immediately.  Note any System Messages errors and consult
    Troubleshooting.
  </div>
</div>
""",
            keywords=[
                "safety",
                "stop",
                "emergency",
                "volume limits",
                "no-flow timeout",
                "max valve open",
                "slack",
                "notifications",
                "alerts",
                "system messages",
                "interlock",
                "cutoff",
            ],
            related_topics=[
                "Creating Schedules",
                "Execution Monitor",
                "Hardware Setup & Maintenance",
                "Troubleshooting",
            ],
        ),
        # ----------------------------------------------------------------
        # HARDWARE
        # ----------------------------------------------------------------
        "Hardware Setup & Maintenance": HelpContent(
            title="Hardware Setup and Maintenance",
            summary="Mode-agnostic setup procedures, relay HAT wiring, and daily/weekly maintenance.",
            content="""
<div class='help-section'>
  <h1>Hardware Setup and Maintenance</h1>
  <p>This guide covers physical setup and ongoing maintenance for both solenoid and pump
  hardware modes.</p>

  <h2>Initial Setup</h2>
  <ol>
    <li>Mount the relay HAT securely on the host computer (Raspberry Pi or compatible
    board).</li>
    <li>Wire each cage's valve or pump to its assigned relay terminal (R1–R15).  Refer to
    the <strong>Cages</strong> tab for the relay-to-cage mapping.</li>
    <li>Connect the master solenoid to relay R16 (solenoid mode).</li>
    <li>If using a Teensy flow-sensor bridge, connect it via USB.  Configure the serial
    port in <strong>Settings → Delivery</strong>.</li>
    <li>Power on hardware and verify all relay indicator lights are off (safe state).</li>
  </ol>

  <h2>Verifying Connections</h2>
  <ul>
    <li>Use the <strong>Priming</strong> panel (Settings → Priming) to manually open and
    close individual relays and confirm water flows through each cage line.</li>
    <li>Check the Calibration table (Settings → Calibration) — uncalibrated cages show
    a red "Not Calibrated" status.  Calibrate before running experiments.</li>
  </ul>

  <h2>Daily Checks</h2>
  <ul>
    <li>Inspect water connections for leaks.</li>
    <li>Verify the System Messages terminal shows no startup errors.</li>
    <li>Confirm the Teensy flow-sensor bridge is connected (solenoid mode).</li>
  </ul>

  <h2>Weekly Maintenance</h2>
  <ul>
    <li>Flush all lines using the Priming panel to clear any biofilm.</li>
    <li>Re-run valve calibration if measured volumes drift from targets.</li>
    <li>Inspect relay terminals and wiring for corrosion or wear.</li>
    <li>Update animal weights and review last-watering timestamps.</li>
  </ul>

  <div class='help-warning'>
    <strong>Critical:</strong> Never change hardware connections while a schedule is
    running.  Always press <strong>Stop</strong> first.
  </div>
</div>
""",
            keywords=[
                "hardware setup",
                "maintenance",
                "relay hat",
                "wiring",
                "solenoid",
                "pump",
                "daily check",
                "weekly maintenance",
                "connections",
                "priming",
                "calibration",
                "hat",
                "relay terminals",
            ],
            related_topics=[
                "Hardware Modes",
                "Valve Calibration",
                "Priming",
                "Flow Sensor",
                "Safety Features",
            ],
        ),
        "Hardware Modes": HelpContent(
            title="Hardware Modes",
            summary="Choose solenoid mode (default) or pump mode to match your physical hardware.",
            content="""
<div class='help-section'>
  <h1>Hardware Modes</h1>
  <p>RRR supports two delivery hardware modes.  The mode is set in
  <strong>Settings → Delivery → Delivery Hardware Mode</strong> and must exactly match
  what is physically installed.  Changing the mode while a schedule is running is blocked.</p>

  <h2>Solenoid Mode (Default)</h2>
  <p>In solenoid mode, each cage has a single solenoid valve wired to one relay (R1–R15).
  A master solenoid on R16 controls the shared water supply line.  Volume is measured in
  real time by a Teensy-based flow sensor via USB serial.</p>
  <ul>
    <li>One relay per cage — scalable to 15 cages per HAT.</li>
    <li>Real-time volumetric feedback from the flow sensor.</li>
    <li>Predictive valve close to minimize overshoot.</li>
    <li>Requires flow-sensor calibration per cage before first use.</li>
    <li>Can operate without the flow sensor if <em>Allow schedules without flow sensor</em>
    is enabled (falls back to calibration values).</li>
  </ul>

  <h2>Pump Mode (Legacy)</h2>
  <p>In pump mode, each relay unit controls a peristaltic pump using timed pulses.
  Two relays are paired per pump unit (e.g., unit 1 → relays 1 and 2).  Volume is
  estimated from pulse count × volume-per-trigger (configured in the Pump Mode Settings
  group).</p>
  <ul>
    <li>Two relays per pump unit — up to 8 units per HAT.</li>
    <li>No flow sensor required — time-based control.</li>
    <li>Set <strong>Pump Output Volume</strong> and <strong>Calibration Factor</strong>
    in Settings → Delivery → Pump Mode Settings.</li>
    <li>Less accurate than solenoid mode; recalibrate when pump tubing is replaced.</li>
  </ul>

  <h2>Choosing a Mode</h2>
  <ul>
    <li>Use <strong>solenoid</strong> for highest volumetric accuracy and real-time
    feedback.</li>
    <li>Use <strong>pump</strong> for legacy setups or environments where solenoid
    hardware is not available.</li>
  </ul>

  <div class='help-warning'>
    <strong>Warning:</strong> The software mode must match your physical hardware.
    Setting solenoid mode with pump hardware (or vice versa) will cause incorrect
    delivery volumes or hardware damage.
  </div>
</div>
""",
            keywords=[
                "hardware mode",
                "solenoid",
                "pump",
                "mode selector",
                "delivery mode",
                "relay unit",
                "pump mode",
                "solenoid mode",
                "peristaltic",
                "valve",
                "flow sensor",
                "legacy",
            ],
            related_topics=[
                "Hardware Setup & Maintenance",
                "Flow Sensor",
                "Valve Calibration",
                "First Time Setup",
            ],
        ),
        "Valve Calibration": HelpContent(
            title="Valve Calibration",
            summary="Per-cage empirical calibration using the Calibration tab and wizard.",
            content="""
<div class='help-section'>
  <h1>Valve Calibration</h1>
  <p>Calibration establishes the exact volume delivered per relay pulse for each cage
  valve.  Without calibration, deliveries use default values that may be inaccurate.</p>

  <h2>Calibration Table (Settings → Calibration)</h2>
  <p>The table shows all 15 cage slots with the following columns:</p>
  <ul>
    <li><strong>Cage</strong> — cage number and custom name.</li>
    <li><strong>Status</strong> — Calibrated (green) or Not Calibrated (red).</li>
    <li><strong>mL/Pulse</strong> — measured volume delivered per relay activation.</li>
    <li><strong>CV%</strong> — coefficient of variation (lower is better; &lt;5% is
    production-ready, &lt;1% is excellent).</li>
    <li><strong>Date</strong> — date of last calibration.</li>
    <li><strong>Action</strong> — <em>Calibrate</em> or <em>Recalibrate</em> button.</li>
  </ul>

  <h2>Running the Calibration Wizard</h2>
  <ol>
    <li>Click <strong>Calibrate</strong> next to a cage (or <em>Calibrate All
    Uncalibrated</em> for a batch).</li>
    <li>Follow the on-screen wizard — it will fire a characterization sequence (250 pulses
    by default).</li>
    <li>Weigh the collected water on a lab scale (accuracy ±0.001 g required).</li>
    <li>Enter the measured mass; the wizard computes mL/pulse and CV%.</li>
    <li>Confirm to save.  The calibration is immediately active for all future
    deliveries.</li>
  </ol>

  <h2>When to Recalibrate</h2>
  <ul>
    <li>After replacing tubing or valves.</li>
    <li>If measured delivery volumes drift from targets during an experiment.</li>
    <li>Routinely as part of weekly maintenance.</li>
    <li>After switching hardware modes.</li>
  </ul>

  <h2>Exporting Calibration Data</h2>
  <p>Click <strong>Export Report</strong> to save calibration data for all cages to a
  CSV file for lab records.</p>

  <div class='help-note'>
    <strong>Note:</strong> You must be logged in to calibrate.  Calibration actions are
    logged to the database with your trainer ID.  Calibration cannot run while a schedule
    is executing.
  </div>
</div>
""",
            keywords=[
                "calibration",
                "valve calibration",
                "ml per pulse",
                "cv%",
                "coefficient of variation",
                "calibrate",
                "recalibrate",
                "250 pulses",
                "lab scale",
                "export",
                "accuracy",
                "solenoid",
            ],
            related_topics=[
                "Hardware Modes",
                "Hardware Setup & Maintenance",
                "Priming",
                "Flow Sensor",
                "Troubleshooting",
            ],
        ),
        "Priming": HelpContent(
            title="Priming",
            summary="Use the Priming tab to flush air from water lines before running experiments.",
            content="""
<div class='help-section'>
  <h1>Priming</h1>
  <p>Priming is the process of opening valves manually to fill the water delivery lines
  and purge trapped air before an experiment.  Air bubbles in the lines cause erratic
  delivery volumes and should be eliminated before calibration or the first run of
  the day.</p>

  <h2>Priming Control Panel (Settings → Priming)</h2>
  <p>The panel has three sections:</p>
  <ul>
    <li><strong>Master Solenoid Control</strong> — open or close the master solenoid
    (R16) that supplies water to all cage lines.</li>
    <li><strong>Cage Relay Control</strong> — select a cage from the dropdown and open
    or close its individual relay.  The master must be open first (safety interlock).</li>
    <li><strong>Emergency Controls</strong> — <em>Close All Relays</em> immediately
    closes every relay, including the master.</li>
  </ul>

  <h2>How to Prime</h2>
  <ol>
    <li>Ensure the water reservoir is connected and filled.</li>
    <li>Click <strong>Open Master</strong> to open the master solenoid.</li>
    <li>Select each cage in turn from the dropdown.</li>
    <li>Click <strong>Open Selected</strong> and wait until water flows steadily from
    the delivery nozzle (no air bubbles).</li>
    <li>Click <strong>Close Selected</strong> before moving to the next cage.</li>
    <li>When all lines are primed, click <strong>Close Master</strong>.</li>
  </ol>

  <h2>Safety Interlocks</h2>
  <ul>
    <li>Individual cage relays cannot be opened unless the master solenoid is open.</li>
    <li>Closing the master solenoid automatically closes any open cage relays first.</li>
    <li><em>Close All Relays</em> bypasses normal sequencing for rapid emergency
    shutdown.</li>
  </ul>
  <p>All priming actions are logged to the <strong>System Messages</strong> terminal with
  timestamps.</p>

  <div class='help-warning'>
    <strong>Warning:</strong> Do not leave cage relays open unattended.  Always close
    all relays before leaving the system.  Use <em>Close All Relays</em> if in doubt.
  </div>
</div>
""",
            keywords=[
                "priming",
                "prime",
                "flush",
                "air bubbles",
                "master solenoid",
                "cage relay",
                "open relay",
                "close relay",
                "emergency stop",
                "close all relays",
                "interlock",
                "lines",
            ],
            related_topics=[
                "Hardware Setup & Maintenance",
                "Valve Calibration",
                "Safety Features",
                "Hardware Modes",
            ],
        ),
        "Flow Sensor": HelpContent(
            title="Flow Sensor",
            summary="The Teensy flow-sensor bridge provides real-time volumetric feedback in solenoid mode.",
            content="""
<div class='help-section'>
  <h1>Flow Sensor</h1>
  <p>In solenoid mode, RRR uses a <strong>Teensy microcontroller</strong> as a USB serial
  bridge to a liquid flow sensor.  The sensor measures the volume of water passing through
  the main supply line in real time, allowing the software to close each valve at exactly
  the right moment.</p>

  <h2>What It Measures</h2>
  <ul>
    <li>Instantaneous flow rate (mL/min) sampled at a configurable rate (default 50 Hz).</li>
    <li>Cumulative volume per delivery event, used to meet per-animal targets.</li>
  </ul>

  <h2>Configuration (Settings → Delivery → Flow Sensor (Teensy Bridge))</h2>
  <ul>
    <li><strong>Teensy Port</strong> — the serial port for the Teensy device (default
    <code>/dev/teensy_flow</code>).  Enter manually or click <strong>Auto-Detect</strong>
    to scan available ports.  You can also try common alternatives such as
    <code>/dev/ttyACM0</code>.</li>
    <li><strong>Test</strong> — sends a ping command to the Teensy; a pong response
    confirms the connection is working.</li>
    <li><strong>Allow schedules without flow sensor</strong> — when checked, the app falls
    back to calibration-based volume estimation if the sensor is unavailable.  When
    unchecked, schedules will fail if the sensor is not connected.</li>
    <li><strong>Sampling Rate</strong> — measurement frequency in Hz (1–100 Hz, default
    50 Hz).</li>
  </ul>

  <h2>Why It Matters</h2>
  <p>Without flow-sensor feedback, volume accuracy depends entirely on per-valve
  calibration constants, which can drift.  With the sensor connected, deliveries are
  closed-loop: the valve closes as soon as the measured volume reaches the target,
  regardless of upstream pressure variation.</p>

  <div class='help-note'>
    <strong>Note:</strong> The flow sensor is only relevant in <strong>solenoid mode</strong>.
    In pump mode, volume is estimated from pulse count and the configured pump output
    volume — no flow sensor is used.
  </div>
</div>
""",
            keywords=[
                "flow sensor",
                "teensy",
                "serial port",
                "uart",
                "solenoid mode",
                "volumetric",
                "real time",
                "feedback",
                "auto detect",
                "ttyacm0",
                "/dev/teensy_flow",
                "sampling rate",
                "ml/min",
            ],
            related_topics=[
                "Hardware Modes",
                "Valve Calibration",
                "Hardware Setup & Maintenance",
                "Troubleshooting",
            ],
        ),
        # ----------------------------------------------------------------
        # SUPPORT
        # ----------------------------------------------------------------
        "Troubleshooting": HelpContent(
            title="Troubleshooting",
            summary="Diagnose and fix common hardware, schedule, flow-sensor, and notification problems.",
            content="""
<div class='help-section'>
  <h1>Troubleshooting</h1>
  <p>Use the steps below to diagnose and resolve common problems.  Always check the
  <strong>System Messages</strong> terminal first — it records all errors with
  timestamps.</p>

  <h2>App Starts in Guest Mode / Settings Tab Disabled</h2>
  <p>This is normal.  Log in on the <strong>Profile</strong> tab.  Settings and Help
  become accessible after a successful login.</p>

  <h2>Wrong Hardware Mode</h2>
  <p>If deliveries are erratic or the hardware does not respond, verify that the mode in
  <strong>Settings → Delivery</strong> matches your physical hardware.  Change the mode
  only when no schedule is running.  Reconnect and restart the app if needed.</p>

  <h2>Valve / Pump Delivers Wrong Volume</h2>
  <ul>
    <li>Open <strong>Settings → Calibration</strong> and check the CV% for the affected
    cage.  High CV% (&gt;5%) indicates poor repeatability — recalibrate.</li>
    <li>In pump mode, verify the <strong>Pump Output Volume</strong> and
    <strong>Calibration Factor</strong> in Settings → Delivery.</li>
    <li>Prime the lines (<strong>Settings → Priming</strong>) to flush any trapped
    air.</li>
  </ul>

  <h2>Flow Sensor / Teensy Not Detected</h2>
  <ul>
    <li>Confirm the Teensy is connected via USB.</li>
    <li>In <strong>Settings → Delivery → Flow Sensor (Teensy Bridge)</strong>, click
    <strong>Auto-Detect</strong>.  If it fails, try entering the port manually
    (e.g., <code>/dev/ttyACM0</code>).</li>
    <li>Click <strong>Test</strong> to send a ping.  If there is no pong response,
    check that the Teensy firmware is uploaded and that your user account is in the
    <code>dialout</code> group (Linux).</li>
    <li>Enable <em>Allow schedules without flow sensor</em> to run on calibration values
    while the sensor is unavailable.</li>
  </ul>

  <h2>Schedule Errors or Won't Start</h2>
  <ul>
    <li>Confirm all required animals have been added and have valid weights.</li>
    <li>Check that cage assignments are valid (no animal on R16 — master solenoid).</li>
    <li>Ensure the schedule start time is in the future.</li>
    <li>Verify volumes are positive and within safe limits.</li>
  </ul>

  <h2>Slack Notifications Not Arriving</h2>
  <ul>
    <li>Go to <strong>Settings → General → Slack Integration</strong> and verify the
    Bot Token and Channel ID.</li>
    <li>Confirm internet connectivity on the host machine.</li>
  </ul>

  <h2>Emergency — Schedule Running and Won't Respond</h2>
  <ol>
    <li>Press <strong>Stop</strong> in the Run/Stop section.</li>
    <li>If Stop does not respond within a few seconds, disconnect power from the relay
    HAT.</li>
    <li>Restart the application.  Review the System Messages terminal for the error that
    caused the hang.</li>
  </ol>

  <div class='help-tip'>
    <strong>Tip:</strong> Enable a Slack integration so you receive alerts even when you
    are away from the workstation.
  </div>
</div>
""",
            keywords=[
                "troubleshooting",
                "errors",
                "issues",
                "flow sensor",
                "teensy",
                "serial port",
                "hardware mode",
                "calibration",
                "schedule error",
                "slack",
                "notifications",
                "stop",
                "emergency",
                "guest mode",
                "volume wrong",
                "delivery",
                "dialout",
            ],
            related_topics=[
                "Safety Features",
                "Hardware Modes",
                "Valve Calibration",
                "Flow Sensor",
                "Priming",
            ],
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
                assert (
                    key in self._content
                ), f"IA topic '{key}' under '{cat}' has no HelpContent entry."

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
            topic_links = "".join(f"<li><a href='topic:{quote(k)}'>{k}</a></li>" for k in topics)
            rows.append(
                f"<div class='lp-cat'>" f"<h2>{cat}</h2>" f"<ul>{topic_links}</ul>" f"</div>"
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
        kw_hits: List[Tuple[str, str]] = []
        body_hits: List[Tuple[str, str]] = []

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
                end = min(len(plain), idx + 80)
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
        links = "".join(f"<a href='topic:{quote(k)}'>{k}</a>" for k in related)
        return f"<div class='related-topics'><strong>Related topics:</strong> {links}</div>"

    def _format_content(self, html_body: str, theme: str, extra_css: str = "") -> str:
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
