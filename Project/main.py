#!/usr/bin/env python3
import sys, os, time, traceback
from PyQt5.QtWidgets import (QApplication, QInputDialog, QListWidget, QVBoxLayout, QLabel, QHBoxLayout)
from PyQt5.QtCore import Qt, QThread, QObject, pyqtSignal, QTimer, QMutex, QMutexLocker
from utils.volume_calculator import VolumeCalculator
from gpio.relay_worker import RelayWorker
from ui.gui import RodentRefreshmentGUI
from gpio.gpio_handler import RelayHandler
from notifications.notifications import NotificationHandler
from settings.config import load_settings, save_settings
from controllers.projects_controller import ProjectsController
from models.database_handler import DatabaseHandler
from models.login_system import LoginSystem
from controllers.system_controller import SystemController
from controllers.pump_controller import PumpController
from models.relay_unit_manager import RelayUnitManager
from ui.SettingsTab import SettingsTab

# =============================================================================
# Global exception hook and stream redirection (unchanged)
# =============================================================================
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

# =============================================================================
# Global thread and worker variables
# =============================================================================
thread = None
worker = None

# =============================================================================
# setup() – create our global objects and UI
# =============================================================================
def setup():
    global relay_handler, app_settings, gui, notification_handler, controller, database_handler, login_system, system_controller

    database_handler = DatabaseHandler()
    system_controller = SystemController(database_handler)
    # Use a distinct global settings dictionary.
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

    gui.settings_tab = SettingsTab(
        system_controller=system_controller,
        suggest_callback=gui.suggest_settings_callback,
        push_callback=gui.push_settings_callback,
        save_slack_callback=gui.save_slack_credentials_callback,
        run_stop_section=gui.run_stop_section,
        login_system=login_system,
        print_to_terminal=gui.print_to_terminal,
        database_handler=database_handler
    )

# =============================================================================
# run_program() – create a new worker and thread and start it.
# =============================================================================
def run_program(schedule, mode, window_start, window_end):
    global thread, worker, notification_handler, controller, system_controller, database_handler
    try:
        print("\nDEBUG - run_program:")
        print(f"system_controller type: {type(system_controller)}")
        print(f"Running program with schedule: {schedule.name}, mode: {mode}")

        # Build a settings dictionary from the system controller.
        worker_settings = {}
        if hasattr(system_controller, 'settings'):
            worker_settings = system_controller.settings.copy()

        # Update with schedule‐specific settings.
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

        # If a previous thread exists, quit it.
        global thread, worker
        if thread is not None:
            thread.quit()
            thread.wait()

        thread = QThread()
        if not isinstance(system_controller, QObject):
            raise TypeError("system_controller must be a SystemController instance")

        # Create a new RelayWorker instance.
        worker = RelayWorker(
            worker_settings,
            relay_handler,
            notification_handler,
            system_controller
        )
        worker.moveToThread(thread)

        # Connect the worker's finished signal to:
        #   • thread.quit() – so the thread stops,
        #   • worker.deleteLater() – so the worker cleans itself up,
        #   • cleanup() – our centralized cleanup function (only once).
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(cleanup)
        thread.finished.connect(thread.deleteLater)
        worker.progress.connect(lambda message: print(message))

        thread.started.connect(worker.run_cycle)
        thread.start()

        print("Program Started")
    except Exception as e:
        print(f"Failed to run program: {e}")
        if notification_handler:
            notification_handler.send_slack_notification(f"Program error: {e}")

# =============================================================================
# Centralized cleanup() – called once when the worker finishes.
# =============================================================================
def cleanup():
    global thread, worker
    print("[DEBUG] Starting cleanup process")
    # Only proceed if the worker is not running.
    if worker and worker._is_running:
        print("[DEBUG] Worker still running, waiting for completion")
        return
    try:
        if relay_handler:
            relay_handler.set_all_relays(0)
            print("[DEBUG] All relays deactivated")
        # Do not call worker.stop() again if it has already been stopped.
        worker = None
        if thread is not None and thread.isRunning():
            thread.quit()
            thread.wait()
        thread = None
        # Reset the UI (only once)
        gui.run_stop_section.reset_ui()
        print("[DEBUG] Cleanup completed. Program ready for the next job.")
    except Exception as e:
        print(f"[ERROR] Unexpected error during cleanup: {e}")

# =============================================================================
# stop_program() – called when the user clicks "Stop."
# =============================================================================
def stop_program():
    global thread, worker, relay_handler
    try:
        print("[DEBUG] Starting stop sequence")
        if worker:
            worker.stop()  # This will cause the worker to emit finished, triggering cleanup().
            print("[DEBUG] Worker stop() called")
        if thread and thread.isRunning():
            if not thread.wait(2000):
                print("[DEBUG] Thread timeout - forcing termination")
                thread.terminate()
            thread.wait()
            print("[DEBUG] Thread stopped")
        if relay_handler:
            relay_handler.set_all_relays(0)
            print("[DEBUG] All relays deactivated")
        # We do not explicitly call cleanup() here; it will be called by worker.finished.
        print("[DEBUG] Stop sequence completed successfully")
        return True
    except Exception as e:
        print(f"[ERROR] Stop sequence failed: {e}")
        return False

# =============================================================================
# RelayWorker.stop() – part of the worker; called only once.
# =============================================================================
# (Inside RelayWorker class, use the following stop() method implementation)
#
#     def stop(self):
#         with QMutexLocker(self.mutex):
#             self._is_running = False
#         self.monitor_timer.stop()
#         self.main_timer.stop()
#         for timer in self.timers:
#             try:
#                 timer.stop()  # No need to call deleteLater() since timers are parented.
#             except RuntimeError as ex:
#                 self.progress.emit(f"Timer already deleted: {ex}")
#         self.timers.clear()
#         self.progress.emit("RelayWorker stopped")
#         self.finished.emit()
#
# This method is only called once (either by stop_program() or when the job completes naturally).

# =============================================================================
# change_relay_hats() and helper functions (unchanged)
# =============================================================================
def change_relay_hats():
    global relay_handler, app_settings
    num_hats, ok = QInputDialog.getInt(None, "Number of Relay Hats", 
                                        "Enter the number of relay hats:", min=1, max=8)
    if not ok:
        return
    app_settings['num_hats'] = num_hats
    app_settings['relay_pairs'] = create_relay_pairs(num_hats)
    relay_unit_manager = RelayUnitManager(app_settings)
    relay_handler.update_relay_units(relay_unit_manager.get_all_relay_units(), num_hats)
    _update_gui_relay_units(relay_unit_manager.get_all_relay_units())
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
    gui.projects_section.schedules_tab.layout.removeItem(gui.projects_section.schedules_tab.relay_layout)
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
    gui.projects_section.schedules_tab.layout.addLayout(gui.projects_section.schedules_tab.relay_layout)

# =============================================================================
# Main entry point
# =============================================================================
def main():
    app = QApplication(sys.argv)
    setup()
    redirector = StreamRedirector()
    redirector.message_signal.connect(gui.system_message_signal)
    sys.stdout = redirector
    sys.stderr = redirector
    
    # Check for UI updates
    try:
        from ui.update_notifier import UpdateNotifier
        UpdateNotifier.check_for_updates()
    except Exception as e:
        print(f"Error checking for UI updates: {e}")
    
    gui.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()