#!/usr/bin/env python3
"""
Startup Performance Test Script

This script measures the time it takes for the application to start up
and become responsive. Run this to benchmark startup performance improvements.
"""

import time
import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

def measure_startup():
    """Measure application startup time."""
    print("Starting startup performance test...")

    start_time = time.time()

    # Import and start the application
    try:
        from main import main
        print("✓ Imports completed")

        # We'll need to modify main() to not actually run the event loop
        # For now, let's measure up to GUI creation
        from main import SafeQApplication
        from ui.style.theme import StyleManager

        app = SafeQApplication(sys.argv)
        print(".2f")

        # Apply theme
        style_manager = StyleManager(app)
        app.setProperty('style_manager', style_manager)
        style_manager.apply("light")
        print(".2f")

        # Test background initialization
        from ui.splash_screen import InitializationWorker
        worker = InitializationWorker()
        worker.start()
        print(".2f")

        # Wait for initialization to complete
        init_start = time.time()
        while not worker.isFinished():
            app.processEvents()
            time.sleep(0.01)  # Small delay to avoid busy waiting

        init_time = time.time() - init_start
        print(".2f")

        # Create GUI
        gui_start = time.time()
        from main import _create_gui_from_components
        components = worker._components if hasattr(worker, '_components') else {}
        gui = _create_gui_from_components(components)
        gui_time = time.time() - gui_start
        print(".2f")

        total_time = time.time() - start_time
        print(f"\n{'='*50}")
        print("STARTUP PERFORMANCE RESULTS:"
        print(".2f")
        print(".2f")
        print(".2f")
        print(".2f")
        print(f"{'='*50}")

        # Test lazy loading performance
        print("\nTesting lazy loading...")
        lazy_start = time.time()

        # Simulate switching to Schedules tab
        gui.main_tab_widget.setCurrentIndex(gui.settings_tab_index)
        app.processEvents()
        settings_load_time = time.time() - lazy_start
        print(".2f")

        return total_time

    except Exception as e:
        print(f"Error during startup test: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    measure_startup()