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
save_current_schedule: adding instant delivery for animal 1 at 2025-02-11 14:54:26.064000 with volume 1.0
save_current_schedule: adding instant schedule with details:<models.Schedule.Schedule object at 0x7f81342b90>

DEBUG - RunStopSection run_program:
self.system_controller type: <class 'controllers.system_controller.SystemController'>

DEBUG INFO:
Schedule: {'schedule_id': 9, 'name': 'test', 'water_volume': 1.0, 'start_time': '2025-02-11T14:54:26.064000', 'end_time': '2025-02-11T14:54:26.064000', 'created_by': 1, 'is_super_user': 0, 'delivery_mode': 'instant', 'cycles_per_day': 1, 'animals': [1], 'desired_water_outputs': {}, 'window_data': {}, 'instant_deliveries': [{'animal_id': 1, 'datetime': datetime.datetime(2025, 2, 11, 14, 54, 26, 64000), 'volume': 1.0, 'relay_unit_id': 1}], 'relay_unit_assignments': {'1': 1}, 'status': 'pending', 'delivered_volumes': {}, 'last_delivery': {}}
Mode: Instant

Schedule Debug Info:
Desired water outputs: {}
Relay assignments: {'1': 1}

DEBUG - run_program:
system_controller type: <class 'controllers.system_controller.SystemController'>
Running program with schedule: test, mode: Instant

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
Skipping past delivery time: 2025-02-11 14:54:26.064000
No future deliveries to schedule
[DEBUG] Starting cleanup process
[DEBUG] Worker still running, waiting for completion
save_current_schedule: adding instant deliveries for unit 1
save_current_schedule: adding instant delivery for animal 1 at 2025-02-11 14:55:26.064000 with volume 1.0
save_current_schedule: adding instant schedule with details:<models.Schedule.Schedule object at 0x7f8133db50>
[DEBUG] Starting stop sequence
[ERROR] Stop sequence failed: wrapped C/C++ object of type QTimer has been deleted