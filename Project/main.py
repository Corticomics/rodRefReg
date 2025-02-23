# main.py

import sys
import os
from utils.volume_calculator import VolumeCalculator
from PyQt5.QtWidgets import QApplication, QInputDialog, QListWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt, QThread, QObject, pyqtSignal, QTimer
from gpio.relay_worker import RelayWorker
from ui.gui import RodentRefreshmentGUI
from gpio.gpio_handler import RelayHandler
from notifications.notifications import NotificationHandler
from settings.config import load_settings, save_settings
from controllers.projects_controller import ProjectsController
from models.database_handler import DatabaseHandler
from models.login_system import LoginSystem  # Import LoginSystem
from models.relay_unit import RelayUnit

import time
import sys
import traceback
from models.relay_unit_manager import RelayUnitManager

def exception_hook(exctype, value, tb):
    print("".join(traceback.format_exception(exctype, value, tb)))
    sys.exit(1)

sys.excepthook = exception_hook

class StreamRedirector(QObject):
    message_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def write(self, message):
        if message.strip():  # Ignore empty messages
            self.message_signal.emit(message)

    def flush(self):
        pass

# Initialize thread and worker globally to reuse them
thread = QThread()
worker = None

def setup():
    global relay_handler, settings, gui, notification_handler, controller, database_handler, login_system

    # Initialize the Projects Controller and Database Handler
    controller = ProjectsController()
    database_handler = DatabaseHandler()

    # Initialize the login system with database handler and assume "Guest" mode if not logged in
    login_system = LoginSystem(database_handler)
    if not login_system.is_logged_in():
        login_system.set_guest_mode()

    # Load settings (if any) and initialize relays
    settings = load_settings()
    
    # Initialize relay unit manager
    relay_unit_manager = RelayUnitManager(settings)
    
    # Initialize relay handler with relay unit manager
    relay_handler = RelayHandler(relay_unit_manager, settings.get('num_hats', 1))
    relay_handler.set_all_relays(0)  # Ensure all relays are closed during setup

    # Initialize Slack notification handler
    notification_handler = NotificationHandler(
        settings.get('slack_token', 'SLACKTOKEN'), 
        settings.get('channel_id', 'ChannelId')
    )

    # Initialize GUI components
    gui = RodentRefreshmentGUI(
        run_program, 
        stop_program, 
        change_relay_hats, 
        settings, 
        database_handler=database_handler, 
        login_system=login_system,
        relay_handler=relay_handler,
        notification_handler=notification_handler
    )

def run_program(schedule, mode, window_start, window_end):
    global thread, worker, notification_handler, controller

    try:
        print(f"Running program with schedule: {schedule.name}, mode: {mode}")

        # Reinitialize the thread and worker
        if thread is not None:
            thread.quit()
            thread.wait()
        thread = QThread()

        # Create base worker settings
        worker_settings = {
            'mode': mode,
            'window_start': window_start,
            'window_end': window_end,
            'min_trigger_interval_ms': 500,
            'database_handler': database_handler,  # Add database handler
            'pump_controller': controller.pump_controller if hasattr(controller, 'pump_controller') else None,
            'schedule_id': schedule.schedule_id
        }
        
        if mode.lower() == "instant":
            # Create delivery instants with correct relay unit assignments
            worker_settings['delivery_instants'] = []
            for delivery in schedule.instant_deliveries:
                worker_settings['delivery_instants'].append({
                    'relay_unit_id': delivery['relay_unit_id'],
                    'animal_id': delivery['animal_id'],
                    'delivery_time': delivery['datetime'].isoformat() if hasattr(delivery['datetime'], 'isoformat') else delivery['datetime'],
                    'water_volume': delivery['volume']
                })
        else:  # Staggered mode
            worker_settings.update({
                'cycle_interval': 3600,
                'stagger_interval': 0.5,
                'water_volume': schedule.water_volume,
                'relay_unit_assignments': schedule.relay_unit_assignments,
                'desired_water_outputs': schedule.desired_water_outputs  # Add this line
            })
        
        print("\nWorker Settings Debug:")
        print(f"Mode: {worker_settings.get('mode')}")
        print(f"Desired outputs: {worker_settings.get('desired_water_outputs')}")
        print(f"Relay assignments: {worker_settings.get('relay_unit_assignments')}\n")
        
        # Initialize worker with correct settings
        worker = RelayWorker(worker_settings, relay_handler, notification_handler)
        worker.moveToThread(thread)

        # Connect signals and slots
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        worker.progress.connect(lambda message: print(message))

        thread.started.connect(worker.run_cycle)
        thread.start()

        print("Program Started")
    except Exception as e:
        print(f"Failed to run program: {e}")
        if notification_handler:
            notification_handler.send_slack_notification(f"Program error: {e}")

def cleanup():
    global thread, worker
    
    print("[DEBUG] Starting cleanup process")
    
    if worker and worker._is_running:
        print("[DEBUG] Worker still running, waiting for completion")
        return
        
    try:
        if relay_handler:
            relay_handler.set_all_relays(0)
            print("[DEBUG] All relays deactivated")
            
        if worker:
            worker._is_running = False
            for timer in worker.timers:
                timer.stop()
            worker.main_timer.stop()
            print("[DEBUG] All timers stopped")
            
        # Check if the worker still exists before trying to disconnect signals
        if worker is not None:
            try:
                worker.finished.disconnect()
                worker.progress.disconnect()
            except TypeError as e:
                print(f"[DEBUG] Error disconnecting signals (may already be disconnected): {e}")
            except RuntimeError as e:
                print(f"[DEBUG] Worker was already deleted or disconnected: {e}")

            worker = None  # Clear the worker reference

        # Stop and clear the thread
        if thread is not None and thread.isRunning():
            try:
                thread.quit()  # Gracefully exit the thread loop
                thread.wait()  # Block until the thread has fully finished execution
            except Exception as e:
                print(f"[ERROR] Error stopping thread: {e}")

        thread = None  # Explicitly set thread to None for reinitialization
        gui.run_stop_section.reset_ui()  # Reset the run_stop_section

        print("[DEBUG] Cleanup completed. Program ready for the next job.")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred during cleanup: {e}")

def stop_program():
    """Central stop control function"""
    global thread, worker, relay_handler
    
    try:
        print("[DEBUG] Starting stop sequence")
        
        # First stop the worker if it exists
        if worker:
            # Stop all timers first
            worker._is_running = False
            for timer in getattr(worker, 'timers', []):
                if timer and timer.isActive():
                    timer.stop()
            
            if hasattr(worker, 'main_timer') and worker.main_timer:
                worker.main_timer.stop()
            
            if hasattr(worker, 'monitor_timer') and worker.monitor_timer:
                worker.monitor_timer.stop()
            
            # Call worker's stop method
            worker.stop()
            
            print("[DEBUG] Worker stopped")
        
        # Wait for thread with timeout
        if thread and thread.isRunning():
            if not thread.wait(2000):  # 2 second timeout
                print("[DEBUG] Thread timeout - forcing termination")
                thread.terminate()
            thread.wait()
            print("[DEBUG] Thread stopped")
        
        # Ensure relays are deactivated
        if relay_handler:
            relay_handler.set_all_relays(0)
            print("[DEBUG] All relays deactivated")
        
        # Clear worker and thread references
        worker = None
        thread = None
        
        print("[DEBUG] Stop sequence completed successfully")
        return True
        
    except Exception as e:
        print(f"[ERROR] Stop sequence failed: {e}")
        return False

def change_relay_hats():
    global relay_handler, settings

    # Prompt user for the number of relay hats
    num_hats, ok = QInputDialog.getInt(None, "Number of Relay Hats", 
                                     "Enter the number of relay hats:", min=1, max=8)
    if not ok:
        return

    # Update settings
    settings['num_hats'] = num_hats
    settings['relay_pairs'] = create_relay_pairs(num_hats)
    
    # Create new relay unit manager with updated settings
    relay_unit_manager = RelayUnitManager(settings)
    
    # Update relay handler
    relay_handler.update_relay_units(relay_unit_manager.get_all_relay_units(), num_hats)

    # Update GUI components
    relay_units = relay_unit_manager.get_all_relay_units()
    _update_gui_relay_units(relay_units)

    # Save settings
    save_settings(settings)
    
    # Reset UI
    cleanup()
    
    # Confirm update
    gui.print_to_terminal(f"Relay hats updated to {num_hats} hats.")

def create_relay_pairs(num_hats):
    relay_units = []
    for hat in range(num_hats):
        start_relay = hat * 16 + 1
        for i in range(0, 16, 2):
            relay_pair = (start_relay + i, start_relay + i + 1)
            relay_units.append(relay_pair)
    return relay_units

def _update_gui_relay_units(relay_units):
    """Update GUI components with new relay units"""
    gui.projects_section.relay_units = relay_units
    gui.projects_section.schedules_tab.relay_units = relay_units
    gui.projects_section.schedules_tab.relay_containers = {}
    
    # Remove old layout
    gui.projects_section.schedules_tab.layout.removeItem(
        gui.projects_section.schedules_tab.relay_layout
    )
    gui.projects_section.schedules_tab.relay_layout = QHBoxLayout()

    # Create new containers
    for relay_unit in relay_units:
        container = QListWidget()
        container.setAcceptDrops(True)
        container.setDragDropMode(QListWidget.InternalMove)
        container.setDefaultDropAction(Qt.MoveAction)
        container.objectName = f"Relay Unit {relay_unit.unit_id}"
        gui.projects_section.schedules_tab.relay_containers[relay_unit.unit_id] = container

        relay_layout = QVBoxLayout()
        relay_layout.addWidget(QLabel(str(relay_unit)))
        relay_layout.addWidget(container)
        gui.projects_section.schedules_tab.relay_layout.addLayout(relay_layout)

    gui.projects_section.schedules_tab.layout.addLayout(
        gui.projects_section.schedules_tab.relay_layout
    )

def main():
    app = QApplication(sys.argv)

    # Call the setup function to initialize everything before starting
    setup()

    # Initialize StreamRedirector and connect its signal to the GUI
    redirector = StreamRedirector()
    redirector.message_signal.connect(gui.system_message_signal)

    # Redirect stdout and stderr to the StreamRedirector
    sys.stdout = redirector
    sys.stderr = redirector

    gui.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()