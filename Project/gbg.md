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
Adding staggered schedule: pfv
Animals: [1, 2]
Relay assignments: {'1': 1, '2': 2}
Water outputs: {'1': 2.0, '2': 2.0}

DEBUG INFO:
Schedule: {'schedule_id': 19, 'name': 'pfv', 'water_volume': 8.0, 'start_time': '2025-01-25T17:02:44.451000', 'end_time': '2025-01-25T17:07:45.074000', 'created_by': 1, 'is_super_user': 0, 'delivery_mode': 'staggered', 'cycles_per_day': 1, 'animals': [1, 2], 'desired_water_outputs': {'1': 2.0, '2': 2.0}, 'instant_deliveries': [], 'relay_unit_assignments': {'1': 1, '2': 2}, 'status': 'pending', 'delivered_volumes': {}, 'last_delivery': {}, 'window_data': {}}
Mode: Staggered

Schedule Debug Info:
Desired water outputs: {'1': 2.0, '2': 2.0}
Relay assignments: {'1': 1, '2': 2}

Settings Debug Info:
Settings desired water outputs: {'1': 2.0, '2': 2.0}
Settings relay assignments: {'1': 1, '2': 2}
Starting schedule execution with mode: Staggered, window_start: 1737849764.451, window_end: 1737850065.074
Animals: [1, 2]
Relay assignments: {'1': 1, '2': 2}
Water outputs: {'1': 2.0, '2': 2.0}
Running program with schedule: pfv, mode: Staggered

Worker Settings Debug:
Mode: Staggered
Desired outputs: {'1': 2.0, '2': 2.0}
Relay assignments: {'1': 1, '2': 2}

Program Started
Starting staggered cycle

Staggered Cycle Debug Info:
Current time: 2025-01-25 17:00:25.240586

Cycle Calculation Debug:
Window duration: 300.623 seconds
Max volume to deliver: 2.0ml
Min cycles needed: 10.0
Calculated cycle interval: 30.0623 seconds
Initializing animal windows
Relay assignments: {'1': 1, '2': 2}
Desired outputs: {'1': 2.0, '2': 2.0}
Created window for animal 1: {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 2.0, 'volume_per_cycle': 0.2}
Volume per cycle: 0.2ml
Created window for animal 2: {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2}
Volume per cycle: 0.2ml
Checking active animals at 2025-01-25 17:00:25.240586
Window start: 2025-01-25 17:02:44.451000, Window end: 2025-01-25 17:07:45.074000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 2.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2})])
Current time (2025-01-25 17:00:25.240586) is before window start (2025-01-25 17:02:44.451000)

Staggered Cycle Debug Info:
Current time: 2025-01-25 17:02:44.074795

Cycle Calculation Debug:
Window duration: 300.623 seconds
Max volume to deliver: 2.0ml
Min cycles needed: 10.0
Calculated cycle interval: 30.0623 seconds
Checking active animals at 2025-01-25 17:02:44.074795
Window start: 2025-01-25 17:02:44.451000, Window end: 2025-01-25 17:07:45.074000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 2.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2})])
Current time (2025-01-25 17:02:44.074795) is before window start (2025-01-25 17:02:44.451000)

Staggered Cycle Debug Info:
Current time: 2025-01-25 17:02:44.452997

Cycle Calculation Debug:
Window duration: 300.623 seconds
Max volume to deliver: 2.0ml
Min cycles needed: 10.0
Calculated cycle interval: 30.0623 seconds
Checking active animals at 2025-01-25 17:02:44.452997
Window start: 2025-01-25 17:02:44.451000, Window end: 2025-01-25 17:07:45.074000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 2.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2})])
Animal 1: delivered=0, target=2.0
Animal 1 is active with 2.0mL remaining
Animal 2: delivered=0, target=2.0
Animal 2 is active with 2.0mL remaining
Active animals: dict_items([('1', {'remaining': 2.0, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 2.0, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 1: 0.2mL in 0s
Scheduled delivery for animal 2: 0.2mL in 2.1s
Triggering relay unit 1 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 1
Executing trigger 2/4 for relay unit 1
Executing trigger 3/4 for relay unit 1
Executing trigger 4/4 for relay unit 1
Successfully triggered relay unit 1 4 times
2025-01-25 17:02:48.443924 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:02:48.444094', 'relay_info': 'Successfully triggered relay unit 1 4 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'
Triggering relay unit 2 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 2
Executing trigger 2/4 for relay unit 2
Executing trigger 3/4 for relay unit 2
Executing trigger 4/4 for relay unit 2
Successfully triggered relay unit 2 4 times
2025-01-25 17:02:52.317550 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:02:52.317688', 'relay_info': 'Successfully triggered relay unit 2 4 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'

Staggered Cycle Debug Info:
Current time: 2025-01-25 17:03:14.004664

Cycle Calculation Debug:
Window duration: 300.623 seconds
Max volume to deliver: 2.0ml
Min cycles needed: 10.0
Calculated cycle interval: 30.0623 seconds
Checking active animals at 2025-01-25 17:03:14.004664
Window start: 2025-01-25 17:02:44.451000, Window end: 2025-01-25 17:07:45.074000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 2.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2})])
Animal 1: delivered=0.2, target=2.0
Animal 1 is active with 1.8mL remaining
Animal 2: delivered=0.2, target=2.0
Animal 2 is active with 1.8mL remaining
Active animals: dict_items([('1', {'remaining': 1.8, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 1.8, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 1: 0.2mL in 0s
Scheduled delivery for animal 2: 0.2mL in 2.1s
Triggering relay unit 1 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 1
Executing trigger 2/4 for relay unit 1
Executing trigger 3/4 for relay unit 1
Executing trigger 4/4 for relay unit 1
Successfully triggered relay unit 1 4 times
2025-01-25 17:03:18.006885 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:03:18.007032', 'relay_info': 'Successfully triggered relay unit 1 4 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'
Triggering relay unit 2 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 2
Executing trigger 2/4 for relay unit 2
Executing trigger 3/4 for relay unit 2
Executing trigger 4/4 for relay unit 2
Successfully triggered relay unit 2 4 times
2025-01-25 17:03:21.810173 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:03:21.810381', 'relay_info': 'Successfully triggered relay unit 2 4 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'

Staggered Cycle Debug Info:
Current time: 2025-01-25 17:03:44.004934

Cycle Calculation Debug:
Window duration: 300.623 seconds
Max volume to deliver: 2.0ml
Min cycles needed: 10.0
Calculated cycle interval: 30.0623 seconds
Checking active animals at 2025-01-25 17:03:44.004934
Window start: 2025-01-25 17:02:44.451000, Window end: 2025-01-25 17:07:45.074000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 2.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2})])
Animal 1: delivered=0.4, target=2.0
Animal 1 is active with 1.6mL remaining
Animal 2: delivered=0.4, target=2.0
Animal 2 is active with 1.6mL remaining
Active animals: dict_items([('1', {'remaining': 1.6, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 1.6, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 1: 0.2mL in 0s
Scheduled delivery for animal 2: 0.2mL in 2.1s
Triggering relay unit 1 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 1
Executing trigger 2/4 for relay unit 1
Executing trigger 3/4 for relay unit 1
Executing trigger 4/4 for relay unit 1
Successfully triggered relay unit 1 4 times
2025-01-25 17:03:47.916254 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:03:47.916408', 'relay_info': 'Successfully triggered relay unit 1 4 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'
Triggering relay unit 2 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 2
Executing trigger 2/4 for relay unit 2
Executing trigger 3/4 for relay unit 2
Executing trigger 4/4 for relay unit 2
Successfully triggered relay unit 2 4 times
2025-01-25 17:03:51.727638 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:03:51.727792', 'relay_info': 'Successfully triggered relay unit 2 4 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'

Staggered Cycle Debug Info:
Current time: 2025-01-25 17:04:14.005300

Cycle Calculation Debug:
Window duration: 300.623 seconds
Max volume to deliver: 2.0ml
Min cycles needed: 10.0
Calculated cycle interval: 30.0623 seconds
Checking active animals at 2025-01-25 17:04:14.005300
Window start: 2025-01-25 17:02:44.451000, Window end: 2025-01-25 17:07:45.074000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 2.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2})])
Animal 1: delivered=0.6000000000000001, target=2.0
Animal 1 is active with 1.4mL remaining
Animal 2: delivered=0.6000000000000001, target=2.0
Animal 2 is active with 1.4mL remaining
Active animals: dict_items([('1', {'remaining': 1.4, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 1.4, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 1: 0.2mL in 0s
Scheduled delivery for animal 2: 0.2mL in 2.1s
Triggering relay unit 1 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 1
Executing trigger 2/4 for relay unit 1
Executing trigger 3/4 for relay unit 1
Executing trigger 4/4 for relay unit 1
Successfully triggered relay unit 1 4 times
2025-01-25 17:04:17.883279 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:04:17.883428', 'relay_info': 'Successfully triggered relay unit 1 4 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'
Triggering relay unit 2 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 2
Executing trigger 2/4 for relay unit 2
Executing trigger 3/4 for relay unit 2
Executing trigger 4/4 for relay unit 2
Successfully triggered relay unit 2 4 times
2025-01-25 17:04:21.807245 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:04:21.807398', 'relay_info': 'Successfully triggered relay unit 2 4 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'

Staggered Cycle Debug Info:
Current time: 2025-01-25 17:04:44.004932

Cycle Calculation Debug:
Window duration: 300.623 seconds
Max volume to deliver: 2.0ml
Min cycles needed: 10.0
Calculated cycle interval: 30.0623 seconds
Checking active animals at 2025-01-25 17:04:44.004932
Window start: 2025-01-25 17:02:44.451000, Window end: 2025-01-25 17:07:45.074000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 2.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2})])
Animal 1: delivered=0.8, target=2.0
Animal 1 is active with 1.2mL remaining
Animal 2: delivered=0.8, target=2.0
Animal 2 is active with 1.2mL remaining
Active animals: dict_items([('1', {'remaining': 1.2, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 1.2, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 1: 0.2mL in 0s
Scheduled delivery for animal 2: 0.2mL in 2.1s
Triggering relay unit 1 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 1
Executing trigger 2/4 for relay unit 1
Executing trigger 3/4 for relay unit 1
Executing trigger 4/4 for relay unit 1
Successfully triggered relay unit 1 4 times
2025-01-25 17:04:47.873373 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:04:47.873529', 'relay_info': 'Successfully triggered relay unit 1 4 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'
Triggering relay unit 2 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 2
Executing trigger 2/4 for relay unit 2
Executing trigger 3/4 for relay unit 2
Executing trigger 4/4 for relay unit 2
Successfully triggered relay unit 2 4 times
2025-01-25 17:04:51.817257 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:04:51.817412', 'relay_info': 'Successfully triggered relay unit 2 4 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'

Staggered Cycle Debug Info:
Current time: 2025-01-25 17:05:14.000256

Cycle Calculation Debug:
Window duration: 300.623 seconds
Max volume to deliver: 2.0ml
Min cycles needed: 10.0
Calculated cycle interval: 30.0623 seconds
Checking active animals at 2025-01-25 17:05:14.000256
Window start: 2025-01-25 17:02:44.451000, Window end: 2025-01-25 17:07:45.074000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 2.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2})])
Animal 1: delivered=1.0, target=2.0
Animal 1 is active with 1.0mL remaining
Animal 2: delivered=1.0, target=2.0
Animal 2 is active with 1.0mL remaining
Active animals: dict_items([('1', {'remaining': 1.0, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 1.0, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 1: 0.2mL in 0s
Scheduled delivery for animal 2: 0.2mL in 2.1s
Triggering relay unit 1 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 1
Executing trigger 2/4 for relay unit 1
Executing trigger 3/4 for relay unit 1
Executing trigger 4/4 for relay unit 1
Successfully triggered relay unit 1 4 times
2025-01-25 17:05:18.196864 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:05:18.197017', 'relay_info': 'Successfully triggered relay unit 1 4 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'
Triggering relay unit 2 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 2
Executing trigger 2/4 for relay unit 2
Executing trigger 3/4 for relay unit 2
Executing trigger 4/4 for relay unit 2
Successfully triggered relay unit 2 4 times
2025-01-25 17:05:22.001416 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:05:22.001640', 'relay_info': 'Successfully triggered relay unit 2 4 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'

Staggered Cycle Debug Info:
Current time: 2025-01-25 17:05:44.004577

Cycle Calculation Debug:
Window duration: 300.623 seconds
Max volume to deliver: 2.0ml
Min cycles needed: 10.0
Calculated cycle interval: 30.0623 seconds
Checking active animals at 2025-01-25 17:05:44.004577
Window start: 2025-01-25 17:02:44.451000, Window end: 2025-01-25 17:07:45.074000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 2.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2})])
Animal 1: delivered=1.2, target=2.0
Animal 1 is active with 0.8mL remaining
Animal 2: delivered=1.2, target=2.0
Animal 2 is active with 0.8mL remaining
Active animals: dict_items([('1', {'remaining': 0.8, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 0.8, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 1: 0.2mL in 0s
Scheduled delivery for animal 2: 0.2mL in 2.1s
Triggering relay unit 1 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 1
Executing trigger 2/4 for relay unit 1
Executing trigger 3/4 for relay unit 1
Executing trigger 4/4 for relay unit 1
Successfully triggered relay unit 1 4 times
2025-01-25 17:05:48.087025 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:05:48.087174', 'relay_info': 'Successfully triggered relay unit 1 4 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'
Triggering relay unit 2 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 2
Executing trigger 2/4 for relay unit 2
Executing trigger 3/4 for relay unit 2
Executing trigger 4/4 for relay unit 2
Successfully triggered relay unit 2 4 times
2025-01-25 17:05:51.951214 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:05:51.951362', 'relay_info': 'Successfully triggered relay unit 2 4 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'

Staggered Cycle Debug Info:
Current time: 2025-01-25 17:06:14.004676

Cycle Calculation Debug:
Window duration: 300.623 seconds
Max volume to deliver: 2.0ml
Min cycles needed: 10.0
Calculated cycle interval: 30.0623 seconds
Checking active animals at 2025-01-25 17:06:14.004676
Window start: 2025-01-25 17:02:44.451000, Window end: 2025-01-25 17:07:45.074000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 2.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2})])
Animal 1: delivered=1.4, target=2.0
Animal 1 is active with 0.6000000000000001mL remaining
Animal 2: delivered=1.4, target=2.0
Animal 2 is active with 0.6000000000000001mL remaining
Active animals: dict_items([('1', {'remaining': 0.6000000000000001, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 0.6000000000000001, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 1: 0.2mL in 0s
Scheduled delivery for animal 2: 0.2mL in 2.1s
Triggering relay unit 1 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 1
Executing trigger 2/4 for relay unit 1
Executing trigger 3/4 for relay unit 1
Executing trigger 4/4 for relay unit 1
Successfully triggered relay unit 1 4 times
2025-01-25 17:06:17.916587 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:06:17.916742', 'relay_info': 'Successfully triggered relay unit 1 4 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'
Triggering relay unit 2 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 2
Executing trigger 2/4 for relay unit 2
Executing trigger 3/4 for relay unit 2
Executing trigger 4/4 for relay unit 2
Successfully triggered relay unit 2 4 times
2025-01-25 17:06:21.730831 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:06:21.730976', 'relay_info': 'Successfully triggered relay unit 2 4 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'

Staggered Cycle Debug Info:
Current time: 2025-01-25 17:06:44.005097

Cycle Calculation Debug:
Window duration: 300.623 seconds
Max volume to deliver: 2.0ml
Min cycles needed: 10.0
Calculated cycle interval: 30.0623 seconds
Checking active animals at 2025-01-25 17:06:44.005097
Window start: 2025-01-25 17:02:44.451000, Window end: 2025-01-25 17:07:45.074000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 2.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2})])
Animal 1: delivered=1.5999999999999999, target=2.0
Animal 1 is active with 0.40000000000000013mL remaining
Animal 2: delivered=1.5999999999999999, target=2.0
Animal 2 is active with 0.40000000000000013mL remaining
Active animals: dict_items([('1', {'remaining': 0.40000000000000013, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 0.40000000000000013, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 1: 0.2mL in 0s
Scheduled delivery for animal 2: 0.2mL in 2.1s
Triggering relay unit 1 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 1
Executing trigger 2/4 for relay unit 1
Executing trigger 3/4 for relay unit 1
Executing trigger 4/4 for relay unit 1
Successfully triggered relay unit 1 4 times
2025-01-25 17:06:47.836813 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:06:47.836968', 'relay_info': 'Successfully triggered relay unit 1 4 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'
Triggering relay unit 2 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 2
Executing trigger 2/4 for relay unit 2
Executing trigger 3/4 for relay unit 2
Executing trigger 4/4 for relay unit 2
Successfully triggered relay unit 2 4 times
2025-01-25 17:06:51.700685 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:06:51.700838', 'relay_info': 'Successfully triggered relay unit 2 4 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'

Staggered Cycle Debug Info:
Current time: 2025-01-25 17:07:14.005640

Cycle Calculation Debug:
Window duration: 300.623 seconds
Max volume to deliver: 2.0ml
Min cycles needed: 10.0
Calculated cycle interval: 30.0623 seconds
Checking active animals at 2025-01-25 17:07:14.005640
Window start: 2025-01-25 17:02:44.451000, Window end: 2025-01-25 17:07:45.074000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 2.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2})])
Animal 1: delivered=1.7999999999999998, target=2.0
Animal 1 is active with 0.20000000000000018mL remaining
Animal 2: delivered=1.7999999999999998, target=2.0
Animal 2 is active with 0.20000000000000018mL remaining
Active animals: dict_items([('1', {'remaining': 0.20000000000000018, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 0.20000000000000018, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 1: 0.2mL in 0s
Scheduled delivery for animal 2: 0.2mL in 2.1s
Triggering relay unit 1 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 1
Executing trigger 2/4 for relay unit 1
Executing trigger 3/4 for relay unit 1
Executing trigger 4/4 for relay unit 1
Successfully triggered relay unit 1 4 times
2025-01-25 17:07:17.833749 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:07:17.833906', 'relay_info': 'Successfully triggered relay unit 1 4 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'
Triggering relay unit 2 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 2
Executing trigger 2/4 for relay unit 2
Executing trigger 3/4 for relay unit 2
Executing trigger 4/4 for relay unit 2
Successfully triggered relay unit 2 4 times
2025-01-25 17:07:21.721097 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:07:21.721251', 'relay_info': 'Successfully triggered relay unit 2 4 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'

Staggered Cycle Debug Info:
Current time: 2025-01-25 17:07:44.002657

Cycle Calculation Debug:
Window duration: 300.623 seconds
Max volume to deliver: 2.0ml
Min cycles needed: 10.0
Calculated cycle interval: 30.0623 seconds
Checking active animals at 2025-01-25 17:07:44.002657
Window start: 2025-01-25 17:02:44.451000, Window end: 2025-01-25 17:07:45.074000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 2.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2})])
Animal 1: delivered=1.9999999999999998, target=2.0
Animal 1 is active with 2.220446049250313e-16mL remaining
Animal 2: delivered=1.9999999999999998, target=2.0
Animal 2 is active with 2.220446049250313e-16mL remaining
Active animals: dict_items([('1', {'remaining': 2.220446049250313e-16, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 2.220446049250313e-16, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 1: 2.220446049250313e-16mL in 0s
Scheduled delivery for animal 2: 2.220446049250313e-16mL in 0.6s
Triggering relay unit 1 for 2.220446049250313e-16ml (1 triggers)
Executing trigger 1/1 for relay unit 1
Successfully triggered relay unit 1 1 times
2025-01-25 17:07:45.054672 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:07:45.054815', 'relay_info': 'Successfully triggered relay unit 1 1 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'
Triggering relay unit 2 for 2.220446049250313e-16ml (1 triggers)
Executing trigger 1/1 for relay unit 2
Successfully triggered relay unit 2 1 times
2025-01-25 17:07:45.851859 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-25T17:07:45.852012', 'relay_info': 'Successfully triggered relay unit 2 1 times'}
Delivery error: 'DatabaseHandler' object has no attribute 'log_delivery'

Staggered Cycle Debug Info:
Current time: 2025-01-25 17:08:13.991476

Cycle Calculation Debug:
Window duration: 300.623 seconds
Max volume to deliver: 2.0ml
Min cycles needed: 10.0
Calculated cycle interval: 30.0623 seconds
Checking active animals at 2025-01-25 17:08:13.991476
Window start: 2025-01-25 17:02:44.451000, Window end: 2025-01-25 17:07:45.074000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 2.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 25, 17, 2, 44, 451000), 'end': datetime.datetime(2025, 1, 25, 17, 7, 45, 74000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.2})])
Current time (2025-01-25 17:08:13.991476) is after window end (2025-01-25 17:07:45.074000)
Window time completed
RelayWorker stopped
[DEBUG] Starting cleanup process
[DEBUG] All relays deactivated
[ERROR] An unexpected error occurred during cleanup: wrapped C/C++ object of type QTimer has been deleted