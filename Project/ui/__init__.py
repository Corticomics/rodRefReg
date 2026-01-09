# ui/__init__.py

from .gui import RodentRefreshmentGUI
from .welcome_section import WelcomeSection
from .run_stop_section import RunStopSection

from .projects_section import ProjectsSection
from .schedules_hub import SchedulesHub  # New: Clean schedule management hub
from .schedules_tab import SchedulesTab  # Legacy: Kept for backwards compatibility
from .animals_tab import AnimalsTab
from .UserTab import UserTab
from .create_schedule_dialog import CreateScheduleDialog
from .relay_unit_widget import RelayUnitWidget
from .animal_entry_widget import AnimalEntryWidget
from .wizard_tab import WizardTab  # New: Step-by-step schedule wizard

from .SettingsTab import SettingsTab
from .HelpTab import HelpTab
from .SuggestSettingsTab import SuggestSettingsTab
from .SlackCredentialsTab import SlackCredentialsTab
from .update_notifier import UpdateNotifier

__all__ = [
    'RodentRefreshmentGUI',
    'SettingsTab',
    'UserTab',
    'HelpTab',
    'SuggestSettingsTab',
    'SlackCredentialsTab',
    'AnimalsTab',
    'SchedulesHub',
    'SchedulesTab',  # Legacy
    'WizardTab',
    'UpdateNotifier'
]