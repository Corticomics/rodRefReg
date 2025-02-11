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
save_current_schedule: adding instant deliveries for unit 1
save_current_schedule: adding instant delivery for animal 1 at 2025-02-11 15:28:41.528000 with volume 3.0
save_current_schedule: adding instant schedule with details:<models.Schedule.Schedule object at 0x7f78f7b810>

DEBUG - RunStopSection run_program:
self.system_controller type: <class 'controllers.system_controller.SystemController'>

DEBUG INFO:
Schedule: {'schedule_id': 15, 'name': 'rtrr', 'water_volume': 3.0, 'start_time': '2025-02-11T15:28:41.528000', 'end_time': '2025-02-11T15:28:41.528000', 'created_by': 1, 'is_super_user': 0, 'delivery_mode': 'instant', 'cycles_per_day': 1, 'animals': [1], 'desired_water_outputs': {}, 'window_data': {}, 'instant_deliveries': [{'animal_id': 1, 'datetime': datetime.datetime(2025, 2, 11, 15, 28, 41, 528000), 'volume': 3.0, 'relay_unit_id': 1}], 'relay_unit_assignments': {'1': 1}, 'status': 'pending', 'delivered_volumes': {}, 'last_delivery': {}}
Mode: Instant

Schedule Debug Info:
Desired water outputs: {}
Relay assignments: {'1': 1}

DEBUG - run_program:
system_controller type: <class 'controllers.system_controller.SystemController'>
Running program with schedule: rtrr, mode: Instant

Worker Settings Debug:
Mode: Instant
Desired outputs: None
Relay assignments: None


DEBUG - RelayWorker Initialization:
system_controller type: <class 'controllers.system_controller.SystemController'>
settings type: <class 'dict'>
self.system_controller type after assignment: <class 'controllers.system_controller.SystemController'>
Program Started
Starting instant cycle
Processing 1 deliveries
Scheduling delivery in 109.42 seconds
Scheduled 1 deliveries
[DEBUG] Starting stop sequence
RelayWorker stopped
[DEBUG] Starting cleanup process
[DEBUG] All relays deactivated
[ERROR] Unexpected error during cleanup: wrapped C/C++ object of type QTimer has been deleted
[DEBUG] Worker stopped
[DEBUG] All relays deactivated
[DEBUG] Stop sequence completed successfully

DEBUG - RunStopSection run_program:
self.system_controller type: <class 'controllers.system_controller.SystemController'>

DEBUG INFO:
Schedule: {'schedule_id': 15, 'name': 'rtrr', 'water_volume': 3.0, 'start_time': '2025-02-11T15:28:41.528000', 'end_time': '2025-02-11T15:28:41.528000', 'created_by': 1, 'is_super_user': 0, 'delivery_mode': 'instant', 'cycles_per_day': 1, 'animals': [1], 'desired_water_outputs': {}, 'window_data': {}, 'instant_deliveries': [{'animal_id': 1, 'datetime': datetime.datetime(2025, 2, 11, 15, 28, 41, 528000), 'volume': 3.0, 'relay_unit_id': 1}], 'relay_unit_assignments': {'1': 1}, 'status': 'pending', 'delivered_volumes': {}, 'last_delivery': {}}
Mode: Instant

Schedule Debug Info:
Desired water outputs: {}
Relay assignments: {'1': 1}

DEBUG - run_program:
system_controller type: <class 'controllers.system_controller.SystemController'>
Running program with schedule: rtrr, mode: Instant

Worker Settings Debug:
Mode: Instant
Desired outputs: None
Relay assignments: None


DEBUG - RelayWorker Initialization:
system_controller type: <class 'controllers.system_controller.SystemController'>
settings type: <class 'dict'>
self.system_controller type after assignment: <class 'controllers.system_controller.SystemController'>
Program Started
Starting instant cycle
Processing 1 deliveries
Scheduling delivery in 105.01 seconds
Scheduled 1 deliveries
Triggering relay unit 1 for 3.0ml (60 triggers)
Executing trigger 1/60 for relay unit 1
Executing trigger 2/60 for relay unit 1
Executing trigger 3/60 for relay unit 1
Executing trigger 4/60 for relay unit 1
Executing trigger 5/60 for relay unit 1
Executing trigger 6/60 for relay unit 1
Executing trigger 7/60 for relay unit 1
Executing trigger 8/60 for relay unit 1
Executing trigger 9/60 for relay unit 1
Executing trigger 10/60 for relay unit 1
Executing trigger 11/60 for relay unit 1
Executing trigger 12/60 for relay unit 1
Executing trigger 13/60 for relay unit 1
Executing trigger 14/60 for relay unit 1
Executing trigger 15/60 for relay unit 1
Executing trigger 16/60 for relay unit 1
Executing trigger 17/60 for relay unit 1
Executing trigger 18/60 for relay unit 1
Executing trigger 19/60 for relay unit 1
Executing trigger 20/60 for relay unit 1
Executing trigger 21/60 for relay unit 1
Executing trigger 22/60 for relay unit 1
Executing trigger 23/60 for relay unit 1
Executing trigger 24/60 for relay unit 1
Executing trigger 25/60 for relay unit 1
Executing trigger 26/60 for relay unit 1
Executing trigger 27/60 for relay unit 1
Executing trigger 28/60 for relay unit 1
Executing trigger 29/60 for relay unit 1
Executing trigger 30/60 for relay unit 1
Executing trigger 31/60 for relay unit 1
Executing trigger 32/60 for relay unit 1
Executing trigger 33/60 for relay unit 1
Executing trigger 34/60 for relay unit 1
Executing trigger 35/60 for relay unit 1
Executing trigger 36/60 for relay unit 1
Executing trigger 37/60 for relay unit 1
Executing trigger 38/60 for relay unit 1
Executing trigger 39/60 for relay unit 1
Executing trigger 40/60 for relay unit 1
Executing trigger 41/60 for relay unit 1
Executing trigger 42/60 for relay unit 1
Executing trigger 43/60 for relay unit 1
Executing trigger 44/60 for relay unit 1
Executing trigger 45/60 for relay unit 1
Executing trigger 46/60 for relay unit 1
Executing trigger 47/60 for relay unit 1
Executing trigger 48/60 for relay unit 1
Executing trigger 49/60 for relay unit 1
Executing trigger 50/60 for relay unit 1
Executing trigger 51/60 for relay unit 1
Executing trigger 52/60 for relay unit 1
Executing trigger 53/60 for relay unit 1
Executing trigger 54/60 for relay unit 1
Executing trigger 55/60 for relay unit 1
Executing trigger 56/60 for relay unit 1
Executing trigger 57/60 for relay unit 1
Executing trigger 58/60 for relay unit 1
Executing trigger 59/60 for relay unit 1
Executing trigger 60/60 for relay unit 1
Successfully triggered relay unit 1 60 times
2025-02-11 15:29:41.893412 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-02-11T15:29:41.893573', 'relay_info': 'Successfully triggered relay unit 1 60 times'}
[DEBUG] Starting cleanup process
[DEBUG] All relays deactivated
[ERROR] Unexpected error during cleanup: wrapped C/C++ object of type QTimer has been deleted