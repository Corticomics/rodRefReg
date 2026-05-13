"""
Data analysis tab for IR sensor visualization.

This module provides a UI tab for visualizing and analyzing drinking data
collected from IR sensors, with support for circadian rhythm analysis.
"""

import logging
import sys
import os
from datetime import datetime, timedelta

# Add the project root to the path to allow imports from ir_module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
        QTableWidget, QTableWidgetItem, QSpinBox, QTabWidget, QGroupBox,
        QFormLayout, QDateEdit, QCheckBox, QFileDialog, QGridLayout, QSplitter
    )
    from PyQt5.QtCore import Qt, QDateTime, pyqtSignal, QSize
    from PyQt5.QtGui import QColor, QPainter, QPen
    
    # Try to import plotting libraries
    MATPLOTLIB_AVAILABLE = False
    try:
        import matplotlib
        matplotlib.use('Qt5Agg')
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        import numpy as np
        MATPLOTLIB_AVAILABLE = True
    except ImportError:
        logging.warning("Matplotlib not available - using simplified charts")
    
    from ir_module.config import is_feature_enabled
    from ir_module.model.drinking_data_model import DrinkingDataModel
    
    logger = logging.getLogger(__name__)
    
    class SimpleChart(QWidget):
        """
        A simple chart widget for when matplotlib is not available.
        
        This provides a basic visualization capability when matplotlib
        cannot be imported.
        """
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setMinimumSize(400, 200)
            
            self.x_values = []
            self.y_values = []
            self.title = ""
            self.x_label = ""
            self.y_label = ""
            
        def set_data(self, x_values, y_values, title="", x_label="", y_label=""):
            """Set the data for the chart."""
            self.x_values = x_values
            self.y_values = y_values
            self.title = title
            self.x_label = x_label
            self.y_label = y_label
            self.update()
            
        def paintEvent(self, event):
            """Paint the chart."""
            if not self.x_values or not self.y_values:
                return
                
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Calculate chart area
            chart_rect = self.rect().adjusted(40, 40, -20, -40)
            
            # Draw title
            painter.drawText(self.rect().adjusted(0, 10, 0, 0), Qt.AlignHCenter, self.title)
            
            # Draw axes
            painter.drawLine(chart_rect.left(), chart_rect.bottom(), chart_rect.right(), chart_rect.bottom())  # X-axis
            painter.drawLine(chart_rect.left(), chart_rect.top(), chart_rect.left(), chart_rect.bottom())  # Y-axis
            
            # Draw labels
            painter.drawText(chart_rect.left() - 30, chart_rect.bottom() + 20, self.x_label)
            painter.drawText(chart_rect.left() - 30, chart_rect.top() - 10, self.y_label)
            
            # Draw data points
            if len(self.x_values) > 1:
                max_y = max(self.y_values) if self.y_values else 1
                
                # Scale points to fit in chart area
                points = []
                for i, y in enumerate(self.y_values):
                    x_pos = chart_rect.left() + (i / (len(self.x_values) - 1)) * chart_rect.width()
                    y_pos = chart_rect.bottom() - (y / max_y) * chart_rect.height()
                    points.append((x_pos, y_pos))
                
                # Draw connecting lines
                pen = QPen(QColor(0, 0, 255), 2)
                painter.setPen(pen)
                for i in range(len(points) - 1):
                    painter.drawLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])
    
    
    class CircadianChart(QWidget):
        """
        Chart for visualizing circadian drinking patterns.
        
        This widget provides a visualization of drinking patterns over
        a 24-hour period, binned into time intervals.
        """
        
        def __init__(self, parent=None):
            super().__init__(parent)
            
            self.layout = QVBoxLayout()
            self.setLayout(self.layout)
            
            if MATPLOTLIB_AVAILABLE:
                # Create matplotlib figure
                self.figure = Figure(figsize=(6, 4), dpi=100)
                self.canvas = FigureCanvas(self.figure)
                self.layout.addWidget(self.canvas)
                
                # Initialize plot
                self.plot = self.figure.add_subplot(111)
            else:
                # Create simple chart
                self.chart = SimpleChart()
                self.layout.addWidget(self.chart)
            
            self.layout.setContentsMargins(0, 0, 0, 0)
            
        def plot_circadian_data(self, data, title="Circadian Drinking Pattern"):
            """
            Plot circadian data.
            
            Args:
                data (dict): Circadian data with time_bins and values.
                title (str): Chart title.
            """
            if not data or not data.get('time_bins') or not data.get('counts'):
                return
                
            time_bins = data['time_bins']
            counts = data['counts']
            
            if MATPLOTLIB_AVAILABLE:
                self.plot.clear()
                
                self.plot.bar(time_bins, counts, width=0.8)
                self.plot.set_title(title)
                self.plot.set_xlabel("Time of Day")
                self.plot.set_ylabel("Drinking Events")
                
                # Rotate x labels for readability
                self.plot.tick_params(axis='x', rotation=45)
                
                self.figure.tight_layout()
                self.canvas.draw()
            else:
                # Use simple chart
                self.chart.set_data(
                    time_bins, 
                    counts, 
                    title=title,
                    x_label="Time of Day",
                    y_label="Drinking Events"
                )
    
    
    class DailyTotalsChart(QWidget):
        """
        Chart for visualizing daily drinking totals.
        
        This widget provides a visualization of drinking volumes and counts
        on a daily basis.
        """
        
        def __init__(self, parent=None):
            super().__init__(parent)
            
            self.layout = QVBoxLayout()
            self.setLayout(self.layout)
            
            if MATPLOTLIB_AVAILABLE:
                # Create matplotlib figure
                self.figure = Figure(figsize=(6, 4), dpi=100)
                self.canvas = FigureCanvas(self.figure)
                self.layout.addWidget(self.canvas)
                
                # Initialize plot with two y-axes
                self.plot = self.figure.add_subplot(111)
                self.plot2 = self.plot.twinx()
            else:
                # Create simple chart
                self.chart = SimpleChart()
                self.layout.addWidget(self.chart)
            
            self.layout.setContentsMargins(0, 0, 0, 0)
            
        def plot_daily_data(self, data, title="Daily Drinking Totals"):
            """
            Plot daily drinking data.
            
            Args:
                data (dict): Daily data with dates, volumes, and counts.
                title (str): Chart title.
            """
            if not data or not data.get('dates') or not data.get('volumes'):
                return
                
            dates = data['dates']
            volumes = data['volumes']
            counts = data.get('counts', [0] * len(dates))
            
            if MATPLOTLIB_AVAILABLE:
                self.plot.clear()
                self.plot2.clear()
                
                # Plot volumes as bars
                bars = self.plot.bar(dates, volumes, color='b', alpha=0.6, label='Volume (ml)')
                self.plot.set_title(title)
                self.plot.set_xlabel("Date")
                self.plot.set_ylabel("Volume (ml)", color='b')
                self.plot.tick_params(axis='y', labelcolor='b')
                
                # Plot counts as line
                line = self.plot2.plot(dates, counts, 'r-', label='Count')
                self.plot2.set_ylabel("Count", color='r')
                self.plot2.tick_params(axis='y', labelcolor='r')
                
                # Rotate x labels for readability
                self.plot.tick_params(axis='x', rotation=45)
                
                # Add legend
                self.figure.legend(loc='upper right')
                
                self.figure.tight_layout()
                self.canvas.draw()
            else:
                # Use simple chart - just show volumes
                self.chart.set_data(
                    dates, 
                    volumes, 
                    title=title,
                    x_label="Date",
                    y_label="Volume (ml)"
                )
    
    
    class DataAnalysisTab(QWidget):
        """
        Main tab for data analysis and visualization.
        
        This tab provides UI for selecting animals, date ranges, and
        visualization options for analyzing drinking patterns.
        """
        
        def __init__(self, database_handler, ir_sensor_manager=None, parent=None):
            """
            Initialize the data analysis tab.
            
            Args:
                database_handler: Database handler for retrieving data.
                ir_sensor_manager: IR sensor manager for real-time updates.
                parent: Parent widget.
            """
            super().__init__(parent)
            
            self.database_handler = database_handler
            self.ir_sensor_manager = ir_sensor_manager
            self.data_model = DrinkingDataModel(database_handler)
            
            self.selected_animal_id = None
            self.selected_bin_size = 5  # Default 5-minute bins
            
            self._setup_ui()
            self._load_animals()
            
            logger.info("DataAnalysisTab initialized")
        
        def _setup_ui(self):
            """Set up the UI components."""
            # Main layout
            main_layout = QVBoxLayout()
            self.setLayout(main_layout)
            
            # Create splitter for resizable sections
            splitter = QSplitter(Qt.Horizontal)
            main_layout.addWidget(splitter)
            
            # Left panel - controls
            controls_widget = QWidget()
            controls_layout = QVBoxLayout(controls_widget)
            
            # Animal selection
            animal_group = QGroupBox("Animal Selection")
            animal_layout = QVBoxLayout()
            
            self.animal_selector = QComboBox()
            self.animal_selector.currentIndexChanged.connect(self._on_animal_selected)
            
            animal_layout.addWidget(QLabel("Select Animal:"))
            animal_layout.addWidget(self.animal_selector)
            
            animal_group.setLayout(animal_layout)
            controls_layout.addWidget(animal_group)
            
            # Time range selection
            time_group = QGroupBox("Time Range")
            time_layout = QFormLayout()
            
            self.start_date = QDateEdit()
            self.start_date.setCalendarPopup(True)
            self.start_date.setDate(QDateTime.currentDateTime().addDays(-7).date())
            
            self.end_date = QDateEdit()
            self.end_date.setCalendarPopup(True)
            self.end_date.setDate(QDateTime.currentDateTime().date())
            
            self.use_date_range = QCheckBox("Use Date Range")
            self.use_date_range.setChecked(False)
            
            time_layout.addRow("Start Date:", self.start_date)
            time_layout.addRow("End Date:", self.end_date)
            time_layout.addRow("", self.use_date_range)
            
            time_group.setLayout(time_layout)
            controls_layout.addWidget(time_group)
            
            # Analysis options
            options_group = QGroupBox("Analysis Options")
            options_layout = QFormLayout()
            
            self.bin_size_selector = QSpinBox()
            self.bin_size_selector.setMinimum(1)
            self.bin_size_selector.setMaximum(60)
            self.bin_size_selector.setValue(5)
            self.bin_size_selector.setSuffix(" minutes")
            
            self.days_selector = QSpinBox()
            self.days_selector.setMinimum(1)
            self.days_selector.setMaximum(90)
            self.days_selector.setValue(7)
            self.days_selector.setSuffix(" days")
            
            options_layout.addRow("Time Bin Size:", self.bin_size_selector)
            options_layout.addRow("Analysis Period:", self.days_selector)
            
            options_group.setLayout(options_layout)
            controls_layout.addWidget(options_group)
            
            # Action buttons
            actions_group = QGroupBox("Actions")
            actions_layout = QVBoxLayout()
            
            self.update_button = QPushButton("Update Charts")
            self.update_button.clicked.connect(self._update_charts)
            
            self.export_button = QPushButton("Export to CSV")
            self.export_button.clicked.connect(self._export_data)
            
            self.test_sensor_button = QPushButton("Test IR Sensor")
            self.test_sensor_button.clicked.connect(self._test_sensor)
            self.test_sensor_button.setEnabled(self.ir_sensor_manager is not None)
            
            actions_layout.addWidget(self.update_button)
            actions_layout.addWidget(self.export_button)
            actions_layout.addWidget(self.test_sensor_button)
            
            actions_group.setLayout(actions_layout)
            controls_layout.addWidget(actions_group)
            
            # Add stretch to push controls to the top
            controls_layout.addStretch()
            
            # Right panel - visualizations
            viz_widget = QWidget()
            viz_layout = QVBoxLayout(viz_widget)
            
            # Tab widget for different visualizations
            self.viz_tabs = QTabWidget()
            
            # Circadian pattern tab
            self.circadian_tab = QWidget()
            circadian_layout = QVBoxLayout(self.circadian_tab)
            
            self.circadian_chart = CircadianChart()
            circadian_layout.addWidget(self.circadian_chart)
            
            # Daily totals tab
            self.daily_tab = QWidget()
            daily_layout = QVBoxLayout(self.daily_tab)
            
            self.daily_chart = DailyTotalsChart()
            daily_layout.addWidget(self.daily_chart)
            
            # Data table tab
            self.table_tab = QWidget()
            table_layout = QVBoxLayout(self.table_tab)
            
            self.data_table = QTableWidget()
            table_layout.addWidget(self.data_table)
            
            # Add tabs to tab widget
            self.viz_tabs.addTab(self.circadian_tab, "Circadian Pattern")
            self.viz_tabs.addTab(self.daily_tab, "Daily Totals")
            self.viz_tabs.addTab(self.table_tab, "Data Table")
            
            viz_layout.addWidget(self.viz_tabs)
            
            # Add panels to splitter
            splitter.addWidget(controls_widget)
            splitter.addWidget(viz_widget)
            
            # Set initial sizes - controls get 1/4 of the space
            splitter.setSizes([25, 75])
        
        def _load_animals(self):
            """Load animals from the database."""
            try:
                # Clear existing items
                self.animal_selector.clear()
                
                # Get animals from database
                animals = self.database_handler.get_all_animals()
                
                # Add to combo box
                for animal in animals:
                    # Assuming animal is a tuple or has lab_animal_id and name attributes
                    try:
                        animal_id = getattr(animal, 'lab_animal_id', animal[0] if isinstance(animal, tuple) else None)
                        name = getattr(animal, 'name', animal[1] if isinstance(animal, tuple) else "Unknown")
                        
                        if animal_id:
                            self.animal_selector.addItem(f"{animal_id} - {name}", animal_id)
                    except Exception as e:
                        logger.error(f"Error processing animal: {e}")
                
                # Enable update button if animals are available
                self.update_button.setEnabled(self.animal_selector.count() > 0)
                
            except Exception as e:
                logger.error(f"Error loading animals: {e}")
        
        def _on_animal_selected(self, index):
            """
            Handle animal selection.
            
            Args:
                index (int): Index of the selected animal.
            """
            if index >= 0:
                self.selected_animal_id = self.animal_selector.itemData(index)
                self._update_charts()
        
        def _update_charts(self):
            """Update all charts with current settings."""
            if not self.selected_animal_id:
                return
                
            # Get settings
            bin_size = self.bin_size_selector.value()
            days = self.days_selector.value()
            
            # Update circadian chart
            circadian_data = self.data_model.get_circadian_pattern(
                self.selected_animal_id,
                days=days,
                bin_minutes=bin_size
            )
            self.circadian_chart.plot_circadian_data(
                circadian_data,
                title=f"Circadian Pattern for Animal {self.selected_animal_id}"
            )
            
            # Update daily totals chart
            daily_data = self.data_model.get_daily_totals(
                self.selected_animal_id,
                days=days
            )
            self.daily_chart.plot_daily_data(
                daily_data,
                title=f"Daily Totals for Animal {self.selected_animal_id}"
            )
            
            # Update data table
            self._update_data_table()
        
        def _update_data_table(self):
            """Update the data table with current data."""
            if not self.selected_animal_id:
                return
                
            try:
                # Get date range if enabled
                start_date = None
                end_date = None
                if self.use_date_range.isChecked():
                    start_date = self.start_date.date().toString(Qt.ISODate)
                    end_date = self.end_date.date().toString(Qt.ISODate)
                
                # Get drinking data
                data = self.data_model.get_drinking_data_for_animal(
                    self.selected_animal_id,
                    start_date,
                    end_date
                )
                
                # Set up table
                self.data_table.clear()
                self.data_table.setRowCount(len(data))
                self.data_table.setColumnCount(5)
                self.data_table.setHorizontalHeaderLabels([
                    "Session ID", "Start Time", "End Time", 
                    "Duration (ms)", "Volume (ml)"
                ])
                
                # Fill table
                for row, session in enumerate(data):
                    for col, value in enumerate(session):
                        item = QTableWidgetItem(str(value))
                        self.data_table.setItem(row, col, item)
                
                # Resize columns to content
                self.data_table.resizeColumnsToContents()
                
            except Exception as e:
                logger.error(f"Error updating data table: {e}")
        
        def _export_data(self):
            """Export data to CSV file."""
            if not self.selected_animal_id:
                return
                
            try:
                # Get file path from dialog
                file_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "Export Data",
                    f"animal_{self.selected_animal_id}_drinking_data.csv",
                    "CSV Files (*.csv)"
                )
                
                if not file_path:
                    return
                
                # Get date range if enabled
                start_date = None
                end_date = None
                if self.use_date_range.isChecked():
                    start_date = self.start_date.date().toString(Qt.ISODate)
                    end_date = self.end_date.date().toString(Qt.ISODate)
                
                # Get drinking data
                data = self.data_model.get_drinking_data_for_animal(
                    self.selected_animal_id,
                    start_date,
                    end_date
                )
                
                # Write to CSV
                with open(file_path, 'w') as f:
                    # Write header
                    f.write("session_id,start_time,end_time,duration_ms,volume_ml\n")
                    
                    # Write data rows
                    for session in data:
                        f.write(','.join(str(value) for value in session) + '\n')
                
                logger.info(f"Exported data to {file_path}")
                
            except Exception as e:
                logger.error(f"Error exporting data: {e}")
        
        def _test_sensor(self):
            """Test IR sensor for the current animal."""
            if not self.selected_animal_id or not self.ir_sensor_manager:
                return
                
            try:
                # Find the relay unit for this animal
                relay_unit = None
                for unit_id, animal_id in self.ir_sensor_manager.animal_relay_mapping.items():
                    if animal_id == self.selected_animal_id:
                        relay_unit = unit_id
                        break
                
                if relay_unit:
                    # Trigger the sensor
                    success = self.ir_sensor_manager.test_sensor(relay_unit)
                    logger.info(f"Sensor test for animal {self.selected_animal_id} on relay unit {relay_unit}: {'Success' if success else 'Failed'}")
                else:
                    logger.warning(f"No relay unit found for animal {self.selected_animal_id}")
                    
            except Exception as e:
                logger.error(f"Error testing sensor: {e}")
    
except ImportError as e:
    # Create a placeholder if PyQt is not available
    logger.error(f"PyQt5 not available - UI components disabled: {e}")
    
    class CircadianChart:
        def __init__(self, *args, **kwargs):
            pass
    
    class DailyTotalsChart:
        def __init__(self, *args, **kwargs):
            pass
    
    class DataAnalysisTab:
        def __init__(self, *args, **kwargs):
            pass 