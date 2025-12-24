#!/usr/bin/env python3
"""
Rodent Refreshment Regulator - Main Entry Point

Optimized startup with:
- Splash screen for immediate visual feedback
- Progressive background initialization
- Deferred heavy component loading

References:
- Qt Threading: https://doc.qt.io/qt-5/thread-basics.html
- Qt Application Lifecycle: https://doc.qt.io/qt-5/qapplication.html
"""
import sys, os, time, traceback
from PyQt5.QtWidgets import (QApplication, QInputDialog, QListWidget, QVBoxLayout, QLabel, QHBoxLayout)
from PyQt5.QtCore import Qt, QThread, QObject, pyqtSignal, QTimer, QMutex, QMutexLocker
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtNetwork import QLocalServer, QLocalSocket

# Defer heavy imports for faster startup
# These will be imported in InitializationWorker or after splash
from ui.style.theme import StyleManager

# =============================================================================
# Global exception hook and stream redirection (unchanged)
# =============================================================================
import os
from datetime import datetime

_DEBUG_LOG_PATH = os.path.expanduser('~/rrr_app_debug.log')

def _dbg(message: str):
    try:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        with open(_DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(f"{ts} [RRR] {message}\n")
    except Exception:
        # Never raise from debug logging
        pass

def exception_hook(exctype, value, tb):
    """Global exception handler for uncaught exceptions outside Qt event loop."""
    msg = "".join(traceback.format_exception(exctype, value, tb))
    print(msg)
    _dbg(f"UNHANDLED EXCEPTION: {msg}")
    # Don't call sys.exit() here - let the app continue if possible
    # sys.exit(1) was causing issues with Qt's event loop

sys.excepthook = exception_hook


class SafeQApplication(QApplication):
    """
    Custom QApplication that catches exceptions in Qt event handlers.
    
    Per Qt documentation (https://doc.qt.io/qt-5/qcoreapplication.html#notify):
    "Future direction: This function will not be called for objects that live 
    outside the main thread in Qt 6. Applications that need that functionality 
    should find other solutions for their use cases."
    
    Per PyQt5 documentation:
    Exceptions raised in event handlers are caught by Qt's C++ event loop before
    reaching Python's exception handling. Override notify() to catch them.
    
    Reference: https://www.riverbankcomputing.com/static/Docs/PyQt5/incompatibilities.html
    """
    
    def notify(self, receiver, event):
        """
        Override QApplication.notify() to catch exceptions in event handlers.
        
        This is the recommended approach per Qt and PyQt5 documentation for
        handling exceptions that occur during event processing.
        """
        try:
            return super().notify(receiver, event)
        except Exception as e:
            # Log the exception with full traceback
            exc_info = sys.exc_info()
            msg = "".join(traceback.format_exception(*exc_info))
            
            # Log to console and debug file
            print(f"\n[Qt Event Handler Exception]\n{msg}")
            _dbg(f"QT EVENT EXCEPTION: {msg}")
            
            # Don't crash the app - return False to indicate event not handled
            # This allows the app to continue running
            return False

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

class ControlSignals(QObject):
    stop_requested = pyqtSignal()

control_signals = ControlSignals()

# =============================================================================
# setup() – Legacy function, now handled by SplashScreen + InitializationWorker
# Kept for backwards compatibility if called directly
# =============================================================================
def setup():
    """
    Legacy setup function - now handled by splash screen background initialization.
    
    This function is kept for backwards compatibility but the preferred approach
    is to use SplashScreen with InitializationWorker for non-blocking startup.
    """
    global relay_handler, app_settings, gui, notification_handler, controller
    global database_handler, login_system, system_controller
    
    # Import all required modules
    from models.database_handler import DatabaseHandler
    from controllers.system_controller import SystemController
    from models.relay_unit_manager import RelayUnitManager
    from gpio.gpio_handler import RelayHandler
    from controllers.projects_controller import ProjectsController
    from controllers.pump_controller import PumpController
    from notifications.notifications import NotificationHandler
    from models.login_system import LoginSystem
    from ui.gui import RodentRefreshmentGUI
    from ui.SettingsTab import SettingsTab

    database_handler = DatabaseHandler()
    system_controller = SystemController(database_handler)
    app_settings = system_controller.settings

    try:
        system_controller.ensure_solenoid_defaults()
        app_settings = system_controller.settings
        print(f"✓ Hardware auto-configuration completed")
    except Exception as e:
        print(f"Hardware auto-configuration failed: {e}")

    relay_unit_manager = RelayUnitManager(app_settings)
    relay_handler = RelayHandler(relay_unit_manager, app_settings['num_hats'])
    app_settings['relay_unit_manager'] = relay_unit_manager
    print(f"✓ RelayUnitManager initialized in {relay_unit_manager.get_hardware_mode()} mode")

    controller = ProjectsController()
    pump_controller = PumpController(relay_handler, database_handler)
    controller.pump_controller = pump_controller
    app_settings['pump_controller'] = pump_controller

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
    """
    Start schedule execution with optimized worker thread creation.
    
    Optimization: Worker creation is lightweight; heavy operations happen
    inside the worker thread via run_cycle().
    
    Reference: https://doc.qt.io/qt-5/qthread.html#details
    """
    global thread, worker, notification_handler, controller, system_controller, database_handler
    
    # Deferred imports for components used by worker
    from gpio.relay_worker import RelayWorker
    
    try:
        print(f"\n[RUN] Starting schedule: {schedule.name}, mode: {mode}")

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

        # Wire worker progress into the UI progress tracker (if available)
        # CRITICAL: Use Qt.QueuedConnection to ensure GUI updates happen in GUI thread
        try:
            if gui and hasattr(gui, 'run_stop_section') and hasattr(gui.run_stop_section, 'progress_tracker'):
                tracker = gui.run_stop_section.progress_tracker
                # Volume updates: update per-animal progress
                def _on_volume_updated(animal_id_str: str, total_ml: float):
                    try:
                        animal_id = int(animal_id_str)
                    except Exception:
                        # Fallback: ignore bad ids
                        return
                    try:
                        tracker.update_animal_progress(animal_id, total_ml, status="Delivering")
                    except Exception:
                        pass
                try:
                    worker.volume_updated.disconnect()
                except Exception:
                    pass
                # Use QueuedConnection to ensure tracker updates happen in GUI thread
                worker.volume_updated.connect(_on_volume_updated, Qt.QueuedConnection)
                # Finished: mark schedule complete in tracker (also queued to GUI thread)
                worker.finished.connect(lambda: getattr(tracker, 'schedule_complete', lambda: None)(), Qt.QueuedConnection)
        except Exception:
            pass

        # Ensure stop requests are delivered to the worker's thread (Qt.QueuedConnection)
        try:
            control_signals.stop_requested.disconnect()
        except Exception:
            pass
        control_signals.stop_requested.connect(worker.stop, Qt.QueuedConnection)

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
            # Emit a queued stop so QTimers are stopped from the owning thread
            control_signals.stop_requested.emit()
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
# change_relay_hats() and helper functions
# =============================================================================
def change_relay_hats():
    """Update relay hat configuration at runtime."""
    global relay_handler, app_settings
    
    # Deferred imports
    from models.relay_unit_manager import RelayUnitManager
    from settings.config import save_settings
    
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
# Main entry point with optimized startup
# =============================================================================

# Global reference for components initialized by splash screen
_initialized_components = {}

def _create_gui_from_components(components: dict):
    """
    Create GUI after background initialization completes.
    
    This is called from the main thread after InitializationWorker finishes.
    Per Qt Documentation: All GUI operations must happen on the main thread.
    
    Reference: https://doc.qt.io/qt-5/thread-basics.html#gui-thread-and-worker-thread
    """
    global relay_handler, app_settings, gui, notification_handler, controller
    global database_handler, login_system, system_controller
    
    # Import GUI components (deferred to after splash)
    from ui.gui import RodentRefreshmentGUI
    from ui.SettingsTab import SettingsTab
    from gpio.relay_worker import RelayWorker
    from utils.volume_calculator import VolumeCalculator
    from notifications.notifications import NotificationHandler
    from settings.config import load_settings, save_settings
    from controllers.projects_controller import ProjectsController
    from models.database_handler import DatabaseHandler
    from models.login_system import LoginSystem
    from controllers.system_controller import SystemController
    from controllers.pump_controller import PumpController
    from models.relay_unit_manager import RelayUnitManager
    from gpio.gpio_handler import RelayHandler
    
    # Extract components from background initialization
    database_handler = components.get('database_handler')
    system_controller = components.get('system_controller')
    relay_handler = components.get('relay_handler')
    notification_handler = components.get('notification_handler')
    login_system = components.get('login_system')
    controller = components.get('controller')
    
    app_settings = system_controller.settings if system_controller else {}
    
    # Create the main GUI
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
    
    return gui


def main():
    """
    Application entry point with optimized startup sequence.
    
    Optimization Strategy:
    1. Show splash screen immediately (instant visual feedback)
    2. Initialize heavy components in background thread
    3. Create GUI after initialization completes
    4. Transition from splash to main window
    
    Reference: https://doc.qt.io/qt-5/qsplashscreen.html
    """
    global gui, system_controller
    
    # Single-instance guard using QLocalServer
    instance_key = 'rrr_single_instance_v1'
    socket = QLocalSocket()
    socket.connectToServer(instance_key)
    if socket.waitForConnected(100):
        try:
            socket.write(b'raise')
            socket.flush()
            socket.waitForBytesWritten(100)
        except Exception:
            pass
        # Another instance is running; exit
        return
    socket.abort()

    # Use SafeQApplication to catch exceptions in Qt event handlers
    app = SafeQApplication(sys.argv)
    
    # Apply initial theme immediately for splash screen consistency
    try:
        _style_manager = StyleManager(app)
        app.setProperty('style_manager', _style_manager)
        _style_manager.apply("light")
    except Exception:
        pass
    
    # Prevent implicit quit
    QGuiApplication.setQuitOnLastWindowClosed(False)
    try:
        app.setQuitOnLastWindowClosed(False)
    except Exception:
        pass

    # Import and show splash screen immediately
    from ui.splash_screen import SplashScreen
    splash = SplashScreen()
    splash.show()
    app.processEvents()  # Force paint before heavy initialization
    
    # Variables to hold GUI after initialization
    main_window = None
    redirector = None
    server = None
    
    def on_initialization_complete(components: dict):
        """Handle completion of background initialization."""
        nonlocal main_window, redirector, server
        global gui, system_controller
        
        try:
            # Create GUI from initialized components
            main_window = _create_gui_from_components(components)
            gui = main_window
            
            # Apply persisted theme
            try:
                style_mgr = app.property('style_manager')
                if style_mgr and system_controller:
                    desired_theme = system_controller.settings.get('theme', 'light')
                    style_mgr.apply(desired_theme)
            except Exception:
                pass
            
            # Setup stream redirection
            redirector = StreamRedirector()
            redirector.message_signal.connect(gui.system_message_signal)
            sys.stdout = redirector
            sys.stderr = redirector
            
            # Check for updates (non-blocking)
            try:
                from ui.update_notifier import UpdateNotifier
                UpdateNotifier.check_for_updates()
            except Exception as e:
                print(f"Error checking for UI updates: {e}")
            
            # Show main window with login overlay if not logged in
            gui.show()
            
            # Show glassmorphism login if not logged in
            if login_system and not login_system.is_logged_in():
                _show_login_overlay(gui)
            
            # Setup local server for single-instance handling
            server = QLocalServer()
            try:
                QLocalServer.removeServer(instance_key)
            except Exception:
                pass
            server.listen(instance_key)
            
            def _handle_new_connection():
                conn = server.nextPendingConnection()
                if conn:
                    try:
                        conn.readAll()
                        conn.disconnectFromServer()
                    except Exception:
                        pass
                try:
                    gui.show()
                    gui.raise_()
                    gui.activateWindow()
                except Exception:
                    pass
            
            server.newConnection.connect(_handle_new_connection)
            
        except Exception as e:
            print(f"Error creating GUI: {e}")
            traceback.print_exc()
    
    # Connect splash completion to GUI creation
    splash.initialization_complete.connect(on_initialization_complete)
    
    # Start background initialization
    splash.start_initialization()
    
    # Setup lifecycle logging (debug)
    try:
        from PyQt5.QtCore import QObject, QEvent
        class _CloseLogger(QObject):
            def eventFilter(self, obj, event):
                try:
                    if event.type() == QEvent.Close:
                        name = getattr(obj, 'objectName', lambda: '')() or obj.__class__.__name__
                        _dbg(f"Close event on: {name}")
                except Exception:
                    pass
                return False
        _close_logger = _CloseLogger()
        app.installEventFilter(_close_logger)
    except Exception:
        pass
    
    sys.exit(app.exec_())


def _show_login_overlay(parent_widget):
    """
    Show the glassmorphism login overlay.
    
    Design: Full-window frosted glass overlay inspired by iOS.
    """
    from ui.glassmorphism_login import GlassmorphismLoginOverlay
    
    overlay = GlassmorphismLoginOverlay(
        login_system,
        database_handler=database_handler,
        parent=parent_widget
    )
    
    def on_login_success(user_info):
        """Handle successful login."""
        parent_widget.on_login(user_info)
    
    def on_login_cancelled():
        """Handle guest mode selection."""
        pass  # Guest mode already set in overlay
    
    overlay.login_successful.connect(on_login_success)
    overlay.login_cancelled.connect(on_login_cancelled)
    overlay.show()

if __name__ == "__main__":
    main()