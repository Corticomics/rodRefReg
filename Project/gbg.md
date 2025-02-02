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

DEBUG INFO:
Schedule: {'schedule_id': 18, 'name': 'cancel mid triggers test', 'water_volume': 3.0, 'start_time': '2025-02-02T12:05:58.882000', 'end_time': '2025-02-02T12:05:59.727000', 'created_by': 1, 'is_super_user': 0, 'delivery_mode': 'instant', 'cycles_per_day': 1, 'animals': [1, 2], 'desired_water_outputs': {}, 'window_data': {}, 'instant_deliveries': [{'animal_id': 1, 'datetime': datetime.datetime(2025, 2, 2, 12, 5, 58, 882000), 'volume': 2.0, 'relay_unit_id': 1}, {'animal_id': 2, 'datetime': datetime.datetime(2025, 2, 2, 12, 5, 59, 727000), 'volume': 1.0, 'relay_unit_id': 2}], 'relay_unit_assignments': {'1': 1, '2': 2}, 'status': 'pending', 'delivered_volumes': {}, 'last_delivery': {}}
Mode: Instant

Schedule Debug Info:
Desired water outputs: {}
Relay assignments: {'1': 1, '2': 2}

Settings Debug Info:
Settings desired water outputs: {}
Settings relay assignments: {'1': 1, '2': 2}
Starting schedule execution with mode: Instant, window_start: 1738523158.882, window_end: 1738523159.727
Animals: [1, 2]
Relay assignments: {'1': 1, '2': 2}
Water outputs: {}
Running program with schedule: cancel mid triggers test, mode: Instant

Worker Settings Debug:
Mode: Instant
Desired outputs: None
Relay assignments: None

Program Started
Starting instant cycle
Processing 2 deliveries
Scheduling delivery in 192.57 seconds
Scheduling delivery in 193.42 seconds
Scheduled 2 deliveries
RelayWorker stopped
[DEBUG] Starting cleanup process
[DEBUG] All relays deactivated
[ERROR] An unexpected error occurred during cleanup: wrapped C/C++ object of type QTimer has been deleted
Program Stopped
[DEBUG] Starting cleanup process
[DEBUG] All relays deactivated
[ERROR] An unexpected error occurred during cleanup: wrapped C/C++ object of type QTimer has been deleted

DEBUG INFO:
Schedule: {'schedule_id': 18, 'name': 'cancel mid triggers test', 'water_volume': 3.0, 'start_time': '2025-02-02T12:05:58.882000', 'end_time': '2025-02-02T12:05:59.727000', 'created_by': 1, 'is_super_user': 0, 'delivery_mode': 'instant', 'cycles_per_day': 1, 'animals': [1, 2], 'desired_water_outputs': {}, 'window_data': {}, 'instant_deliveries': [{'animal_id': 1, 'datetime': datetime.datetime(2025, 2, 2, 12, 5, 58, 882000), 'volume': 2.0, 'relay_unit_id': 1}, {'animal_id': 2, 'datetime': datetime.datetime(2025, 2, 2, 12, 5, 59, 727000), 'volume': 1.0, 'relay_unit_id': 2}], 'relay_unit_assignments': {'1': 1, '2': 2}, 'status': 'pending', 'delivered_volumes': {}, 'last_delivery': {}}
Mode: Instant

Schedule Debug Info:
Desired water outputs: {}
Relay assignments: {'1': 1, '2': 2}

Settings Debug Info:
Settings desired water outputs: {}
Settings relay assignments: {'1': 1, '2': 2}
Starting schedule execution with mode: Instant, window_start: 1738523158.882, window_end: 1738523159.727
Animals: [1, 2]
Relay assignments: {'1': 1, '2': 2}
Water outputs: {}
Running program with schedule: cancel mid triggers test, mode: Instant
Failed to run program: wrapped C/C++ object of type QThread has been deleted
2025-02-02 12:03:13.048809 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-02-02T12:03:13.049514', 'relay_info': 'Program error: wrapped C/C++ object of type QThread has been deleted'}