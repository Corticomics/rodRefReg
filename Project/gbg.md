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
Schedule object: staggered, stg 2, 3.0, 2025-01-25T14:52:15.728000, 2025-01-25T14:57:16.336000, 1, False, [2, 1], {'2': 0.0, '1': 0.0}, []

DEBUG INFO:
Schedule: {'schedule_id': 3, 'name': 'stg 2', 'water_volume': 3.0, 'start_time': '2025-01-25T14:52:15.728000', 'end_time': '2025-01-25T14:57:16.336000', 'created_by': 1, 'is_super_user': 0, 'delivery_mode': 'staggered', 'cycles_per_day': 1, 'animals': [], 'desired_water_outputs': {}, 'instant_deliveries': [], 'relay_unit_assignments': {}, 'status': 'pending', 'delivered_volumes': {}, 'last_delivery': {}, 'window_data': {}}
Mode: Staggered
Starting schedule execution with mode: Staggered, window_start: 1737841935.728, window_end: 1737842236.336
Running program with schedule: stg 2, mode: Staggered
Program Started
Starting staggered cycle
No active animals in current time window
Window time completed
RelayWorker stopped
[DEBUG] Starting cleanup process
[DEBUG] All relays deactivated
[ERROR] An unexpected error occurred during cleanup: wrapped C/C++ object of type QTimer has been deleted