Failed to pause schedule: 'RunStopSection' object has no attribute 'schedule_manager'


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
Adding staggered schedule: tesrt syg
Animals: [1, 2]
Relay assignments: {'1': 1, '2': 2}
Water outputs: {'1': 1.0, '2': 2.0}
save_current_schedule: added staggered schedule with details:<models.Schedule.Schedule object at 0x7fa63a8dd0>

DEBUG INFO:
Schedule: {'schedule_id': 9, 'name': 'tesrt syg', 'water_volume': 3.0, 'start_time': '2025-02-02T11:09:19.737000', 'end_time': '2025-02-02T11:20:21.161000', 'created_by': 1, 'is_super_user': 0, 'delivery_mode': 'staggered', 'cycles_per_day': 1, 'animals': [1, 2], 'desired_water_outputs': {'1': 1.0, '2': 2.0}, 'window_data': {}, 'instant_deliveries': [], 'relay_unit_assignments': {'1': 1, '2': 2}, 'status': 'pending', 'delivered_volumes': {}, 'last_delivery': {}}
Mode: Staggered

Schedule Debug Info:
Desired water outputs: {'1': 1.0, '2': 2.0}
Relay assignments: {'1': 1, '2': 2}

Settings Debug Info:
Settings desired water outputs: {'1': 1.0, '2': 2.0}
Settings relay assignments: {'1': 1, '2': 2}
Starting schedule execution with mode: Staggered, window_start: 1738519759.737, window_end: 1738520421.161
Animals: [1, 2]
Relay assignments: {'1': 1, '2': 2}
Water outputs: {'1': 1.0, '2': 2.0}
Running program with schedule: tesrt syg, mode: Staggered

Worker Settings Debug:
Mode: Staggered
Desired outputs: {'1': 1.0, '2': 2.0}
Relay assignments: {'1': 1, '2': 2}

Program Started
Starting staggered cycle

Staggered Cycle Debug Info:
Current time: 2025-02-02 11:07:57.438720
Initializing animal windows
Created window for animal 1: {'start': datetime.datetime(2025, 2, 2, 11, 9, 19, 737000), 'end': datetime.datetime(2025, 2, 2, 11, 20, 21, 161000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 1.0, 'volume_per_cycle': 0.1}
Volume per cycle: 0.1ml
Created window for animal 2: {'start': datetime.datetime(2025, 2, 2, 11, 9, 19, 737000), 'end': datetime.datetime(2025, 2, 2, 11, 20, 21, 161000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2}
Volume per cycle: 0.2ml
Checking active animals at 2025-02-02 11:07:57.438720
Window start: 2025-02-02 11:09:19.737000, Window end: 2025-02-02 11:20:21.161000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 2, 2, 11, 9, 19, 737000), 'end': datetime.datetime(2025, 2, 2, 11, 20, 21, 161000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 1.0, 'volume_per_cycle': 0.1}), ('2', {'start': datetime.datetime(2025, 2, 2, 11, 9, 19, 737000), 'end': datetime.datetime(2025, 2, 2, 11, 20, 21, 161000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2})])
Current time (2025-02-02 11:07:57.438720) is before window start (2025-02-02 11:09:19.737000)

Staggered Cycle Debug Info:
Current time: 2025-02-02 11:09:19.528792
Checking active animals at 2025-02-02 11:09:19.528792
Window start: 2025-02-02 11:09:19.737000, Window end: 2025-02-02 11:20:21.161000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 2, 2, 11, 9, 19, 737000), 'end': datetime.datetime(2025, 2, 2, 11, 20, 21, 161000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 1.0, 'volume_per_cycle': 0.1}), ('2', {'start': datetime.datetime(2025, 2, 2, 11, 9, 19, 737000), 'end': datetime.datetime(2025, 2, 2, 11, 20, 21, 161000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2})])
Current time (2025-02-02 11:09:19.528792) is before window start (2025-02-02 11:09:19.737000)

Staggered Cycle Debug Info:
Current time: 2025-02-02 11:09:19.742167
Checking active animals at 2025-02-02 11:09:19.742167
Window start: 2025-02-02 11:09:19.737000, Window end: 2025-02-02 11:20:21.161000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 2, 2, 11, 9, 19, 737000), 'end': datetime.datetime(2025, 2, 2, 11, 20, 21, 161000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 1.0, 'volume_per_cycle': 0.1}), ('2', {'start': datetime.datetime(2025, 2, 2, 11, 9, 19, 737000), 'end': datetime.datetime(2025, 2, 2, 11, 20, 21, 161000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2})])
Animal 1: delivered=0, target=1.0
Animal 1 is active with 1.0mL remaining
Animal 2: delivered=0, target=2.0
Animal 2 is active with 2.0mL remaining
Active animals: dict_items([('1', {'remaining': 1.0, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 2.0, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 2: 0.2mL in 0s
Scheduled delivery for animal 1: 0.1mL in 2.1s
Triggering relay unit 2 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 2
Executing trigger 2/4 for relay unit 2
Executing trigger 3/4 for relay unit 2
Executing trigger 4/4 for relay unit 2
Successfully triggered relay unit 2 4 times
2025-02-02 11:09:23.576220 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-02-02T11:09:23.576375', 'relay_info': 'Successfully triggered relay unit 2 4 times'}
Delivered 0.200mL to animal 2 (Total: 0.200mL)
Triggering relay unit 1 for 0.1ml (2 triggers)
Executing trigger 1/2 for relay unit 1
Executing trigger 2/2 for relay unit 1
Successfully triggered relay unit 1 2 times
2025-02-02 11:09:25.466450 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-02-02T11:09:25.466610', 'relay_info': 'Successfully triggered relay unit 1 2 times'}
Delivered 0.100mL to animal 1 (Total: 0.100mL)

Staggered Cycle Debug Info:
Current time: 2025-02-02 11:10:25.451592
Checking active animals at 2025-02-02 11:10:25.451592
Window start: 2025-02-02 11:09:19.737000, Window end: 2025-02-02 11:20:21.161000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 2, 2, 11, 9, 19, 737000), 'end': datetime.datetime(2025, 2, 2, 11, 20, 21, 161000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 1.0, 'volume_per_cycle': 0.1}), ('2', {'start': datetime.datetime(2025, 2, 2, 11, 9, 19, 737000), 'end': datetime.datetime(2025, 2, 2, 11, 20, 21, 161000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2})])
Animal 1: delivered=0.1, target=1.0
Animal 1 is active with 0.9mL remaining
Animal 2: delivered=0.2, target=2.0
Animal 2 is active with 1.8mL remaining
Active animals: dict_items([('1', {'remaining': 0.9, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 1.8, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 2: 0.2mL in 0s
Scheduled delivery for animal 1: 0.1mL in 2.1s
Triggering relay unit 2 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 2
Executing trigger 2/4 for relay unit 2
Executing trigger 3/4 for relay unit 2
Executing trigger 4/4 for relay unit 2
Successfully triggered relay unit 2 4 times
2025-02-02 11:10:29.277260 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-02-02T11:10:29.277418', 'relay_info': 'Successfully triggered relay unit 2 4 times'}
Delivered 0.200mL to animal 2 (Total: 0.400mL)
Triggering relay unit 1 for 0.1ml (2 triggers)
Executing trigger 1/2 for relay unit 1
Executing trigger 2/2 for relay unit 1
Successfully triggered relay unit 1 2 times
2025-02-02 11:10:31.173434 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-02-02T11:10:31.173613', 'relay_info': 'Successfully triggered relay unit 1 2 times'}
Delivered 0.100mL to animal 1 (Total: 0.200mL)

Staggered Cycle Debug Info:
Current time: 2025-02-02 11:11:31.506996
Checking active animals at 2025-02-02 11:11:31.506996
Window start: 2025-02-02 11:09:19.737000, Window end: 2025-02-02 11:20:21.161000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 2, 2, 11, 9, 19, 737000), 'end': datetime.datetime(2025, 2, 2, 11, 20, 21, 161000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 1.0, 'volume_per_cycle': 0.1}), ('2', {'start': datetime.datetime(2025, 2, 2, 11, 9, 19, 737000), 'end': datetime.datetime(2025, 2, 2, 11, 20, 21, 161000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2})])
Animal 1: delivered=0.2, target=1.0
Animal 1 is active with 0.8mL remaining
Animal 2: delivered=0.4, target=2.0
Animal 2 is active with 1.6mL remaining
Active animals: dict_items([('1', {'remaining': 0.8, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 1.6, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 2: 0.2mL in 0s
Scheduled delivery for animal 1: 0.1mL in 2.1s
Triggering relay unit 2 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 2
Executing trigger 2/4 for relay unit 2
Executing trigger 3/4 for relay unit 2
Executing trigger 4/4 for relay unit 2
Successfully triggered relay unit 2 4 times
2025-02-02 11:11:35.343683 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-02-02T11:11:35.343847', 'relay_info': 'Successfully triggered relay unit 2 4 times'}
Delivered 0.200mL to animal 2 (Total: 0.600mL)
Triggering relay unit 1 for 0.1ml (2 triggers)
Executing trigger 1/2 for relay unit 1
Executing trigger 2/2 for relay unit 1
Successfully triggered relay unit 1 2 times
2025-02-02 11:11:37.238208 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-02-02T11:11:37.238446', 'relay_info': 'Successfully triggered relay unit 1 2 times'}
Delivered 0.100mL to animal 1 (Total: 0.300mL)

Staggered Cycle Debug Info:
Current time: 2025-02-02 11:12:37.462534
Checking active animals at 2025-02-02 11:12:37.462534
Window start: 2025-02-02 11:09:19.737000, Window end: 2025-02-02 11:20:21.161000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 2, 2, 11, 9, 19, 737000), 'end': datetime.datetime(2025, 2, 2, 11, 20, 21, 161000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 1.0, 'volume_per_cycle': 0.1}), ('2', {'start': datetime.datetime(2025, 2, 2, 11, 9, 19, 737000), 'end': datetime.datetime(2025, 2, 2, 11, 20, 21, 161000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2})])
Animal 1: delivered=0.30000000000000004, target=1.0
Animal 1 is active with 0.7mL remaining
Animal 2: delivered=0.6000000000000001, target=2.0
Animal 2 is active with 1.4mL remaining
Active animals: dict_items([('1', {'remaining': 0.7, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 1.4, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 2: 0.2mL in 0s
Scheduled delivery for animal 1: 0.1mL in 2.1s
Triggering relay unit 2 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 2
Executing trigger 2/4 for relay unit 2
Executing trigger 3/4 for relay unit 2
Executing trigger 4/4 for relay unit 2
Successfully triggered relay unit 2 4 times
2025-02-02 11:12:41.289474 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-02-02T11:12:41.289639', 'relay_info': 'Successfully triggered relay unit 2 4 times'}
Delivered 0.200mL to animal 2 (Total: 0.800mL)
Triggering relay unit 1 for 0.1ml (2 triggers)
Executing trigger 1/2 for relay unit 1
Executing trigger 2/2 for relay unit 1
Successfully triggered relay unit 1 2 times
2025-02-02 11:12:43.191768 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-02-02T11:12:43.191928', 'relay_info': 'Successfully triggered relay unit 1 2 times'}
Delivered 0.100mL to animal 1 (Total: 0.400mL)

Staggered Cycle Debug Info:
Current time: 2025-02-02 11:13:43.507734
Checking active animals at 2025-02-02 11:13:43.507734
Window start: 2025-02-02 11:09:19.737000, Window end: 2025-02-02 11:20:21.161000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 2, 2, 11, 9, 19, 737000), 'end': datetime.datetime(2025, 2, 2, 11, 20, 21, 161000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 1.0, 'volume_per_cycle': 0.1}), ('2', {'start': datetime.datetime(2025, 2, 2, 11, 9, 19, 737000), 'end': datetime.datetime(2025, 2, 2, 11, 20, 21, 161000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2})])
Animal 1: delivered=0.4, target=1.0
Animal 1 is active with 0.6mL remaining
Animal 2: delivered=0.8, target=2.0
Animal 2 is active with 1.2mL remaining
Active animals: dict_items([('1', {'remaining': 0.6, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 1.2, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 2: 0.2mL in 0s
Scheduled delivery for animal 1: 0.1mL in 2.1s
Triggering relay unit 2 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 2
Executing trigger 2/4 for relay unit 2
Executing trigger 3/4 for relay unit 2
Executing trigger 4/4 for relay unit 2
Successfully triggered relay unit 2 4 times
2025-02-02 11:13:47.398468 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-02-02T11:13:47.398617', 'relay_info': 'Successfully triggered relay unit 2 4 times'}
Delivered 0.200mL to animal 2 (Total: 1.000mL)
Triggering relay unit 1 for 0.1ml (2 triggers)
Executing trigger 1/2 for relay unit 1
Executing trigger 2/2 for relay unit 1
Successfully triggered relay unit 1 2 times
2025-02-02 11:13:49.378753 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-02-02T11:13:49.378905', 'relay_info': 'Successfully triggered relay unit 1 2 times'}
Delivered 0.100mL to animal 1 (Total: 0.500mL)
RelayWorker stopped
[DEBUG] Starting cleanup process
[DEBUG] All relays deactivated
[DEBUG] All timers stopped
[DEBUG] Cleanup completed. Program ready for the next job.
Program Stopped



DEBUG INFO:
Schedule: {'schedule_id': 10, 'name': 'tyt', 'water_volume': 3.0, 'start_time': '2025-02-02T11:17:07.832000', 'end_time': '2025-02-02T11:17:08.536000', 'created_by': 1, 'is_super_user': 0, 'delivery_mode': 'instant', 'cycles_per_day': 1, 'animals': [1, 2], 'desired_water_outputs': {}, 'window_data': {}, 'instant_deliveries': [{'animal_id': 1, 'datetime': datetime.datetime(2025, 2, 2, 11, 17, 7, 832000), 'volume': 1.0, 'relay_unit_id': 1}, {'animal_id': 2, 'datetime': datetime.datetime(2025, 2, 2, 11, 17, 8, 536000), 'volume': 2.0, 'relay_unit_id': 2}], 'relay_unit_assignments': {'1': 1, '2': 2}, 'status': 'pending', 'delivered_volumes': {}, 'last_delivery': {}}
Mode: Instant

Schedule Debug Info:
Desired water outputs: {}
Relay assignments: {'1': 1, '2': 2}

Settings Debug Info:
Settings desired water outputs: {}
Settings relay assignments: {'1': 1, '2': 2}
Starting schedule execution with mode: Instant, window_start: 1738520227.832, window_end: 1738520228.536
Animals: [1, 2]
Relay assignments: {'1': 1, '2': 2}
Water outputs: {}
Running program with schedule: tyt, mode: Instant
Failed to run program: wrapped C/C++ object of type QThread has been deleted
2025-02-02 11:15:19.410676 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-02-02T11:15:19.411416', 'relay_info': 'Program error: wrapped C/C++ object of type QThread has been deleted'}