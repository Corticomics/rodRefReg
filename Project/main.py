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
from models.login_system import LoginSystem
from models.relay_unit import RelayUnit
from controllers.system_controller import SystemController
from controllers.pump_controller import PumpController
import time
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
        if message.strip():
            self.message_signal.emit(message)

    def flush(self):
        pass

# Global thread and worker
thread = QThread()
worker = None

def setup():
    global relay_handler, app_settings, gui, notification_handler, controller, database_handler, login_system, system_controller

    database_handler = DatabaseHandler()
    system_controller = SystemController(database_handler)
    
    # Use a distinct global name for the settings dictionary
    app_settings = system_controller.settings
    
    relay_unit_manager = RelayUnitManager(app_settings)
    relay_handler = RelayHandler(relay_unit_manager, app_settings['num_hats'])
    
    controller = ProjectsController()
    pump_controller = PumpController(relay_handler, database_handler)
    controller.pump_controller = pump_controller
    
    notification_handler = NotificationHandler(
        app_settings.get('slack_token'),
        app_settings.get('channel_id')
    )
    
    login_system = LoginSystem(database_handler)
    if not login_system.is_logged_in():
        login_system.set_guest_mode()
    
    gui = RodentRefreshmentGUI(
        run_program,
        stop_program,
        change_relay_hats,
        system_controller=system_controller,
        database_handler=database_handler,
        login_system=login_system,
        relay_handler=relay_handler,
        notification_handler=notification_handler
    )

def run_program(schedule, mode, window_start, window_end):
    global thread, worker, notification_handler, controller, system_controller

    try:
        print("\nDEBUG - run_program:")
        print(f"system_controller type: {type(system_controller)}")
        print(f"Running program with schedule: {schedule.name}, mode: {mode}")

        # Create base worker settings using system_controller's settings
        worker_settings = {}  # Initialize empty dict first
        if hasattr(system_controller, 'settings'):
            worker_settings = system_controller.settings.copy()
        
        # Update with schedule-specific settings
        worker_settings.update({
            'mode': mode,
            'window_start': window_start,
            'window_end': window_end,
            'min_trigger_interval_ms': worker_settings.get('min_trigger_interval_ms', 500),
            'database_handler': database_handler,
            'pump_controller': controller.pump_controller,
            'schedule_id': schedule.schedule_id
        })
        
        if mode.lower() == "instant":
            worker_settings['delivery_instants'] = []
            for delivery in schedule.instant_deliveries:
                worker_settings['delivery_instants'].append({
                    'relay_unit_id': delivery['relay_unit_id'],
                    'animal_id': delivery['animal_id'],
                    'delivery_time': delivery['datetime'].isoformat() if hasattr(delivery['datetime'], 'isoformat') else delivery['datetime'],
                    'water_volume': delivery['volume']
                })
        else:
            worker_settings.update({
                'cycle_interval': worker_settings.get('cycle_interval', 3600),
                'stagger_interval': worker_settings.get('stagger_interval', 0.5),
                'water_volume': schedule.water_volume,
                'relay_unit_assignments': schedule.relay_unit_assignments,
                'desired_water_outputs': schedule.desired_water_outputs
            })
        
        print("\nWorker Settings Debug:")
        print(f"Mode: {worker_settings.get('mode')}")
        print(f"Desired outputs: {worker_settings.get('desired_water_outputs')}")
        print(f"Relay assignments: {worker_settings.get('relay_unit_assignments')}\n")
        
        # Reinitialize the thread and worker
        if thread is not None:
            thread.quit()
            thread.wait()
        thread = QThread()

        # Create worker with explicit system_controller instance
        if not isinstance(system_controller, QObject):
            print("WARNING: system_controller is not a QObject instance!")
            print(f"system_controller type: {type(system_controller)}")
            raise TypeError("system_controller must be a SystemController instance")

        worker = RelayWorker(
            worker_settings, 
            relay_handler, 
            notification_handler,
            system_controller  # Pass the actual SystemController instance
        )
        worker.moveToThread(thread)

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
            
        if worker is not None:
            try:
                worker.finished.disconnect()
                worker.progress.disconnect()
            except TypeError as e:
                print(f"[DEBUG] Error disconnecting signals: {e}")
            except RuntimeError as e:
                print(f"[DEBUG] Worker already deleted: {e}")
            worker = None

        if thread is not None and thread.isRunning():
            try:
                thread.quit()
                thread.wait()
            except Exception as e:
                print(f"[ERROR] Error stopping thread: {e}")

        thread = None
        gui.run_stop_section.reset_ui()
        print("[DEBUG] Cleanup completed. Program ready for the next job.")
    except Exception as e:
        print(f"[ERROR] Unexpected error during cleanup: {e}")

def stop_program():
    global thread, worker, relay_handler
    try:
        print("[DEBUG] Starting stop sequence")
        if worker:
            worker._is_running = False
            for timer in getattr(worker, 'timers', []):
                if timer and timer.isActive():
                    timer.stop()
            if hasattr(worker, 'main_timer') and worker.main_timer:
                worker.main_timer.stop()
            if hasattr(worker, 'monitor_timer') and worker.monitor_timer:
                worker.monitor_timer.stop()
            worker.stop()
            print("[DEBUG] Worker stopped")
        if thread and thread.isRunning():
            if not thread.wait(2000):
                print("[DEBUG] Thread timeout - forcing termination")
                thread.terminate()
            thread.wait()
            print("[DEBUG] Thread stopped")
        if relay_handler:
            relay_handler.set_all_relays(0)
            print("[DEBUG] All relays deactivated")
        worker = None
        thread = None
        print("[DEBUG] Stop sequence completed successfully")
        return True
    except Exception as e:
        print(f"[ERROR] Stop sequence failed: {e}")
        return False

def change_relay_hats():
    global relay_handler, app_settings  # use app_settings
    num_hats, ok = QInputDialog.getInt(None, "Number of Relay Hats", 
                                        "Enter the number of relay hats:", min=1, max=8)
    if not ok:
        return

    app_settings['num_hats'] = num_hats
    app_settings['relay_pairs'] = create_relay_pairs(num_hats)
    
    relay_unit_manager = RelayUnitManager(app_settings)
    relay_handler.update_relay_units(relay_unit_manager.get_all_relay_units(), num_hats)

    relay_units = relay_unit_manager.get_all_relay_units()
    _update_gui_relay_units(relay_units)

    save_settings(app_settings)
    
    cleanup()
    
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
    gui.projects_section.relay_units = relay_units
    gui.projects_section.schedules_tab.relay_units = relay_units
    gui.projects_section.schedules_tab.relay_containers = {}
    
    gui.projects_section.schedules_tab.layout.removeItem(
        gui.projects_section.schedules_tab.relay_layout
    )
    gui.projects_section.schedules_tab.relay_layout = QHBoxLayout()

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

    setup()

    redirector = StreamRedirector()
    redirector.message_signal.connect(gui.system_message_signal)

    sys.stdout = redirector
    sys.stderr = redirector

    gui.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()