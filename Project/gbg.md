System Messages
Loaded 2 animals for all trainers (guest mode)
Displaying all animals (guest mode)
Loaded 2 animals for all trainers (guest mode)
Initiating authentication for username: adm
Authentication successful.
Retrieved 2 animals from the database for trainer_id 1
Loaded 2 animals for trainer 1
Login successful: {'username': 'adm', 'trainer_id': 1, 'role': 'normal'}
Logged in as: adm
Displaying animals for trainer ID 1
About to load animals for trainer_id: 1 (type: <class 'int'>)
Retrieved 2 animals from the database for trainer_id 1
Loaded 2 animals for trainer ID 1
Adding staggered schedule: ers
Animals: [1, 2]
Relay assignments: {'2': 1, '1': 2}
Water outputs: {'2': 1.0, '1': 2.0}
save_current_schedule: added staggered schedule with details:<models.Schedule.Schedule object at 0x7fb5173d90>

DEBUG INFO:
Schedule: {'schedule_id': 4, 'name': 'ers', 'water_volume': 3.0, 'start_time': '2025-02-02T12:25:42.517000', 'end_time': '2025-02-02T13:23:43.063000', 'created_by': 1, 'is_super_user': 0, 'delivery_mode': 'staggered', 'cycles_per_day': 1, 'animals': [1, 2], 'desired_water_outputs': {'1': 2.0, '2': 1.0}, 'window_data': {}, 'instant_deliveries': [], 'relay_unit_assignments': {'1': 2, '2': 1}, 'status': 'pending', 'delivered_volumes': {}, 'last_delivery': {}}
Mode: Staggered

Schedule Debug Info:
Desired water outputs: {'1': 2.0, '2': 1.0}
Relay assignments: {'1': 2, '2': 1}

Settings Debug Info:
Settings desired water outputs: {'1': 2.0, '2': 1.0}
Settings relay assignments: {'1': 2, '2': 1}
Starting schedule execution with mode: Staggered, window_start: 1738524342.517, window_end: 1738527823.063
Animals: [1, 2]
Relay assignments: {'1': 2, '2': 1}
Water outputs: {'1': 2.0, '2': 1.0}
Running program with schedule: ers, mode: Staggered

Worker Settings Debug:
Mode: Staggered
Desired outputs: {'1': 2.0, '2': 1.0}
Relay assignments: {'1': 2, '2': 1}

Program Started
Starting staggered cycle

Staggered Cycle Debug Info:
Current time: 2025-02-02 12:23:54.532172
Initializing animal windows
Created window for animal 1: {'start': datetime.datetime(2025, 2, 2, 12, 25, 42, 517000), 'end': datetime.datetime(2025, 2, 2, 13, 23, 43, 63000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2}
Volume per cycle: 0.2ml
Created window for animal 2: {'start': datetime.datetime(2025, 2, 2, 12, 25, 42, 517000), 'end': datetime.datetime(2025, 2, 2, 13, 23, 43, 63000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 1.0, 'volume_per_cycle': 0.1}
Volume per cycle: 0.1ml
Checking active animals at 2025-02-02 12:23:54.532172
Window start: 2025-02-02 12:25:42.517000, Window end: 2025-02-02 13:23:43.063000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 2, 2, 12, 25, 42, 517000), 'end': datetime.datetime(2025, 2, 2, 13, 23, 43, 63000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 2, 2, 12, 25, 42, 517000), 'end': datetime.datetime(2025, 2, 2, 13, 23, 43, 63000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 1.0, 'volume_per_cycle': 0.1})])
Current time (2025-02-02 12:23:54.532172) is before window start (2025-02-02 12:25:42.517000)
RelayWorker stopped
[DEBUG] Starting cleanup process
[DEBUG] All relays deactivated
[ERROR] An unexpected error occurred during cleanup: wrapped C/C++ object of type QTimer has been deleted
Program Stopped
[DEBUG] Starting cleanup process
[DEBUG] All relays deactivated
[ERROR] An unexpected error occurred during cleanup: wrapped C/C++ object of type QTimer has been deleted