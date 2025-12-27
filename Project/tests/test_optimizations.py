#!/usr/bin/env python3
"""
Comprehensive Test Script for RRR Optimizations

Tests the following:
1. Module imports and dependencies
2. Database handler operations
3. System controller initialization
4. Relay system initialization
5. Splash screen InitializationWorker (headless)
6. Run button optimization methods
7. Schedule execution data flow

Run with: python3 tests/test_optimizations.py

Reference: PyQt5 Testing - https://doc.qt.io/qt-5/qtest.html
"""

import sys
import os
import time
import traceback
from datetime import datetime, timedelta

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Test results tracking
TESTS_RUN = 0
TESTS_PASSED = 0
TESTS_FAILED = 0
TEST_RESULTS = []


def test_result(name: str, passed: bool, details: str = ""):
    """Record a test result."""
    global TESTS_RUN, TESTS_PASSED, TESTS_FAILED
    TESTS_RUN += 1
    if passed:
        TESTS_PASSED += 1
        status = "✓ PASS"
    else:
        TESTS_FAILED += 1
        status = "✗ FAIL"
    
    result = f"{status}: {name}"
    if details:
        result += f"\n         {details}"
    TEST_RESULTS.append((name, passed, details))
    print(result)


def section(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


# =============================================================================
# TEST 1: Module Imports
# =============================================================================
def test_imports():
    """Test that all critical modules can be imported."""
    section("1. MODULE IMPORTS")
    
    modules = [
        ("models.database_handler", "DatabaseHandler"),
        ("controllers.system_controller", "SystemController"),
        ("models.relay_unit_manager", "RelayUnitManager"),
        ("gpio.gpio_handler", "RelayHandler"),
        ("controllers.projects_controller", "ProjectsController"),
        ("controllers.pump_controller", "PumpController"),
        ("notifications.notifications", "NotificationHandler"),
        ("models.login_system", "LoginSystem"),
        ("gpio.relay_worker", "RelayWorker"),
        ("ui.splash_screen", "SplashScreen"),
        ("ui.splash_screen", "InitializationWorker"),
    ]
    
    for module_path, class_name in modules:
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            test_result(f"Import {module_path}.{class_name}", True)
        except Exception as e:
            test_result(f"Import {module_path}.{class_name}", False, str(e))


# =============================================================================
# TEST 2: Database Handler
# =============================================================================
def test_database_handler():
    """Test database handler initialization and operations."""
    section("2. DATABASE HANDLER")
    
    try:
        from models.database_handler import DatabaseHandler
        db = DatabaseHandler()
        test_result("DatabaseHandler initialization", True)
    except Exception as e:
        test_result("DatabaseHandler initialization", False, str(e))
        return None
    
    # Test connection
    try:
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            test_result("Database connection", result[0] == 1)
    except Exception as e:
        test_result("Database connection", False, str(e))
    
    # Test get_all_schedules
    try:
        schedules = db.get_all_schedules()
        test_result("get_all_schedules()", True, f"Found {len(schedules)} schedules")
    except Exception as e:
        test_result("get_all_schedules()", False, str(e))
    
    # Test get_schedule_details if schedules exist
    if schedules:
        try:
            schedule_id = schedules[0][0]  # First schedule's ID
            details = db.get_schedule_details(schedule_id)
            test_result("get_schedule_details()", len(details) > 0, 
                       f"Schedule ID {schedule_id}")
        except Exception as e:
            test_result("get_schedule_details()", False, str(e))
    
    return db


# =============================================================================
# TEST 3: System Controller
# =============================================================================
def test_system_controller(db):
    """Test system controller initialization."""
    section("3. SYSTEM CONTROLLER")
    
    if db is None:
        test_result("SystemController (skipped)", False, "No database handler")
        return None
    
    try:
        from controllers.system_controller import SystemController
        sc = SystemController(db)
        test_result("SystemController initialization", True)
    except Exception as e:
        test_result("SystemController initialization", False, str(e))
        return None
    
    # Test settings
    try:
        settings = sc.settings
        test_result("Settings loaded", isinstance(settings, dict), 
                   f"{len(settings)} settings keys")
    except Exception as e:
        test_result("Settings loaded", False, str(e))
    
    # Test required settings keys
    required_keys = ['num_hats', 'hardware_mode']
    for key in required_keys:
        try:
            value = sc.settings.get(key)
            test_result(f"Setting '{key}' exists", value is not None, 
                       f"value={value}")
        except Exception as e:
            test_result(f"Setting '{key}' exists", False, str(e))
    
    return sc


# =============================================================================
# TEST 4: Relay System
# =============================================================================
def test_relay_system(sc):
    """Test relay unit manager and handler."""
    section("4. RELAY SYSTEM")
    
    if sc is None:
        test_result("Relay system (skipped)", False, "No system controller")
        return None
    
    # Test RelayUnitManager
    try:
        from models.relay_unit_manager import RelayUnitManager
        rum = RelayUnitManager(sc.settings)
        units = rum.get_all_relay_units()
        test_result("RelayUnitManager initialization", True, 
                   f"{len(units)} relay units")
    except Exception as e:
        test_result("RelayUnitManager initialization", False, str(e))
        return None
    
    # Test hardware mode
    try:
        mode = rum.get_hardware_mode()
        test_result("Hardware mode detection", mode in ['solenoid', 'pump'], 
                   f"mode={mode}")
    except Exception as e:
        test_result("Hardware mode detection", False, str(e))
    
    # Test RelayHandler
    try:
        from gpio.gpio_handler import RelayHandler
        rh = RelayHandler(rum, sc.settings['num_hats'])
        test_result("RelayHandler initialization", True)
        return rh
    except Exception as e:
        test_result("RelayHandler initialization", False, str(e))
        return None


# =============================================================================
# TEST 5: Splash Screen Components (Headless)
# =============================================================================
def test_splash_components():
    """Test splash screen components without GUI."""
    section("5. SPLASH SCREEN COMPONENTS")
    
    # Test InitializationWorker can be created
    try:
        from ui.splash_screen import InitializationWorker
        worker = InitializationWorker()
        test_result("InitializationWorker creation", True)
    except Exception as e:
        test_result("InitializationWorker creation", False, str(e))
        return
    
    # Test worker has required signals
    try:
        has_progress = hasattr(worker, 'progress')
        has_finished = hasattr(worker, 'finished')
        has_error = hasattr(worker, 'error')
        test_result("Worker signals exist", 
                   has_progress and has_finished and has_error,
                   f"progress={has_progress}, finished={has_finished}, error={has_error}")
    except Exception as e:
        test_result("Worker signals exist", False, str(e))
    
    # Test worker run method exists
    try:
        has_run = hasattr(worker, 'run') and callable(worker.run)
        test_result("Worker.run() method exists", has_run)
    except Exception as e:
        test_result("Worker.run() method exists", False, str(e))


# =============================================================================
# TEST 6: Run Button Optimization Methods
# =============================================================================
def test_run_optimization():
    """Test that run button optimization methods exist."""
    section("6. RUN BUTTON OPTIMIZATION")
    
    # We can't fully test the RunStopSection without a GUI, but we can
    # verify the methods exist in the source code
    try:
        import inspect
        from ui.run_stop_section import RunStopSection
        
        # Check for _prepare_and_execute_schedule method
        has_prepare = hasattr(RunStopSection, '_prepare_and_execute_schedule')
        test_result("_prepare_and_execute_schedule() exists", has_prepare)
        
        # Check for _reset_run_button method
        has_reset = hasattr(RunStopSection, '_reset_run_button')
        test_result("_reset_run_button() exists", has_reset)
        
        # Check run_program method signature
        run_method = getattr(RunStopSection, 'run_program', None)
        if run_method:
            source = inspect.getsource(run_method)
            has_process_events = 'processEvents' in source
            has_singleshot = 'singleShot' in source
            test_result("run_program() uses processEvents()", has_process_events,
                       "For immediate UI update")
            test_result("run_program() uses QTimer.singleShot()", has_singleshot,
                       "For deferred execution")
        else:
            test_result("run_program() method exists", False)
            
    except Exception as e:
        test_result("Run optimization methods", False, str(e))


# =============================================================================
# TEST 7: Schedule Data Flow
# =============================================================================
def test_schedule_data_flow(db):
    """Test the complete schedule data flow."""
    section("7. SCHEDULE DATA FLOW")
    
    if db is None:
        test_result("Schedule data flow (skipped)", False, "No database handler")
        return
    
    # Get a test schedule
    try:
        schedules = db.get_all_schedules()
        if not schedules:
            test_result("Test schedule available", False, "No schedules in database")
            return
        
        schedule_id = schedules[0][0]
        schedule_name = schedules[0][1]
        test_result("Test schedule available", True, 
                   f"ID={schedule_id}, Name={schedule_name}")
    except Exception as e:
        test_result("Test schedule available", False, str(e))
        return
    
    # Test get_schedule_details
    try:
        details = db.get_schedule_details(schedule_id)
        if details:
            detail = details[0]
            has_animals = 'animal_ids' in detail
            has_relay = 'relay_unit_assignments' in detail
            has_outputs = 'desired_water_outputs' in detail
            test_result("Schedule details structure", 
                       has_animals and has_relay and has_outputs,
                       f"animals={has_animals}, relay={has_relay}, outputs={has_outputs}")
            
            # Show animal count
            animal_count = len(detail.get('animal_ids', []))
            test_result("Animals in schedule", animal_count > 0, 
                       f"{animal_count} animals")
        else:
            test_result("Schedule details structure", False, "Empty details")
    except Exception as e:
        test_result("Schedule details structure", False, str(e))
    
    # Test delivery mode detection
    try:
        details = db.get_schedule_details(schedule_id)
        if details:
            mode = details[0].get('delivery_mode', 'Unknown')
            test_result("Delivery mode", mode in ['Staggered', 'Instant', 'staggered', 'instant'],
                       f"mode={mode}")
    except Exception as e:
        test_result("Delivery mode", False, str(e))


# =============================================================================
# TEST 8: Main.py Configuration
# =============================================================================
def test_main_config():
    """Test main.py configuration."""
    section("8. MAIN.PY CONFIGURATION")
    
    try:
        # Read main.py and check for USE_SPLASH_SCREEN
        main_path = os.path.join(PROJECT_ROOT, 'main.py')
        with open(main_path, 'r') as f:
            content = f.read()
        
        has_splash_flag = 'USE_SPLASH_SCREEN' in content
        test_result("USE_SPLASH_SCREEN flag exists", has_splash_flag)
        
        # Check if splash is disabled (current workaround)
        splash_disabled = 'USE_SPLASH_SCREEN = False' in content
        test_result("Splash screen disabled (workaround)", splash_disabled,
                   "Expected: False for stability on Pi")
        
        # Check for _main_with_splash function
        has_with_splash = '_main_with_splash' in content
        test_result("_main_with_splash() exists", has_with_splash)
        
        # Check for _main_without_splash function
        has_without_splash = '_main_without_splash' in content
        test_result("_main_without_splash() exists", has_without_splash)
        
        # Check for _create_gui_from_components function
        has_create_gui = '_create_gui_from_components' in content
        test_result("_create_gui_from_components() exists", has_create_gui)
        
    except Exception as e:
        test_result("Main.py configuration", False, str(e))


# =============================================================================
# TEST 9: Timer Overflow Prevention
# =============================================================================
def test_timer_overflow():
    """Test timer overflow prevention in relay_worker."""
    section("9. TIMER OVERFLOW PREVENTION")
    
    try:
        worker_path = os.path.join(PROJECT_ROOT, 'gpio', 'relay_worker.py')
        with open(worker_path, 'r') as f:
            content = f.read()
        
        # Check for MAX_TIMER_DELAY_MS
        has_max_delay = 'MAX_TIMER_DELAY_MS' in content
        test_result("MAX_TIMER_DELAY_MS constant exists", has_max_delay)
        
        # Check for 2-week cap (1,209,600,000 ms)
        has_two_week_cap = '1_209_600_000' in content or '1209600000' in content
        test_result("2-week timer cap implemented", has_two_week_cap,
                   "MAX_TIMER_DELAY_MS = 1,209,600,000 ms")
        
    except Exception as e:
        test_result("Timer overflow prevention", False, str(e))


# =============================================================================
# TEST 10: QSS Theme Files
# =============================================================================
def test_theme_files():
    """Test QSS theme files exist and have teal accent."""
    section("10. QSS THEME FILES")
    
    themes = [
        ('ui/style/app-light.qss', 'Light theme'),
        ('ui/style/app-dark.qss', 'Dark theme'),
    ]
    
    for theme_path, name in themes:
        full_path = os.path.join(PROJECT_ROOT, theme_path)
        try:
            with open(full_path, 'r') as f:
                content = f.read()
            
            # Check file exists and has content
            test_result(f"{name} file exists", len(content) > 100,
                       f"{len(content)} bytes")
            
            # Check for teal accent color
            has_teal = '#0D9488' in content or '#14B8A6' in content
            test_result(f"{name} has teal accent", has_teal,
                       "Primary accent color")
            
            # Check for IBM Plex Sans
            has_font = 'IBM Plex Sans' in content
            test_result(f"{name} uses IBM Plex Sans", has_font)
            
        except FileNotFoundError:
            test_result(f"{name} file exists", False, "File not found")
        except Exception as e:
            test_result(f"{name}", False, str(e))


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================
def run_all_tests():
    """Run all tests and print summary."""
    print("\n" + "="*60)
    print("  RODENT REFRESHMENT REGULATOR - OPTIMIZATION TESTS")
    print("="*60)
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Project: {PROJECT_ROOT}")
    print("="*60)
    
    start_time = time.time()
    
    # Run tests
    test_imports()
    db = test_database_handler()
    sc = test_system_controller(db)
    rh = test_relay_system(sc)
    test_splash_components()
    test_run_optimization()
    test_schedule_data_flow(db)
    test_main_config()
    test_timer_overflow()
    test_theme_files()
    
    elapsed = time.time() - start_time
    
    # Print summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)
    print(f"  Total Tests: {TESTS_RUN}")
    print(f"  Passed:      {TESTS_PASSED} ✓")
    print(f"  Failed:      {TESTS_FAILED} ✗")
    print(f"  Pass Rate:   {TESTS_PASSED/TESTS_RUN*100:.1f}%")
    print(f"  Duration:    {elapsed:.2f}s")
    print("="*60)
    
    if TESTS_FAILED > 0:
        print("\n  FAILED TESTS:")
        for name, passed, details in TEST_RESULTS:
            if not passed:
                print(f"    ✗ {name}")
                if details:
                    print(f"      {details}")
    
    print("\n" + "="*60)
    print("  TEST COMPLETE")
    print("="*60 + "\n")
    
    return TESTS_FAILED == 0


if __name__ == "__main__":
    # Ensure we can find PyQt5
    try:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QCoreApplication
        
        # Create a minimal app for testing (required for some Qt operations)
        app = QCoreApplication.instance()
        if app is None:
            app = QCoreApplication(sys.argv)
    except ImportError as e:
        print(f"ERROR: PyQt5 not available: {e}")
        print("Install with: pip install PyQt5")
        sys.exit(1)
    
    success = run_all_tests()
    sys.exit(0 if success else 1)

