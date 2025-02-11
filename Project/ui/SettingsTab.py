from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QGroupBox, 
    QFormLayout, QLineEdit, QLabel, QPushButton, 
    QMessageBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QFileDialog, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
import json
import os
import base64
from cryptography.fernet import Fernet
from datetime import datetime
import pandas as pd
from models.animal import Animal

class SettingsTab(QWidget):
    settings_updated = pyqtSignal(dict)
    
    def __init__(self, system_controller, suggest_callback=None, 
                 push_callback=None, save_slack_callback=None, 
                 run_stop_section=None, login_system=None,
                 print_to_terminal=None, database_handler=None):
        super().__init__()
        
        if not system_controller:
            raise ValueError("system_controller is required")
        
        self.system_controller = system_controller
        self.settings = system_controller.settings
        self.suggest_callback = suggest_callback
        self.push_callback = push_callback
        self.save_slack_callback = save_slack_callback
        self.run_stop_section = run_stop_section
        self.login_system = login_system
        self.print_to_terminal = print_to_terminal or (lambda x: None)
        
        # Get database handler from system controller if not provided
        self.database_handler = database_handler or system_controller.database_handler
        
        if not self.database_handler:
            raise ValueError("database_handler must be provided either directly or through system_controller")
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget for settings
        self.tab_widget = QTabWidget()
        
        # Create and add settings sub-tabs
        self.pump_settings = self._create_pump_settings()
        self.system_settings = self._create_system_settings()
        self.notifications = self._create_notifications()
        self.backup_restore = self._create_backup_restore()
        self.data_import_export = self._create_data_import_export()
        
        # Add sub-tabs to settings - CHECK USABILITY OF SYSTEM AND BACKUP/RESTORE
        self.tab_widget.addTab(self.pump_settings, "Pump Settings")
        #self.tab_widget.addTab(self.system_settings, "System")
        self.tab_widget.addTab(self.notifications, "Notifications")
        #self.tab_widget.addTab(self.backup_restore, "Backup/Restore")
        self.tab_widget.addTab(self.data_import_export, "Data Import/Export")
        
        layout.addWidget(self.tab_widget)
        
        # Add save button at bottom of settings
        save_button = QPushButton("Save All Settings")
        save_button.clicked.connect(self._save_all_settings)
        layout.addWidget(save_button)

    def _create_pump_settings(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Pump Configuration Group
        pump_group = QGroupBox("Pump Configuration")
        pump_layout = QFormLayout()
        
        self.pump_volume = QDoubleSpinBox()
        self.pump_volume.setRange(0, 1000)
        self.pump_volume.setValue(self.settings.get('pump_volume_ul', 50))
        self.pump_volume.setSuffix(" µL")
        pump_layout.addRow("Pump Output Volume:", self.pump_volume)
        
        self.calibration_factor = QDoubleSpinBox()
        self.calibration_factor.setRange(0.1, 10.0)
        self.calibration_factor.setValue(self.settings.get('calibration_factor', 1.0))
        self.calibration_factor.setSingleStep(0.1)
        pump_layout.addRow("Calibration Factor:", self.calibration_factor)
        
        pump_group.setLayout(pump_layout)
        layout.addWidget(pump_group)
        
        widget.setLayout(layout)
        return widget

    def _create_system_settings(self):
        """Create system settings tab with proper type handling"""
        system_tab = QWidget()
        layout = QFormLayout()

        # Log Level Spinner with proper type handling
        self.log_level = QSpinBox()
        self.log_level.setRange(0, 4)  # 0=DEBUG to 4=CRITICAL
        self.log_level.setValue(int(self.settings.get('log_level', 2)))
        self.log_level.valueChanged.connect(self._log_level_changed)
        
        # Add tooltip to explain log levels
        self.log_level.setToolTip(
            "0=DEBUG, 1=INFO, 2=WARNING, 3=ERROR, 4=CRITICAL"
        )
        
        layout.addRow("Log Level:", self.log_level)
        
        # Rest of the system settings...
        system_tab.setLayout(layout)
        return system_tab

    def _log_level_changed(self, value):
        """Handle log level changes"""
        self.settings['log_level'] = value
        if self.push_callback:
            self.push_callback()

    def _create_notifications(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        slack_group = QGroupBox("Slack Integration")
        slack_layout = QFormLayout()
        
        self.slack_token = QLineEdit()
        self.slack_token.setText(self._decrypt_sensitive_data(
            self.settings.get('slack_token', '')))
        self.slack_token.setEchoMode(QLineEdit.Password)
        slack_layout.addRow("Slack Bot Token:", self.slack_token)
        
        self.slack_channel = QLineEdit()
        self.slack_channel.setText(self.settings.get('channel_id', ''))
        slack_layout.addRow("Channel ID:", self.slack_channel)
        
        slack_group.setLayout(slack_layout)
        layout.addWidget(slack_group)
        
        widget.setLayout(layout)
        return widget

    def _create_backup_restore(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        backup_group = QGroupBox("Backup and Restore")
        backup_layout = QVBoxLayout()
        
        backup_button = QPushButton("Create Backup")
        backup_button.clicked.connect(self.create_backup)
        backup_layout.addWidget(backup_button)
        
        restore_button = QPushButton("Restore from Backup")
        restore_button.clicked.connect(self.restore_from_backup)
        backup_layout.addWidget(restore_button)
        
        backup_group.setLayout(backup_layout)
        layout.addWidget(backup_group)
        
        widget.setLayout(layout)
        return widget

    def _create_data_import_export(self):
        widget = QWidget()
        layout = QGridLayout()
        
        export_btn = QPushButton("Export Animals to CSV")
        export_btn.clicked.connect(self.export_animals)
        import_btn = QPushButton("Import Animals from CSV")
        import_btn.clicked.connect(self.import_animals)
        
        layout.addWidget(export_btn, 0, 0)
        layout.addWidget(import_btn, 0, 1)
        
        widget.setLayout(layout)
        return widget

    def _get_or_create_key(self):
        key_file = "settings_key.key"
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return base64.urlsafe_b64decode(f.read())
        else:
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(base64.urlsafe_b64encode(key))
            return key

    def _encrypt_sensitive_data(self, data):
        if not data:
            return ""
        return self.fernet.encrypt(data.encode()).decode()

    def _decrypt_sensitive_data(self, data):
        if not data:
            return ""
        try:
            return self.fernet.decrypt(data.encode()).decode()
        except:
            return ""

    def create_backup(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Backup", 
                f"rrr_backup_{timestamp}.json",
                "JSON files (*.json)"
            )
            
            if filename:
                with open(filename, 'w') as f:
                    json.dump(self.settings, f, indent=4)
                QMessageBox.information(self, "Success", "Backup created successfully")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create backup: {str(e)}")

    def restore_from_backup(self):
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, "Load Backup",
                "",
                "JSON files (*.json)"
            )
            
            if filename:
                with open(filename, 'r') as f:
                    backup_settings = json.load(f)
                
                # Validate backup data
                required_keys = ['pump_volume_ul', 'calibration_factor']
                if not all(key in backup_settings for key in required_keys):
                    raise ValueError("Invalid backup file format")
                
                self.settings.update(backup_settings)
                self.load_settings()
                QMessageBox.information(self, "Success", "Settings restored successfully")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to restore backup: {str(e)}")

    def load_settings(self):
        """Reload all settings into UI elements"""
        self.pump_volume.setValue(self.settings.get('pump_volume_ul', 50))
        self.calibration_factor.setValue(self.settings.get('calibration_factor', 1.0))
        self.slack_token.setText(self._decrypt_sensitive_data(self.settings.get('slack_token', '')))
        self.slack_channel.setText(self.settings.get('channel_id', ''))
        self.log_level.setValue(self.settings.get('log_level', 2))

    def _save_all_settings(self):
        try:
            self.settings.update({
                'pump_volume_ul': self.pump_volume.value(),
                'calibration_factor': self.calibration_factor.value(),
                'slack_token': self._encrypt_sensitive_data(self.slack_token.text()),
                'channel_id': self.slack_channel.text(),
                'log_level': self.log_level.value()
            })
            
            self.push_callback()
            self.settings_updated.emit(self.settings)
            QMessageBox.information(self, "Success", "Settings saved successfully")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")

    def export_animals(self):
        """Export animals to CSV with proper Excel compatibility."""
        if not self.database_handler:
            QMessageBox.critical(self, "Export Error", "Database handler not initialized")
            return
        
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Animals", "", "CSV Files (*.csv);;Excel Files (*.xlsx)"
            )
            if not file_path:
                return
            
            animals = self.database_handler.get_all_animals()
            if not animals:
                QMessageBox.information(self, "Export Info", "No animals found to export")
                return
            
            data = []
            for animal in animals:
                # Format dates in Excel-friendly format
                last_weighted = (datetime.fromisoformat(animal.last_weighted).strftime('%Y-%m-%d %H:%M:%S') 
                               if animal.last_weighted else '')
                last_watering = (datetime.fromisoformat(animal.last_watering).strftime('%Y-%m-%d %H:%M:%S') 
                               if animal.last_watering else '')
                
                data.append({
                    'Lab Animal ID': animal.lab_animal_id,
                    'Name': animal.name,
                    'Gender': animal.gender or '',
                    'Initial Weight (g)': f"{animal.initial_weight:.1f}" if animal.initial_weight else '',
                    'Last Weight (g)': f"{animal.last_weight:.1f}" if animal.last_weight else '',
                    'Last Weighted': last_weighted,
                    'Last Watering': last_watering
                })
            
            df = pd.DataFrame(data)
            
            # Export based on file extension
            if file_path.endswith('.xlsx'):
                # Export as Excel file
                df.to_excel(file_path, index=False, engine='openpyxl')
            else:
                # Export as CSV with Excel-friendly encoding and separator
                df.to_csv(file_path, index=False, encoding='utf-8-sig', sep=',')
            
            self.print_to_terminal(f"Successfully exported {len(animals)} animals to {file_path}")
            QMessageBox.information(self, "Success", f"Successfully exported {len(animals)} animals")
            
        except AttributeError as e:
            QMessageBox.critical(self, "Export Error", "Database connection error. Please check system configuration.")
            self.print_to_terminal(f"Database error during export: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error exporting animals: {str(e)}")
            self.print_to_terminal(f"Unexpected error during export: {str(e)}")
            
    #Check for data formatting w jackson
    def import_animals(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Import Animals", "", "CSV Files (*.csv)"
            )
            if file_path:
                df = pd.read_csv(file_path)
                current_trainer = self.login_system.get_current_trainer()
                trainer_id = current_trainer['trainer_id'] if current_trainer else None
                
                imported = 0
                errors = []
                
                for _, row in df.iterrows():
                    try:
                        # Map lab document format to our database format
                        gender = 'female' if row['# Females'] == 1 else 'male' if row['# Males'] == 1 else None
                        
                        # Convert birthdate to our datetime format
                        birthdate = datetime.strptime(str(row['Birthdate']), '%y%m%d')
                        
                        animal = Animal(
                            animal_id=None,
                            lab_animal_id=str(row['Ear tag ID#']) if pd.notna(row['Ear tag ID#']) else row['Cage Number #'],
                            name=row['Nickname'] if pd.notna(row['Nickname']) else '',
                            initial_weight=None,  # No weight in lab format
                            last_weight=None,
                            last_weighted=None,
                            last_watering=None,
                            gender=gender
                        )
                        
                        if self.database_handler.add_animal(animal, trainer_id):
                            imported += 1
                        
                    except Exception as e:
                        errors.append(f"Row {_+2}: {str(e)}")
                
                msg = f"Successfully imported {imported} animals."
                if errors:
                    msg += f"\n\nErrors ({len(errors)}):\n" + "\n".join(errors)
                
                QMessageBox.information(self, "Import Results", msg)
                self.print_to_terminal(f"Imported {imported} animals from {file_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Error importing animals: {e}") 