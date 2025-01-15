System Messages
Loaded 2 animals for all trainers (guest mode)
Displaying all animals (guest mode)
Loaded 2 animals for all trainers (guest mode)
Initiating authentication for username: admin
Authentication successful.
Retrieved 2 animals from the database for trainer_id 1
Loaded 2 animals for trainer 1
Error retrieving schedules for trainer_id 1: no such column: relay_unit_id
Traceback (most recent call last):

  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/models/database_handler.py", line 410, in get_schedules_by_trainer
    cursor.execute('SELECT schedule_id, name, relay_unit_id, water_volume, start_time, end_time, created_by, is_super_user FROM schedules WHERE created_by = ?', (trainer_id,))

sqlite3.OperationalError: no such column: relay_unit_id

Login successful: {'username': 'admin', 'trainer_id': 1, 'role': 'normal'}
Logged in as: admin
Displaying animals for trainer ID 1
About to load animals for trainer_id: 1 (type: <class 'int'>)
Retrieved 2 animals from the database for trainer_id 1
Loaded 2 animals for trainer ID 1
Relay data for unit 1: {'animals': [<models.animal.Animal object at 0x7f8ddc6510>], 'desired_water_output': {'1': 0.0}, 'delivery_mode': 'instant', 'delivery_schedule': [{'datetime': datetime.datetime(2025, 1, 15, 22, 33, 5, 639000), 'volume': 1.0}]}
Relay data for unit 2: {'animals': [<models.animal.Animal object at 0x7f8ddc6610>], 'desired_water_output': {'2': 0.0}, 'delivery_mode': 'instant', 'delivery_schedule': [{'datetime': datetime.datetime(2025, 1, 15, 22, 34, 6, 526000), 'volume': 2.0}]}
Relay data for unit 3: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 4: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 5: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 6: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 7: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 8: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
save_current_schedule: adding instant deliveries for unit 1
save_current_schedule: adding instant delivery for animal 1 at 2025-01-15 22:33:05.639000 with volume 1.0
save_current_schedule: adding instant deliveries for unit 2
save_current_schedule: adding instant delivery for animal 2 at 2025-01-15 22:34:06.526000 with volume 2.0
Schedule object: instant, t1, 3.0, 2025-01-15T22:33:05.639000, 2025-01-15T22:34:06.526000, 1, False, [], {}, [{'animal_id': 1, 'datetime': datetime.datetime(2025, 1, 15, 22, 33, 5, 639000), 'volume': 1.0, 'relay_unit_id': 1}, {'animal_id': 2, 'datetime': datetime.datetime(2025, 1, 15, 22, 34, 6, 526000), 'volume': 2.0, 'relay_unit_id': 2}]
Error retrieving schedules for trainer_id 1: no such column: relay_unit_id
Traceback (most recent call last):

  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/models/database_handler.py", line 410, in get_schedules_by_trainer
    cursor.execute('SELECT schedule_id, name, relay_unit_id, water_volume, start_time, end_time, created_by, is_super_user FROM schedules WHERE created_by = ?', (trainer_id,))

sqlite3.OperationalError: no such column: relay_unit_id