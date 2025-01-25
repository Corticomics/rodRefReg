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
Adding staggered schedule: teste zarag
Animals: [1, 2]
Relay assignments: {'1': 1, '2': 2}
Water outputs: {'1': 1.0, '2': 2.0}

DEBUG INFO:
Schedule: {'schedule_id': 16, 'name': 'teste zarag', 'water_volume': 6.0, 'start_time': '2025-01-25T16:36:19.002000', 'end_time': '2025-01-25T16:41:19.627000', 'created_by': 1, 'is_super_user': 0, 'delivery_mode': 'staggered', 'cycles_per_day': 1, 'animals': [1, 2], 'desired_water_outputs': {'1': 1.0, '2': 2.0}, 'instant_deliveries': [], 'relay_unit_assignments': {'1': 1, '2': 2}, 'status': 'pending', 'delivered_volumes': {}, 'last_delivery': {}, 'window_data': {}}
Mode: Staggered

Schedule Debug Info:
Desired water outputs: {'1': 1.0, '2': 2.0}
Relay assignments: {'1': 1, '2': 2}

Settings Debug Info:
Settings desired water outputs: {'1': 1.0, '2': 2.0}
Settings relay assignments: {'1': 1, '2': 2}
Starting schedule execution with mode: Staggered, window_start: 1737848179.002, window_end: 1737848479.627
Animals: [1, 2]
Relay assignments: {'1': 1, '2': 2}
Water outputs: {'1': 1.0, '2': 2.0}
Running program with schedule: teste zarag, mode: Staggered

Worker Settings Debug:
Mode: Staggered
Desired outputs: {'1': 1.0, '2': 2.0}
Relay assignments: {'1': 1, '2': 2}

Program Started
Starting staggered cycle

Staggered Cycle Debug Info:
Current time: 2025-01-25 16:34:37.947046
Settings: {'mode': 'Staggered', 'window_start': 1737848179.002, 'window_end': 1737848479.627, 'min_trigger_interval_ms': 500, 'database_handler': <models.database_handler.DatabaseHandler object at 0x7fb2507750>, 'pump_controller': None, 'cycle_interval': 3600, 'stagger_interval': 0.5, 'water_volume': 6.0, 'relay_unit_assignments': {'1': 1, '2': 2}, 'desired_water_outputs': {'1': 1.0, '2': 2.0}}
Initializing animal windows
Relay assignments: {'1': 1, '2': 2}
Desired outputs: {'1': 1.0, '2': 2.0}
Created window for animal 1: {'start': datetime.datetime(2025, 1, 25, 16, 36, 19, 2000), 'end': datetime.datetime(2025, 1, 25, 16, 41, 19, 627000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 1.0}
Created window for animal 2: {'start': datetime.datetime(2025, 1, 25, 16, 36, 19, 2000), 'end': datetime.datetime(2025, 1, 25, 16, 41, 19, 627000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0}
Checking active animals at 2025-01-25 16:34:37.947046
Window start: 2025-01-25 16:36:19.002000, Window end: 2025-01-25 16:41:19.627000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 25, 16, 36, 19, 2000), 'end': datetime.datetime(2025, 1, 25, 16, 41, 19, 627000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 1.0}), ('2', {'start': datetime.datetime(2025, 1, 25, 16, 36, 19, 2000), 'end': datetime.datetime(2025, 1, 25, 16, 41, 19, 627000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0})])
Active animals: dict_items([])
No active animals in current time window
WARNING:root:No active animals found