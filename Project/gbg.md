System Messages
Loaded 2 animals for all trainers (guest mode)
Displaying all animals (guest mode)
Loaded 2 animals for all trainers (guest mode)
Error toggling mode: 'NoneType' object does not support item assignment
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
Relay data for unit 1: {'animals': [<models.animal.Animal object at 0x7f8f723810>], 'desired_water_output': {'1': 0.0}, 'delivery_mode': 'instant', 'delivery_schedule': [{'datetime': datetime.datetime(2025, 1, 18, 10, 59, 35, 329000), 'volume': 1.0}]}
Relay data for unit 2: {'animals': [<models.animal.Animal object at 0x7f8f723890>], 'desired_water_output': {'2': 0.0}, 'delivery_mode': 'instant', 'delivery_schedule': [{'datetime': datetime.datetime(2025, 1, 18, 11, 0, 36, 33000), 'volume': 2.0}]}
Relay data for unit 3: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 4: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 5: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 6: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 7: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 8: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
save_current_schedule: adding instant deliveries for unit 1
save_current_schedule: adding instant delivery for animal 1 at 2025-01-18 10:59:35.329000 with volume 1.0
save_current_schedule: adding instant deliveries for unit 2
save_current_schedule: adding instant delivery for animal 2 at 2025-01-18 11:00:36.033000 with volume 2.0
Schedule object: instant, t2, 3.0, 2025-01-18T10:59:35.329000, 2025-01-18T11:00:36.033000, 1, False, [], {}, [{'animal_id': 1, 'datetime': datetime.datetime(2025, 1, 18, 10, 59, 35, 329000), 'volume': 1.0, 'relay_unit_id': 1}, {'animal_id': 2, 'datetime': datetime.datetime(2025, 1, 18, 11, 0, 36, 33000), 'volume': 2.0, 'relay_unit_id': 2}]
Error updating table: too many values to unpack (expected 6)
Traceback (most recent call last):

  File "/home/conelab-rrr2/Documents/GitHub/rodRefReg/Project/ui/schedule_drop_area.py", line 155, in update_table
    animal_id, lab_id, name, datetime_str, volume, relay_unit_id = delivery
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

ValueError: too many values to unpack (expected 6)
