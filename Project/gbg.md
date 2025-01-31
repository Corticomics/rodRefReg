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
save_current_schedule: adding instant schedule with details:<models.Schedule.Schedule object at 0x7fb22bc110>
Database error when adding schedule: NOT NULL constraint failed: schedules.start_time
Traceback (most recent call last):

  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/models/database_handler.py", line 244, in add_schedule
    cursor.execute('''

sqlite3.IntegrityError: NOT NULL constraint failed: schedules.start_time

Error details: Traceback (most recent call last):
  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/ui/schedules_tab.py", line 316, in save_current_schedule
    raise Exception("Failed to save schedule to database")
Exception: Failed to save schedule to database