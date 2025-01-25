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
Adding staggered schedule: fr
Animals: [2, 1]
Relay assignments: {'2': 1, '1': 2}
Water outputs: {'2': 1.0, '1': 2.0}

Schedule details from DB:
Animal IDs: [1, 2]
Relay assignments: {'1': 2, '2': 1}

DEBUG INFO:
Schedule: {'schedule_id': 12, 'name': 'fr', 'water_volume': 6.0, 'start_time': '2025-01-25T16:02:07.269000', 'end_time': '2025-01-25T16:07:07.976000', 'created_by': 1, 'is_super_user': 0, 'delivery_mode': 'staggered', 'cycles_per_day': 1, 'animals': [1, 2], 'desired_water_outputs': {'1': 2.0, '2': 1.0}, 'instant_deliveries': [], 'relay_unit_assignments': {'1': 2, '2': 1}, 'status': 'pending', 'delivered_volumes': {}, 'last_delivery': {}, 'window_data': {}}
Mode: Staggered
Starting schedule execution with mode: Staggered, window_start: 1737846127.269, window_end: 1737846427.976
Animals: [1, 2]
Relay assignments: {'1': 2, '2': 1}
Water outputs: {'1': 2.0, '2': 1.0}
Running program with schedule: fr, mode: Staggered
Program Started
Starting staggered cycle
No active animals in current time window
WARNING:root:No active animals found
