# help_content_manager.py
from dataclasses import dataclass
from typing import Dict, List
import os
import json

@dataclass
class HelpContent:
    title: str
    content: str
    keywords: List[str]
    related_topics: List[str]
    video_tutorials: Dict[str, str]

class HelpContentManager:
    def __init__(self):
        self.content = self._load_default_content()

    def _load_default_content(self) -> Dict[str, HelpContent]:
        existing_content = {
            "Getting Started": HelpContent(
                title="Getting Started with the Rodent Refreshment Regulator (RRR)",
                content="""
<div class='help-section'>
  <h1>Welcome to RRR</h1>
  <p>The Rodent Refreshment Regulator (RRR) is designed to help you automatically deliver water to your research animals with high precision and safety. This guide will walk you through the basic steps to get started with the system.</p>
  <h2>Step-by-Step Quick Start</h2>
  <ol>
    <li><strong>Log In or Use Guest Mode:</strong> Sign in using your credentials to access full features. If you do not have an account, you can use guest mode (note that saving schedules requires an account).</li>
    <li><strong>Register Your Animals:</strong> Go to the <em>Animals</em> tab and add your research subjects by providing their unique IDs, names, and weights. This information is essential to calculate the proper water volumes.</li>
    <li><strong>Create a Water Delivery Schedule:</strong> In the <em>Schedules</em> tab, you can choose between <strong>Instant</strong> and <strong>Staggered</strong> delivery modes. Set your desired delivery times and volumes.</li>
    <li><strong>Check Your Hardware:</strong> Before you start an experiment, ensure that your pumps, relay units, and relay hats are connected correctly. Use the settings and test functions to verify that everything is working as expected.</li>
    <li><strong>Start Your Experiment:</strong> Press the <strong>Run</strong> button in the Run/Stop section and monitor the system messages for real-time updates.</li>
  </ol>
  <div class='help-note'>
    <strong>Note:</strong> Always perform a quick hardware test before starting a full experiment.
  </div>
</div>
                """,
                keywords=["getting started", "login", "setup", "introduction", "quick start"],
                related_topics=["System Overview", "First Time Setup"],
                video_tutorials={"Getting Started Video": "getting_started.mp4"}
            ),
            "Animal Management": HelpContent(
                title="Managing Research Subjects",
                content="""
<div class='help-section'>
  <h1>Managing Your Research Animals</h1>
  <p>This section explains how to add new animals, update their information, and monitor their health. Accurate records help ensure that each animal receives the correct water volume and that you can track their overall wellbeing.</p>
  <h2>Adding New Animals</h2>
  <ol>
    <li>Go to the <strong>Animals</strong> tab.</li>
    <li>Click the <strong>Add Animal</strong> button.</li>
    <li>Fill in the following fields:
      <ul>
        <li><strong>Lab Animal ID:</strong> A unique identifier (e.g., "A001").</li>
        <li><strong>Name:</strong> The animal's name or code.</li>
        <li><strong>Initial Weight:</strong> The weight when first registered (in grams).</li>
        <li><strong>Last Weight:</strong> The most recent weight, if available.</li>
        <li><strong>Time Stamps:</strong> Record when the animal was last weighed and watered.</li>
      </ul>
    </li>
    <li>Click <strong>Save</strong> to add the animal to the system.</li>
  </ol>
  <h2>Editing and Monitoring</h2>
  <p>To update an animal's data, select the animal and click <strong>Edit</strong>. Make sure to update weights daily for accurate water delivery calculations.</p>
  <div class='help-warning'>
    <strong>Important:</strong> Inaccurate weight entries can lead to improper water volumes.
  </div>
</div>
                """,
                keywords=["animal management", "add animal", "edit animal", "monitoring", "health"],
                related_topics=["Adding Animals", "Data Collection"],
                video_tutorials={"Animal Management Tutorial": "animal_management.mp4"}
            ),
            "Schedule Creation": HelpContent(
                title="Creating Water Delivery Schedules",
                content="""
<div class='help-section'>
  <h1>Setting Up Water Delivery Schedules</h1>
  <p>Schedules determine when and how much water is delivered. RRR offers two modes:</p>
  <ul>
    <li><strong>Instant Delivery:</strong> All animals receive water simultaneously.</li>
    <li><strong>Staggered Delivery:</strong> Water is dispensed gradually over a set period, reducing stress.</li>
  </ul>
  <h2>How to Create a Schedule</h2>
  <ol>
    <li>Go to the <strong>Schedules</strong> tab and click <strong>Create New Schedule</strong>.</li>
    <li>Enter a descriptive schedule name and specify the total water volume.</li>
    <li>For <strong>Instant Delivery</strong>: Choose specific delivery times for each animal.</li>
    <li>For <strong>Staggered Delivery</strong>: Set the start and end times for the water delivery window.</li>
    <li>Assign animals to relay units; the system will calculate the number of pump triggers needed based on each animal's weight and calibration settings.</li>
    <li>Review your settings and click <strong>Save</strong>.</li>
  </ol>
  <h2>Best Practices</h2>
  <ul>
    <li>Double-check all time and volume settings before activation.</li>
    <li>Start with a test schedule to verify delivery accuracy.</li>
    <li>Monitor system messages during the experiment.</li>
  </ul>
  <div class='help-tip'>
    <strong>Tip:</strong> Use the suggestion feature to automatically generate optimal parameters based on historical data.
  </div>
</div>
                """,
                keywords=["schedule creation", "water delivery", "instant schedule", "staggered schedule", "setup"],
                related_topics=["Basic Operations", "Hardware Setup"],
                video_tutorials={"Schedule Setup Tutorial": "schedule_creation.mp4"}
            ),
            "System Overview": HelpContent(
                title="System Overview and Architecture",
                content="""
<div class='help-section'>
  <h1>Understanding the RRR System</h1>
  <p>The Rodent Refreshment Regulator integrates hardware, software, and scheduling to deliver water accurately. This overview explains how the components work together:</p>
  <h2>Main Components</h2>
  <ul>
    <li><strong>Animals Tab:</strong> Register and monitor research subjects.</li>
    <li><strong>Schedules Tab:</strong> Create and manage water delivery schedules.</li>
    <li><strong>Hardware Interface:</strong> Controls pumps and relay units for precise water delivery.</li>
    <li><strong>Monitoring Dashboard:</strong> Provides real-time system status and alerts.</li>
    <li><strong>Settings Tab:</strong> Adjust calibration, pump volume, and safety limits.</li>
  </ul>
  <h2>How It Works</h2>
  <p>The system calculates the number of pump triggers needed for each animal based on its weight and your chosen water volume. It then schedules these triggers according to the selected delivery mode, ensuring safe and accurate delivery.</p>
  <div class='help-note'>
    <strong>Tip for New Users:</strong> Familiarize yourself with each component to fully utilize the system's capabilities.
  </div>
</div>
                """,
                keywords=["system overview", "architecture", "components", "workflow"],
                related_topics=["Getting Started", "Basic Operations"],
                video_tutorials={"System Overview Video": "system_overview.mp4"}
            ),
            "Adding Animals": HelpContent(
                title="Adding and Managing Research Subjects",
                content="""
<div class='help-section'>
  <h1>Adding and Managing Animals</h1>
  <p>This guide explains how to add new animals and maintain their records. Proper animal data is essential for calculating safe water delivery volumes.</p>
  <h2>Steps to Add an Animal</h2>
  <ol>
    <li>Go to the <strong>Animals</strong> tab.</li>
    <li>Click the <strong>Add Animal</strong> button.</li>
    <li>Enter the required details:
      <ul>
        <li><strong>Lab Animal ID:</strong> A unique identifier.</li>
        <li><strong>Name:</strong> The animal's name.</li>
        <li><strong>Initial Weight:</strong> The animal's weight at registration (in grams).</li>
        <li><strong>Last Weight:</strong> The most recent weight (if available).</li>
        <li><strong>Date/Time:</strong> When the animal was last weighed and watered.</li>
      </ul>
    </li>
    <li>Click <strong>Save</strong> to register the animal.</li>
  </ol>
  <h2>Editing Animal Records</h2>
  <p>To update an animal's data, select it from the table and click <strong>Edit</strong>. Regular updates ensure the system calculates water volumes accurately.</p>
  <div class='help-warning'>
    <strong>Important:</strong> Consistent and accurate measurements are critical for animal health and experimental reliability.
  </div>
</div>
                """,
                keywords=["add animal", "manage animal", "edit animal", "health monitoring"],
                related_topics=["Animal Management", "Data Collection"],
                video_tutorials={"Animal Entry Tutorial": "add_animal_tutorial.mp4"}
            ),
            "Creating Schedules": HelpContent(
                title="Water Delivery Scheduling Explained",
                content="""
<div class='help-section'>
  <h1>Water Delivery Scheduling</h1>
  <p>This guide explains how to set up and manage water delivery schedules using RRR.</p>
  <h2>Delivery Modes</h2>
  <ul>
    <li><strong>Instant Delivery:</strong> All animals receive water at the same time. Use for brief, synchronized hydration events.</li>
    <li><strong>Staggered Delivery:</strong> Water is delivered over a set period to minimize stress. This mode spaces out pump triggers for gradual delivery.</li>
  </ul>
  <h2>How to Create a Schedule</h2>
  <ol>
    <li>Navigate to the <strong>Schedules</strong> tab and click <strong>Create New Schedule</strong>.</li>
    <li>Enter a schedule name and specify the total water volume.</li>
    <li>For <strong>Instant Delivery</strong>, define the exact delivery times for each animal.</li>
    <li>For <strong>Staggered Delivery</strong>, set a start and end time to create a delivery window.</li>
    <li>Assign animals to specific relay units so that the system knows which pump to trigger.</li>
    <li>Review the calculated number of pump triggers and confirm your settings.</li>
    <li>Click <strong>Save</strong> to store the schedule.</li>
  </ol>
  <div class='help-tip'>
    <strong>Tip:</strong> Always perform a test run of your schedule to ensure the settings are correct before starting your experiment.
  </div>
</div>
                """,
                keywords=["creating schedules", "schedule setup", "water delivery", "instant", "staggered"],
                related_topics=["Schedule Creation", "Basic Operations"],
                video_tutorials={"Schedule Scheduling Guide": "creating_schedules.mp4"}
            ),
            "First Time Setup": HelpContent(
                title="First Time Setup Guide",
                content="""
<div class='help-section'>
  <h1>First Time Setup for RRR</h1>
  <p>If you are using RRR for the first time, follow this comprehensive setup guide to ensure your system is configured correctly.</p>
  <h2>Initial Steps</h2>
  <ol>
    <li><strong>Hardware Check:</strong>
      <ul>
        <li>Verify that all pump units, relay units, and relay hats are connected properly.</li>
        <li>Ensure that all cables and power supplies are secure.</li>
      </ul>
    </li>
    <li><strong>User Account Setup:</strong>
      <ul>
        <li>Create an administrator account if you haven't already.</li>
        <li>Configure user roles to control access and permissions.</li>
      </ul>
    </li>
    <li><strong>Calibration and Testing:</strong>
      <ul>
        <li>Run the pump calibration test from the Settings tab to confirm that each pump delivers the expected volume (default: 50 µL per trigger).</li>
        <li>Use the Change Relay Hats feature to test that all relay units are working correctly.</li>
      </ul>
    </li>
    <li><strong>Perform a Full System Test:</strong>
      <ul>
        <li>Create a short, trial schedule and run it.</li>
        <li>Check that water is delivered accurately and that system messages report no errors.</li>
      </ul>
    </li>
  </ol>
  <div class='help-warning'>
    <strong>Warning:</strong> Do not start a full experiment until you have confirmed that every component of the system passes its test.
  </div>
</div>
                """,
                keywords=["first time setup", "initial setup", "calibration", "hardware test"],
                related_topics=["Hardware Setup", "Basic Operations"],
                video_tutorials={"First Time Setup Video": "first_time_setup.mp4"}
            ),
            "Basic Operations": HelpContent(
                title="Basic Daily Operations",
                content="""
<div class='help-section'>
  <h1>Basic System Operations</h1>
  <p>This guide covers the everyday tasks you need to perform to run RRR smoothly.</p>
  <h2>System Startup</h2>
  <ol>
    <li>Power on your RRR system.</li>
    <li>Log in with your credentials (or use guest mode if you are testing).</li>
    <li>Check the <strong>System Messages</strong> for any initial errors.</li>
  </ol>
  <h2>Animal and Data Management</h2>
  <ol>
    <li>Update animal weights and other data in the <strong>Animals</strong> tab.</li>
    <li>Ensure that the recommended water volumes are recalculated based on updated weights.</li>
    <li>Review the animal list for any discrepancies.</li>
  </ol>
  <h2>Schedule Verification</h2>
  <ol>
    <li>Open the <strong>Schedules</strong> tab to view active and upcoming water delivery schedules.</li>
    <li>Monitor delivery logs and system messages during water delivery.</li>
  </ol>
  <div class='help-tip'>
    <strong>Pro Tip:</strong> Use the dashboard view to get a quick status update on all active schedules.
  </div>
</div>
                """,
                keywords=["basic operations", "daily tasks", "startup", "monitoring"],
                related_topics=["First Time Setup", "Schedule Creation"],
                video_tutorials={"Daily Operations Video": "daily_operations.mp4"}
            ),
            "Hardware Setup": HelpContent(
                title="Hardware Setup and Maintenance",
                content="""
<div class='help-section'>
  <h1>Hardware Setup and Maintenance</h1>
  <p>This section details the physical components of RRR and how to maintain them.</p>
  <h2>Components Overview</h2>
  <ul>
    <li><strong>Pump Units:</strong> Deliver water with high precision. The default setting is 50 µL per trigger.</li>
    <li><strong>Relay Units and Hats:</strong> Control the pumps. Each unit is assigned to specific animals.</li>
  </ul>
  <h2>Initial Hardware Configuration</h2>
  <ol>
    <li>Ensure all relay hats are properly installed and all relays are in the off state.</li>
    <li>Run the hardware test in the Settings tab to verify proper operation.</li>
  </ol>
  <h2>Maintenance Procedures</h2>
  <ul>
    <li><strong>Daily Checks:</strong> Visually inspect connections and verify that no relays are inadvertently active.</li>
    <li><strong>Weekly Maintenance:</strong> Clean relay hats, recalibrate pumps, and check for any signs of wear or damage.</li>
  </ul>
  <div class='help-warning'>
    <strong>Critical:</strong> Always perform a full hardware test after any maintenance or configuration changes.
  </div>
</div>
                """,
                keywords=["hardware setup", "maintenance", "pump calibration", "relay units"],
                related_topics=["First Time Setup", "Safety Features"],
                video_tutorials={"Hardware Setup Guide": "hardware_setup.mp4"}
            ),
            "Safety Features": HelpContent(
                title="Safety Features and Emergency Procedures",
                content="""
<div class='help-section'>
  <h1>Safety Features and Emergency Procedures</h1>
  <p>The safety of your animals and equipment is our top priority. This guide explains the built-in safety mechanisms of RRR and what you should do in an emergency.</p>
  <h2>Built-In Safety Mechanisms</h2>
  <ul>
    <li><strong>Volume Limits:</strong> The system calculates a maximum safe water volume based on each animal's weight and will not exceed it.</li>
    <li><strong>Trigger Spacing:</strong> Ensures a minimum interval between pump activations to prevent hardware overload.</li>
    <li><strong>Emergency Stop:</strong> Press the <strong>Stop</strong> button at any time to immediately halt water delivery.</li>
  </ul>
  <h2>Alerts and Notifications</h2>
  <ul>
    <li>All errors and important system events are displayed in the <strong>System Messages</strong> area.</li>
    <li>If configured, Slack notifications will alert you of critical issues.</li>
  </ul>
  <h2>Emergency Procedures</h2>
  <ol>
    <li>Press the <strong>Stop</strong> button to abort any running schedule.</li>
    <li>Confirm that all relay units are deactivated.</li>
    <li>If necessary, manually override the system by disconnecting the power supply.</li>
  </ol>
  <div class='help-warning'>
    <strong>Important:</strong> Follow all emergency procedures carefully and only override safety settings if absolutely necessary.
  </div>
</div>
                """,
                keywords=["safety", "emergency", "stop", "alerts"],
                related_topics=["Hardware Setup", "Basic Operations"],
                video_tutorials={"Safety Procedures Video": "safety_features.mp4"}
            ),
            "Troubleshooting": HelpContent(
                title="Troubleshooting Common Issues",
                content="""
<div class='help-section'>
  <h1>Troubleshooting and Common Issues</h1>
  <p>If you encounter problems while using RRR, this guide will help you diagnose and resolve them.</p>
  <h2>Hardware Connection Issues</h2>
  <ul>
    <li><strong>Cable and Connector Check:</strong> Ensure all cables are securely connected and that relay hats are properly installed.</li>
    <li><strong>Pump Calibration:</strong> If water volumes are off, re-run the calibration test in the Settings tab.</li>
  </ul>
  <h2>Schedule and Software Errors</h2>
  <ul>
    <li><strong>Invalid Schedule Settings:</strong> Check that start and end times, animal assignments, and water volumes are entered correctly.</li>
    <li><strong>System Messages:</strong> Review the terminal output for error messages that indicate what might be wrong.</li>
  </ul>
  <h2>Notification Issues</h2>
  <ul>
    <li>Ensure that your Slack credentials and channel ID are correct in the Notifications settings.</li>
    <li>Verify that your internet connection is stable.</li>
  </ul>
  <div class='help-tip'>
    <strong>Tip:</strong> Always use the <strong>Stop</strong> button to abort a schedule before restarting the system. Note any error messages and consult this guide for potential fixes.
  </div>
</div>
                """,
                keywords=["troubleshooting", "errors", "issues", "problem solving"],
                related_topics=["Safety Features", "Basic Operations"],
                video_tutorials={"Troubleshooting Tutorial": "troubleshooting.mp4"}
            )
        }
        
        return existing_content

    def get_content(self, topic: str) -> str:
        """Retrieve formatted content for a specific topic"""
        if topic in self.content:
            return self._format_content(self.content[topic])
        return self._format_content(self._get_error_content())

    def _format_content(self, content: HelpContent) -> str:
        """Format the content with consistent styling"""
        return f"""
<style>
    .help-section {{
        font-family: 'Segoe UI', Arial, sans-serif;
        color: #2c3e50;
        line-height: 1.6;
        padding: 20px;
    }}
    h1 {{
        color: #1a73e8;
        font-size: 24px;
        margin-bottom: 20px;
    }}
    h2 {{
        color: #2c3e50;
        font-size: 18px;
        margin-top: 20px;
    }}
    .help-note, .help-warning, .help-tip {{
        padding: 15px;
        border-radius: 4px;
        margin: 15px 0;
    }}
    .help-note {{
        background-color: #e8f0fe;
        border-left: 4px solid #1a73e8;
    }}
    .help-warning {{
        background-color: #fef0f0;
        border-left: 4px solid #dc3545;
    }}
    .help-tip {{
        background-color: #f0f9f0;
        border-left: 4px solid #28a745;
    }}
</style>
{content.content}
        """

    def _get_error_content(self) -> HelpContent:
        return HelpContent(
            title="Topic Not Found",
            content="""
<div class='help-section'>
  <h1>Topic Not Found</h1>
  <p>The requested help topic could not be found. Please check the topic name and try again.</p>
</div>
            """,
            keywords=[],
            related_topics=[],
            video_tutorials={}
        )