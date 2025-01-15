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
Relay data for unit 1: {'animals': [<models.animal.Animal object at 0x7fa6aa62d0>], 'desired_water_output': {'1': 0.0}, 'delivery_mode': 'instant', 'delivery_schedule': [{'datetime': datetime.datetime(2025, 1, 15, 21, 49, 1, 923000), 'volume': 2.0}]}
Relay data for unit 2: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 3: {'animals': [<models.animal.Animal object at 0x7fa6aa7e50>], 'desired_water_output': {'2': 0.0}, 'delivery_mode': 'instant', 'delivery_schedule': [{'datetime': datetime.datetime(2025, 1, 15, 21, 50, 0, 435000), 'volume': 4.0}]}
Relay data for unit 4: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 5: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 6: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 7: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 8: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
save_current_schedule: adding instant deliveries for unit 1
save_current_schedule: adding instant delivery for animal 1 at 2025-01-15 21:49:01.923000 with volume 2.0
save_current_schedule: adding instant deliveries for unit 3
save_current_schedule: adding instant delivery for animal 2 at 2025-01-15 21:50:00.435000 with volume 4.0
Schedule object: instant, t6, 6.0, 2025-01-15T21:49:01.923000, 2025-01-15T21:50:00.435000, 1, False, [], {}, [{'animal_id': 1, 'datetime': datetime.datetime(2025, 1, 15, 21, 49, 1, 923000), 'volume': 2.0}, {'animal_id': 2, 'datetime': datetime.datetime(2025, 1, 15, 21, 50, 0, 435000), 'volume': 4.0}]
Schedule 't6' added with ID: 6
Running program with schedule: t6, mode: Instant, window_start: 1736977741, window_end: 1736977800
Program Started
Starting instant cycle
Processing 2 deliveries
Processing delivery time: 2025-01-15 21:49:01.923000
Scheduling delivery in 100.43 seconds
Processing delivery time: 2025-01-15 21:50:00.435000
Scheduling delivery in 159.45 seconds
Scheduled 2 deliveries
Triggering relay unit 1 for 2.0ml (40 triggers)
Executing trigger 1/40 for relay unit 1
Executing trigger 2/40 for relay unit 1
Executing trigger 3/40 for relay unit 1
Executing trigger 4/40 for relay unit 1
Executing trigger 5/40 for relay unit 1
Executing trigger 6/40 for relay unit 1
Executing trigger 7/40 for relay unit 1
Executing trigger 8/40 for relay unit 1
Executing trigger 9/40 for relay unit 1
Executing trigger 10/40 for relay unit 1
Executing trigger 11/40 for relay unit 1
Executing trigger 12/40 for relay unit 1
Executing trigger 13/40 for relay unit 1
Executing trigger 14/40 for relay unit 1
Executing trigger 15/40 for relay unit 1
Executing trigger 16/40 for relay unit 1
Executing trigger 17/40 for relay unit 1
Executing trigger 18/40 for relay unit 1
Executing trigger 19/40 for relay unit 1
Executing trigger 20/40 for relay unit 1
Executing trigger 21/40 for relay unit 1
Executing trigger 22/40 for relay unit 1
Executing trigger 23/40 for relay unit 1
Executing trigger 24/40 for relay unit 1
Executing trigger 25/40 for relay unit 1
Executing trigger 26/40 for relay unit 1
Executing trigger 27/40 for relay unit 1
Executing trigger 28/40 for relay unit 1
Executing trigger 29/40 for relay unit 1
Executing trigger 30/40 for relay unit 1
Executing trigger 31/40 for relay unit 1
Executing trigger 32/40 for relay unit 1
Executing trigger 33/40 for relay unit 1
Executing trigger 34/40 for relay unit 1
Executing trigger 35/40 for relay unit 1
Executing trigger 36/40 for relay unit 1
Executing trigger 37/40 for relay unit 1
Executing trigger 38/40 for relay unit 1
Executing trigger 39/40 for relay unit 1
Executing trigger 40/40 for relay unit 1
Successfully triggered relay unit 1 40 times
2025-01-15 21:49:41.736668 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-15T21:49:41.736819', 'relay_info': 'Successfully triggered relay unit 1 40 times'}
Logged pump trigger: {'timestamp': '2025-01-15T21:49:41.738992', 'relay_info': 'Successfully triggered relay unit 1 40 times'}
Triggering relay unit 1 for 4.0ml (80 triggers)
Executing trigger 1/80 for relay unit 1
Executing trigger 2/80 for relay unit 1
Executing trigger 3/80 for relay unit 1
Executing trigger 4/80 for relay unit 1
Executing trigger 5/80 for relay unit 1
Executing trigger 6/80 for relay unit 1
Executing trigger 7/80 for relay unit 1
Executing trigger 8/80 for relay unit 1
Executing trigger 9/80 for relay unit 1
Executing trigger 10/80 for relay unit 1
Executing trigger 11/80 for relay unit 1
Executing trigger 12/80 for relay unit 1
Executing trigger 13/80 for relay unit 1
Executing trigger 14/80 for relay unit 1
Executing trigger 15/80 for relay unit 1
Executing trigger 16/80 for relay unit 1
Executing trigger 17/80 for relay unit 1
Executing trigger 18/80 for relay unit 1
Executing trigger 19/80 for relay unit 1
Executing trigger 20/80 for relay unit 1
Executing trigger 21/80 for relay unit 1
Executing trigger 22/80 for relay unit 1
Executing trigger 23/80 for relay unit 1
Executing trigger 24/80 for relay unit 1
Executing trigger 25/80 for relay unit 1
Executing trigger 26/80 for relay unit 1
Executing trigger 27/80 for relay unit 1
Executing trigger 28/80 for relay unit 1
Executing trigger 29/80 for relay unit 1
Executing trigger 30/80 for relay unit 1
Executing trigger 31/80 for relay unit 1
Executing trigger 32/80 for relay unit 1
Executing trigger 33/80 for relay unit 1
Executing trigger 34/80 for relay unit 1
Executing trigger 35/80 for relay unit 1
Executing trigger 36/80 for relay unit 1
Executing trigger 37/80 for relay unit 1
Executing trigger 38/80 for relay unit 1
Executing trigger 39/80 for relay unit 1
Executing trigger 40/80 for relay unit 1
Executing trigger 41/80 for relay unit 1
Executing trigger 42/80 for relay unit 1
Executing trigger 43/80 for relay unit 1
Executing trigger 44/80 for relay unit 1
Executing trigger 45/80 for relay unit 1
Executing trigger 46/80 for relay unit 1
Executing trigger 47/80 for relay unit 1
Executing trigger 48/80 for relay unit 1
Executing trigger 49/80 for relay unit 1
Executing trigger 50/80 for relay unit 1
Executing trigger 51/80 for relay unit 1
Executing trigger 52/80 for relay unit 1
Executing trigger 53/80 for relay unit 1
Executing trigger 54/80 for relay unit 1
Executing trigger 55/80 for relay unit 1
Executing trigger 56/80 for relay unit 1
Executing trigger 57/80 for relay unit 1
Executing trigger 58/80 for relay unit 1
Executing trigger 59/80 for relay unit 1
Executing trigger 60/80 for relay unit 1
Executing trigger 61/80 for relay unit 1
Executing trigger 62/80 for relay unit 1
Executing trigger 63/80 for relay unit 1
Executing trigger 64/80 for relay unit 1
Executing trigger 65/80 for relay unit 1
Executing trigger 66/80 for relay unit 1
Executing trigger 67/80 for relay unit 1
Executing trigger 68/80 for relay unit 1
Executing trigger 69/80 for relay unit 1
Executing trigger 70/80 for relay unit 1
Executing trigger 71/80 for relay unit 1
Executing trigger 72/80 for relay unit 1
Executing trigger 73/80 for relay unit 1
Executing trigger 74/80 for relay unit 1
Executing trigger 75/80 for relay unit 1
Executing trigger 76/80 for relay unit 1
Executing trigger 77/80 for relay unit 1
Executing trigger 78/80 for relay unit 1
Executing trigger 79/80 for relay unit 1
Executing trigger 80/80 for relay unit 1
Successfully triggered relay unit 1 80 times
2025-01-15 21:51:21.088165 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-15T21:51:21.088318', 'relay_info': 'Successfully triggered relay unit 1 80 times'}
Logged pump trigger: {'timestamp': '2025-01-15T21:51:21.090385', 'relay_info': 'Successfully triggered relay unit 1 80 times'}
[DEBUG] Starting cleanup process
[DEBUG] All relays deactivated
[DEBUG] Worker was already deleted or disconnected: wrapped C/C++ object of type RelayWorker has been deleted
[DEBUG] Cleanup completed. Program ready for the next job.