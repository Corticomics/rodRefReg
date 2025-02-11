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
save_current_schedule: adding instant delivery for animal 1 at 2025-02-11 15:02:54.229000 with volume 1.0
save_current_schedule: adding instant schedule with details:<models.Schedule.Schedule object at 0x7f86b5ef90>

DEBUG - RunStopSection run_program:
self.system_controller type: <class 'controllers.system_controller.SystemController'>

DEBUG INFO:
Schedule: {'schedule_id': 11, 'name': '1', 'water_volume': 1.0, 'start_time': '2025-02-11T15:02:54.229000', 'end_time': '2025-02-11T15:02:54.229000', 'created_by': 1, 'is_super_user': 0, 'delivery_mode': 'instant', 'cycles_per_day': 1, 'animals': [1], 'desired_water_outputs': {}, 'window_data': {}, 'instant_deliveries': [{'animal_id': 1, 'datetime': datetime.datetime(2025, 2, 11, 15, 2, 54, 229000), 'volume': 1.0, 'relay_unit_id': 1}], 'relay_unit_assignments': {'1': 1}, 'status': 'pending', 'delivered_volumes': {}, 'last_delivery': {}}
Mode: Instant

Schedule Debug Info:
Desired water outputs: {}
Relay assignments: {'1': 1}

DEBUG - run_program:
system_controller type: <class 'controllers.system_controller.SystemController'>
Running program with schedule: 1, mode: Instant

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
Scheduling delivery in 104.12 seconds
Scheduled 1 deliveries
Triggering relay unit 1 for 1.0ml (20 triggers)
Executing trigger 1/20 for relay unit 1
Executing trigger 2/20 for relay unit 1
Executing trigger 3/20 for relay unit 1
Executing trigger 4/20 for relay unit 1
Executing trigger 5/20 for relay unit 1
Executing trigger 6/20 for relay unit 1
Executing trigger 7/20 for relay unit 1
Executing trigger 8/20 for relay unit 1
Executing trigger 9/20 for relay unit 1
Executing trigger 10/20 for relay unit 1
Executing trigger 11/20 for relay unit 1
Executing trigger 12/20 for relay unit 1
Executing trigger 13/20 for relay unit 1
Executing trigger 14/20 for relay unit 1
Executing trigger 15/20 for relay unit 1
Executing trigger 16/20 for relay unit 1
Executing trigger 17/20 for relay unit 1
Executing trigger 18/20 for relay unit 1
Executing trigger 19/20 for relay unit 1
Executing trigger 20/20 for relay unit 1
Successfully triggered relay unit 1 20 times
2025-02-11 15:03:14.383159 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-02-11T15:03:14.383325', 'relay_info': 'Successfully triggered relay unit 1 20 times'}
[DEBUG] Starting cleanup process
[DEBUG] All relays deactivated
[ERROR] Unexpected error during cleanup: wrapped C/C++ object of type QTimer has been deleted