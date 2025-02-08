from dataclasses import dataclass
from typing import Dict, List
import json
import os

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
                title="Getting Started with RRR",
                content="""
                <div class='help-section'>
                    <h1>Welcome to the Rodent Refreshment Regulator (RRR)</h1>
                    
                    <h2>Quick Start Guide</h2>
                    <ol>
                        <li>Log in to your account or use guest mode</li>
                        <li>Navigate to the Animals tab to register your subjects</li>
                        <li>Create a water delivery schedule</li>
                        <li>Configure and verify your hardware setup</li>
                        <li>Start your experiment</li>
                    </ol>

                    <h2>Key Features</h2>
                    <ul>
                        <li>Automated water delivery scheduling</li>
                        <li>Real-time monitoring and notifications</li>
                        <li>Data logging and export capabilities</li>
                        <li>Multi-user support with role-based access</li>
                    </ul>

                    <div class='help-note'>
                        <strong>Note:</strong> Always verify your hardware connections before starting an experiment.
                    </div>
                </div>
                """,
                keywords=["start", "begin", "introduction", "overview"],
                related_topics=["Hardware Setup", "Creating Schedules"],
                video_tutorials={"Introduction": "intro.mp4"}
            ),
            
            "Animal Management": HelpContent(
                title="Managing Research Subjects",
                content="""
                <div class='help-section'>
                    <h1>Animal Management</h1>
                    
                    <h2>Adding New Animals</h2>
                    <ol>
                        <li>Navigate to the Animals tab</li>
                        <li>Click "Add New Animal"</li>
                        <li>Enter the required information:
                            <ul>
                                <li>Animal ID</li>
                                <li>Species</li>
                                <li>Weight</li>
                                <li>Study group</li>
                            </ul>
                        </li>
                    </ol>

                    <h2>Monitoring Health Status</h2>
                    <p>The system automatically tracks:</p>
                    <ul>
                        <li>Daily water intake</li>
                        <li>Access patterns</li>
                        <li>Weight changes</li>
                    </ul>

                    <div class='help-warning'>
                        <strong>Important:</strong> Monitor animal weight daily and ensure proper hydration levels.
                    </div>
                </div>
                """,
                keywords=["animals", "subjects", "monitoring", "health"],
                related_topics=["Health Monitoring", "Data Analysis"],
                video_tutorials={"Animal Care": "animal_care.mp4"}
            ),
            
            "Schedule Creation": HelpContent(
                title="Creating Water Delivery Schedules",
                content="""
                <div class='help-section'>
                    <h1>Water Delivery Schedules</h1>
                    
                    <h2>Creating a New Schedule</h2>
                    <ol>
                        <li>Go to the Schedules tab</li>
                        <li>Set delivery parameters:
                            <ul>
                                <li>Frequency</li>
                                <li>Volume per delivery</li>
                                <li>Time windows</li>
                            </ul>
                        </li>
                        <li>Assign animals to the schedule</li>
                        <li>Verify and activate</li>
                    </ol>

                    <h2>Best Practices</h2>
                    <ul>
                        <li>Start with conservative water volumes</li>
                        <li>Include rest periods</li>
                        <li>Monitor initial responses</li>
                    </ul>

                    <div class='help-tip'>
                        <strong>Tip:</strong> Use the suggestion feature for optimal delivery parameters.
                    </div>
                </div>
                """,
                keywords=["schedule", "delivery", "timing", "water"],
                related_topics=["Water Management", "System Settings"],
                video_tutorials={"Schedule Setup": "schedule_setup.mp4"}
            ),
            
            "System Overview": HelpContent(
                title="RRR System Overview",
                content="""
                <div class='help-section'>
                    <h1>Understanding the Rodent Refreshment Regulator</h1>
                    
                    <h2>Core Components</h2>
                    <ul>
                        <li><strong>Animals Tab:</strong> Manage research subjects and track their health metrics</li>
                        <li><strong>Schedules Tab:</strong> Create and manage water delivery schedules</li>
                        <li><strong>Water Delivery System:</strong> Automated precision water dispensing</li>
                        <li><strong>Monitoring Dashboard:</strong> Real-time status and alerts</li>
                    </ul>

                    <div class='help-diagram'>
                        <img src='resources/system_diagram.png' alt='System Overview Diagram'>
                    </div>

                    <h2>Key Features for Researchers</h2>
                    <ul>
                        <li>Precise water volume control (0.01mL accuracy)</li>
                        <li>Automated health monitoring</li>
                        <li>Customizable delivery schedules</li>
                        <li>Data export for analysis</li>
                    </ul>

                    <div class='help-note'>
                        <strong>Note for New Users:</strong> Start with the "First Time Setup" guide for step-by-step configuration instructions.
                    </div>
                </div>
                """,
                keywords=["overview", "introduction", "system", "components"],
                related_topics=["First Time Setup", "Basic Operations"],
                video_tutorials={"System Overview": "system_overview.mp4"}
            ),

            "Adding Animals": HelpContent(
                title="Managing Research Subjects",
                content="""
                <div class='help-section'>
                    <h1>Adding and Managing Research Subjects</h1>
                    
                    <h2>Step-by-Step Guide</h2>
                    <ol>
                        <li>Navigate to the Animals Tab</li>
                        <li>Click "Add Animal" button</li>
                        <li>Enter required information:
                            <ul>
                                <li>Lab Animal ID (unique identifier)</li>
                                <li>Initial weight (in grams)</li>
                                <li>Species/strain information</li>
                                <li>Study group assignment</li>
                            </ul>
                        </li>
                    </ol>

                    <div class='help-warning'>
                        <strong>Important:</strong> Always verify weight measurements before entry. This data is crucial for health monitoring.
                    </div>

                    <h2>Best Practices</h2>
                    <ul>
                        <li>Use consistent ID naming conventions</li>
                        <li>Update weights at the same time daily</li>
                        <li>Monitor water consumption patterns</li>
                        <li>Document any health observations</li>
                    </ul>

                    <div class='help-tip'>
                        <strong>Pro Tip:</strong> Use the filter function to quickly locate specific animals in large studies.
                    </div>
                </div>
                """,
                keywords=["animals", "subjects", "add", "manage", "weight"],
                related_topics=["Health Monitoring", "Data Collection"],
                video_tutorials={"Adding Animals": "add_animal_tutorial.mp4"}
            ),

            "Creating Schedules": HelpContent(
                title="Water Delivery Scheduling",
                content="""
                <div class='help-section'>
                    <h1>Creating Water Delivery Schedules</h1>
                    
                    <h2>Schedule Types</h2>
                    <ul>
                        <li><strong>Staggered Delivery:</strong> Distributed water delivery over time</li>
                        <li><strong>Instant Delivery:</strong> Simultaneous delivery to all subjects</li>
                    </ul>

                    <h2>Setting Up a Schedule</h2>
                    <ol>
                        <li>Select delivery mode (Staggered/Instant)</li>
                        <li>Set delivery windows:
                            <ul>
                                <li>Start time</li>
                                <li>End time</li>
                                <li>Frequency</li>
                            </ul>
                        </li>
                        <li>Assign animals to relay units</li>
                        <li>Configure volume parameters</li>
                        <li>Activate schedule</li>
                    </ol>

                    <div class='help-warning'>
                        <strong>Critical:</strong> Always ensure backup water sources are available during initial schedule testing.
                    </div>

                    <h2>Volume Calculations</h2>
                    <p>The system automatically suggests volumes based on:
                        <ul>
                            <li>Animal weight</li>
                            <li>Species requirements</li>
                            <li>Environmental conditions</li>
                        </ul>
                    </p>
                </div>
                """,
                keywords=["schedule", "water", "delivery", "timing"],
                related_topics=["Volume Control", "Safety Features"],
                video_tutorials={"Schedule Creation": "create_schedule.mp4"}
            )
        }
        
        # Add new content
        additional_content = {
            "First Time Setup": HelpContent(
                title="First Time Setup Guide",
                content="""
                <div class='help-section'>
                    <h1>Setting Up RRR for First Use</h1>
                    
                    <h2>Initial Configuration</h2>
                    <ol>
                        <li>System Requirements Check:
                            <ul>
                                <li>Verify hardware connections</li>
                                <li>Check pump calibration</li>
                                <li>Test relay units</li>
                            </ul>
                        </li>
                        <li>User Account Setup:
                            <ul>
                                <li>Create administrator account</li>
                                <li>Configure user roles</li>
                                <li>Set access permissions</li>
                            </ul>
                        </li>
                    </ol>

                    <div class='help-warning'>
                        <strong>Important:</strong> Complete all hardware tests before adding animals to the system.
                    </div>

                    <h2>Hardware Configuration</h2>
                    <ul>
                        <li>Pump Setup:
                            <ul>
                                <li>Calibrate flow rates</li>
                                <li>Set trigger volumes</li>
                                <li>Test emergency stops</li>
                            </ul>
                        </li>
                        <li>Relay Unit Configuration:
                            <ul>
                                <li>Assign unit IDs</li>
                                <li>Test connections</li>
                                <li>Verify feedback signals</li>
                            </ul>
                        </li>
                    </ul>
                </div>
                """,
                keywords=["setup", "configuration", "initial", "first time"],
                related_topics=["Hardware Setup", "User Management"],
                video_tutorials={"Initial Setup": "first_time_setup.mp4"}
            ),

            "Basic Operations": HelpContent(
                title="Basic System Operations",
                content="""
                <div class='help-section'>
                    <h1>Basic Operations Guide</h1>
                    
                    <h2>Daily Tasks</h2>
                    <ol>
                        <li>System Startup:
                            <ul>
                                <li>Power on sequence</li>
                                <li>Login procedures</li>
                                <li>Initial checks</li>
                            </ul>
                        </li>
                        <li>Animal Management:
                            <ul>
                                <li>Weight recordings</li>
                                <li>Health checks</li>
                                <li>Water consumption monitoring</li>
                            </ul>
                        </li>
                        <li>Schedule Verification:
                            <ul>
                                <li>Review active schedules</li>
                                <li>Check delivery logs</li>
                                <li>Verify system status</li>
                            </ul>
                        </li>
                    </ol>

                    <div class='help-tip'>
                        <strong>Pro Tip:</strong> Use the dashboard for quick status overview of all active schedules.
                    </div>
                </div>
                """,
                keywords=["basic", "operations", "daily", "tasks"],
                related_topics=["Animal Management", "Schedule Creation"],
                video_tutorials={"Daily Operations": "basic_ops.mp4"}
            ),

            "Hardware Setup": HelpContent(
                title="Hardware Configuration",
                content="""
                <div class='help-section'>
                    <h1>Hardware Setup and Configuration</h1>
                    
                    <h2>System Components</h2>
                    <ul>
                        <li>Pump Units:
                            <ul>
                                <li>0.01mL precision delivery</li>
                                <li>Emergency stop capability</li>
                                <li>Flow rate monitoring</li>
                            </ul>
                        </li>
                        <li>Relay Units:
                            <ul>
                                <li>Individual animal assignment</li>
                                <li>Status indicators</li>
                                <li>Manual override controls</li>
                            </ul>
                        </li>
                    </ul>

                    <div class='help-warning'>
                        <strong>Critical:</strong> Always perform a full system test after any hardware changes.
                    </div>

                    <h2>Maintenance Schedule</h2>
                    <ul>
                        <li>Daily Checks:
                            <ul>
                                <li>Visual inspection</li>
                                <li>Flow rate verification</li>
                                <li>Leak detection</li>
                            </ul>
                        </li>
                        <li>Weekly Maintenance:
                            <ul>
                                <li>Clean filters</li>
                                <li>Calibrate pumps</li>
                                <li>Test safety systems</li>
                            </ul>
                        </li>
                    </ul>
                </div>
                """,
                keywords=["hardware", "setup", "configuration", "maintenance"],
                related_topics=["Safety Features", "System Settings"],
                video_tutorials={"Hardware Setup": "hardware_setup.mp4"}
            ),

            "Safety Features": HelpContent(
                title="System Safety Features",
                content="""
                <div class='help-section'>
                    <h1>Safety Systems and Protocols</h1>
                    
                    <h2>Automated Safety Controls</h2>
                    <ul>
                        <li>Volume Limits:
                            <ul>
                                <li>Maximum delivery volumes</li>
                                <li>Rate limiting</li>
                                <li>Daily intake monitoring</li>
                            </ul>
                        </li>
                        <li>Emergency Systems:
                            <ul>
                                <li>Auto-shutdown triggers</li>
                                <li>Leak detection</li>
                                <li>Power failure handling</li>
                            </ul>
                        </li>
                    </ul>

                    <div class='help-warning'>
                        <strong>Critical:</strong> Never disable safety systems without proper authorization.
                    </div>

                    <h2>Monitoring and Alerts</h2>
                    <ul>
                        <li>Real-time Monitoring:
                            <ul>
                                <li>Flow rate tracking</li>
                                <li>Pressure monitoring</li>
                                <li>System status updates</li>
                            </ul>
                        </li>
                        <li>Alert System:
                            <ul>
                                <li>SMS notifications</li>
                                <li>Email alerts</li>
                                <li>System warnings</li>
                            </ul>
                        </li>
                    </ul>
                </div>
                """,
                keywords=["safety", "emergency", "monitoring", "alerts"],
                related_topics=["Hardware Setup", "System Settings"],
                video_tutorials={"Safety Systems": "safety_features.mp4"}
            )
        }
        
        # Merge existing and new content
        existing_content.update(additional_content)
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
            content="<div class='help-section'><h1>Topic Not Found</h1><p>The requested help topic could not be found.</p></div>",
            keywords=[],
            related_topics=[],
            video_tutorials={}
        ) 