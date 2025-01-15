System Messages
Loaded 2 animals for all trainers (guest mode)
Displaying all animals (guest mode)
Loaded 2 animals for all trainers (guest mode)
Initiating authentication for username: admin
Authentication successful.
Retrieved 2 animals from the database for trainer_id 1
Loaded 2 animals for trainer 1
Login successful: {'username': 'admin', 'trainer_id': 1, 'role': 'normal'}
Logged in as: admin
Displaying animals for trainer ID 1
About to load animals for trainer_id: 1 (type: <class 'int'>)
Retrieved 2 animals from the database for trainer_id 1
Loaded 2 animals for trainer ID 1
Relay data for unit 1: {'animals': [<models.animal.Animal object at 0x7f909e5f10>], 'desired_water_output': {'1': 0.0}, 'delivery_mode': 'instant', 'delivery_schedule': [{'datetime': datetime.datetime(2025, 1, 15, 22, 7, 6, 207000), 'volume': 1.0}]}
Relay data for unit 2: {'animals': [<models.animal.Animal object at 0x7f909e5f90>], 'desired_water_output': {'2': 0.0}, 'delivery_mode': 'instant', 'delivery_schedule': [{'datetime': datetime.datetime(2025, 1, 15, 22, 8, 9, 811000), 'volume': 2.0}]}
Relay data for unit 3: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 4: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 5: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 6: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 7: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 8: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
save_current_schedule: adding instant deliveries for unit 1
save_current_schedule: adding instant delivery for animal 1 at 2025-01-15 22:07:06.207000 with volume 1.0
save_current_schedule: adding instant deliveries for unit 2
save_current_schedule: adding instant delivery for animal 2 at 2025-01-15 22:08:09.811000 with volume 2.0
Schedule object: instant, t7, 3.0, 2025-01-15T22:07:06.207000, 2025-01-15T22:08:09.811000, 1, False, [], {}, [{'animal_id': 1, 'datetime': datetime.datetime(2025, 1, 15, 22, 7, 6, 207000), 'volume': 1.0, 'relay_unit_id': 1}, {'animal_id': 2, 'datetime': datetime.datetime(2025, 1, 15, 22, 8, 9, 811000), 'volume': 2.0, 'relay_unit_id': 2}]
Database error when adding schedule: NOT NULL constraint failed: schedules.relay_unit_id
Traceback (most recent call last):

  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/models/database_handler.py", line 195, in add_schedule
    cursor.execute('''

sqlite3.IntegrityError: NOT NULL constraint failed: schedules.relay_unit_id