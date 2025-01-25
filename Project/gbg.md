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
Adding staggered schedule: testeeee
Animals: [1, 2]
Relay assignments: {'1': 1, '2': 2}
Water outputs: {'1': 2.0, '2': 1.0}

Schedule details from DB:
Animal IDs: [1, 2]
Relay assignments: {'1': 1, '2': 2}

DEBUG INFO:
Schedule: {'schedule_id': 14, 'name': 'testeeee', 'water_volume': 6.0, 'start_time': '2025-01-25T16:13:41.299000', 'end_time': '2025-01-25T16:18:42.003000', 'created_by': 1, 'is_super_user': 0, 'delivery_mode': 'staggered', 'cycles_per_day': 1, 'animals': [1, 2], 'desired_water_outputs': {'1': 2.0, '2': 1.0}, 'instant_deliveries': [], 'relay_unit_assignments': {'1': 1, '2': 2}, 'status': 'pending', 'delivered_volumes': {}, 'last_delivery': {}, 'window_data': {}}
Mode: Staggered
Starting schedule execution with mode: Staggered, window_start: 1737846821.299, window_end: 1737847122.003
Animals: [1, 2]
Relay assignments: {'1': 1, '2': 2}
Water outputs: {'1': 2.0, '2': 1.0}
Running program with schedule: testeeee, mode: Staggered
Program Started
Starting staggered cycle
Checking active animals at 2025-01-25 16:11:56.638897, window_start: 2025-01-25 16:13:41.299000, window_end: 2025-01-25 16:18:42.003000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 25, 16, 13, 41, 299000), 'end': datetime.datetime(2025, 1, 25, 16, 18, 42, 3000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 0}), ('2', {'start': datetime.datetime(2025, 1, 25, 16, 13, 41, 299000), 'end': datetime.datetime(2025, 1, 25, 16, 18, 42, 3000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 0})])
Active animals: dict_items([])
No active animals in current time window
WARNING:root:No active animals found
