Error logging delivery: NOT NULL constraint failed: dispensing_history.schedule_id
Traceback (most recent call last):

  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/models/database_handler.py", line 1268, in log_delivery
    cursor.execute('''

sqlite3.IntegrityError: NOT NULL constraint failed: dispensing_history.schedule_id


mouseuser@raspberrypi:~/Documents/GitHub/rodRefReg/Project $ sudo python3 main.py
QStandardPaths: XDG_RUNTIME_DIR not set, defaulting to '/tmp/runtime-root'
Database error during table creation: duplicate column name: cycle_index
Traceback (most recent call last):
  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/models/database_handler.py", line 185, in create_tables
    cursor.execute('''
sqlite3.OperationalError: duplicate column name: cycle_index
Database error during table creation: duplicate column name: cycle_index
Traceback (most recent call last):
  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/models/database_handler.py", line 185, in create_tables
    cursor.execute('''
sqlite3.OperationalError: duplicate column name: cycle_index

Failed to pause schedule: 'RunStopSection' object has no attribute 'schedule_manager

Running program with schedule: test, mode: Staggered
Failed to run program: wrapped C/C++ object of type QThread has been deleted

Logged pump trigger: {'timestamp': '2025-01-29T17:36:59.914151', 'relay_info': 'Program error: wrapped C/C++ object of type QThread has been deleted'}
Error stopping program: wrapped C/C++ object of type QTimer has been deleted


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
Adding staggered schedule: test 1
Animals: [1, 2]
Relay assignments: {'1': 1, '2': 2}
Water outputs: {'1': 3.0, '2': 2.0}

DEBUG INFO:
Schedule: {'schedule_id': 2, 'name': 'test 1', 'water_volume': 5.0, 'start_time': '2025-01-31T12:04:31.073000', 'end_time': '2025-01-31T12:11:32.273000', 'created_by': 1, 'is_super_user': 0, 'delivery_mode': 'staggered', 'cycles_per_day': 1, 'animals': [1, 2], 'desired_water_outputs': {'1': 3.0, '2': 2.0}, 'instant_deliveries': [], 'relay_unit_assignments': {'1': 1, '2': 2}, 'status': 'pending', 'delivered_volumes': {}, 'last_delivery': {}, 'window_data': {}}
Mode: Staggered

Schedule Debug Info:
Desired water outputs: {'1': 3.0, '2': 2.0}
Relay assignments: {'1': 1, '2': 2}

Settings Debug Info:
Settings desired water outputs: {'1': 3.0, '2': 2.0}
Settings relay assignments: {'1': 1, '2': 2}
Starting schedule execution with mode: Staggered, window_start: 1738350271.073, window_end: 1738350692.273
Animals: [1, 2]
Relay assignments: {'1': 1, '2': 2}
Water outputs: {'1': 3.0, '2': 2.0}
Running program with schedule: test 1, mode: Staggered

Worker Settings Debug:
Mode: Staggered
Desired outputs: {'1': 3.0, '2': 2.0}
Relay assignments: {'1': 1, '2': 2}

Program Started
Starting staggered cycle

Staggered Cycle Debug Info:
Current time: 2025-01-31 12:02:48.529410

Cycle Calculation Debug:
Window duration: 421.2 seconds
Max volume to deliver: 3.0ml
Min cycles needed: 15.0
Calculated cycle interval: 28.08 seconds
Initializing animal windows
Relay assignments: {'1': 1, '2': 2}
Desired outputs: {'1': 3.0, '2': 2.0}
Created window for animal 1: {'start': datetime.datetime(2025, 1, 31, 12, 4, 31, 73000), 'end': datetime.datetime(2025, 1, 31, 12, 11, 32, 273000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 3.0, 'volume_per_cycle': 0.2}
Volume per cycle: 0.2ml
Created window for animal 2: {'start': datetime.datetime(2025, 1, 31, 12, 4, 31, 73000), 'end': datetime.datetime(2025, 1, 31, 12, 11, 32, 273000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.13333333333333333}
Volume per cycle: 0.13333333333333333ml
Checking active animals at 2025-01-31 12:02:48.529410
Window start: 2025-01-31 12:04:31.073000, Window end: 2025-01-31 12:11:32.273000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 31, 12, 4, 31, 73000), 'end': datetime.datetime(2025, 1, 31, 12, 11, 32, 273000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 3.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 31, 12, 4, 31, 73000), 'end': datetime.datetime(2025, 1, 31, 12, 11, 32, 273000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.13333333333333333})])
Current time (2025-01-31 12:02:48.529410) is before window start (2025-01-31 12:04:31.073000)

Staggered Cycle Debug Info:
Current time: 2025-01-31 12:04:32.059969

Cycle Calculation Debug:
Window duration: 421.2 seconds
Max volume to deliver: 3.0ml
Min cycles needed: 15.0
Calculated cycle interval: 28.08 seconds
Checking active animals at 2025-01-31 12:04:32.059969
Window start: 2025-01-31 12:04:31.073000, Window end: 2025-01-31 12:11:32.273000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 31, 12, 4, 31, 73000), 'end': datetime.datetime(2025, 1, 31, 12, 11, 32, 273000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 3.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 31, 12, 4, 31, 73000), 'end': datetime.datetime(2025, 1, 31, 12, 11, 32, 273000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.13333333333333333})])
Animal 1: delivered=0, target=3.0
Animal 1 is active with 3.0mL remaining
Animal 2: delivered=0, target=2.0
Animal 2 is active with 2.0mL remaining
Active animals: dict_items([('1', {'remaining': 3.0, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 2.0, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 1: 0.2mL in 0s
Scheduled delivery for animal 2: 0.13333333333333333mL in 2.1s
Triggering relay unit 1 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 1
Executing trigger 2/4 for relay unit 1
Executing trigger 3/4 for relay unit 1
Executing trigger 4/4 for relay unit 1
Successfully triggered relay unit 1 4 times
2025-01-31 12:04:35.895373 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-31T12:04:35.895522', 'relay_info': 'Successfully triggered relay unit 1 4 times'}
Delivered 0.200mL to animal 1 (Total: 0.200mL)
Triggering relay unit 2 for 0.13333333333333333ml (3 triggers)
Executing trigger 1/3 for relay unit 2
Executing trigger 2/3 for relay unit 2
Executing trigger 3/3 for relay unit 2
Successfully triggered relay unit 2 3 times
2025-01-31 12:04:38.799227 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-31T12:04:38.799376', 'relay_info': 'Successfully triggered relay unit 2 3 times'}
Delivered 0.133mL to animal 2 (Total: 0.133mL)

Staggered Cycle Debug Info:
Current time: 2025-01-31 12:04:59.963616

Cycle Calculation Debug:
Window duration: 421.2 seconds
Max volume to deliver: 3.0ml
Min cycles needed: 15.0
Calculated cycle interval: 28.08 seconds
Checking active animals at 2025-01-31 12:04:59.963616
Window start: 2025-01-31 12:04:31.073000, Window end: 2025-01-31 12:11:32.273000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 31, 12, 4, 31, 73000), 'end': datetime.datetime(2025, 1, 31, 12, 11, 32, 273000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 3.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 31, 12, 4, 31, 73000), 'end': datetime.datetime(2025, 1, 31, 12, 11, 32, 273000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.13333333333333333})])
Animal 1: delivered=0.2, target=3.0
Animal 1 is active with 2.8mL remaining
Animal 2: delivered=0.13333333333333333, target=2.0
Animal 2 is active with 1.8666666666666667mL remaining
Active animals: dict_items([('1', {'remaining': 2.8, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 1.8666666666666667, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 1: 0.2mL in 0s
Scheduled delivery for animal 2: 0.13333333333333333mL in 2.1s
Triggering relay unit 1 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 1
Executing trigger 2/4 for relay unit 1
Executing trigger 3/4 for relay unit 1
Executing trigger 4/4 for relay unit 1
Successfully triggered relay unit 1 4 times
2025-01-31 12:05:03.864338 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-31T12:05:03.864492', 'relay_info': 'Successfully triggered relay unit 1 4 times'}
Delivered 0.200mL to animal 1 (Total: 0.400mL)
Triggering relay unit 2 for 0.13333333333333333ml (3 triggers)
Executing trigger 1/3 for relay unit 2
Executing trigger 2/3 for relay unit 2
Executing trigger 3/3 for relay unit 2
Successfully triggered relay unit 2 3 times
2025-01-31 12:05:06.704103 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-31T12:05:06.704256', 'relay_info': 'Successfully triggered relay unit 2 3 times'}
Delivered 0.133mL to animal 2 (Total: 0.267mL)

Staggered Cycle Debug Info:
Current time: 2025-01-31 12:05:27.979383

Cycle Calculation Debug:
Window duration: 421.2 seconds
Max volume to deliver: 3.0ml
Min cycles needed: 15.0
Calculated cycle interval: 28.08 seconds
Checking active animals at 2025-01-31 12:05:27.979383
Window start: 2025-01-31 12:04:31.073000, Window end: 2025-01-31 12:11:32.273000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 31, 12, 4, 31, 73000), 'end': datetime.datetime(2025, 1, 31, 12, 11, 32, 273000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 3.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 31, 12, 4, 31, 73000), 'end': datetime.datetime(2025, 1, 31, 12, 11, 32, 273000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.13333333333333333})])
Animal 1: delivered=0.4, target=3.0
Animal 1 is active with 2.6mL remaining
Animal 2: delivered=0.26666666666666666, target=2.0
Animal 2 is active with 1.7333333333333334mL remaining
Active animals: dict_items([('1', {'remaining': 2.6, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 1.7333333333333334, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 1: 0.2mL in 0s
Scheduled delivery for animal 2: 0.13333333333333333mL in 2.1s
Triggering relay unit 1 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 1
Executing trigger 2/4 for relay unit 1
Executing trigger 3/4 for relay unit 1
Executing trigger 4/4 for relay unit 1
Successfully triggered relay unit 1 4 times
2025-01-31 12:05:31.802190 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-31T12:05:31.802341', 'relay_info': 'Successfully triggered relay unit 1 4 times'}
Delivered 0.200mL to animal 1 (Total: 0.600mL)
Triggering relay unit 2 for 0.13333333333333333ml (3 triggers)
Executing trigger 1/3 for relay unit 2
Executing trigger 2/3 for relay unit 2
Executing trigger 3/3 for relay unit 2
Successfully triggered relay unit 2 3 times
2025-01-31 12:05:34.702827 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-31T12:05:34.703076', 'relay_info': 'Successfully triggered relay unit 2 3 times'}
Delivered 0.133mL to animal 2 (Total: 0.400mL)

Staggered Cycle Debug Info:
Current time: 2025-01-31 12:05:55.964240

Cycle Calculation Debug:
Window duration: 421.2 seconds
Max volume to deliver: 3.0ml
Min cycles needed: 15.0
Calculated cycle interval: 28.08 seconds
Checking active animals at 2025-01-31 12:05:55.964240
Window start: 2025-01-31 12:04:31.073000, Window end: 2025-01-31 12:11:32.273000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 31, 12, 4, 31, 73000), 'end': datetime.datetime(2025, 1, 31, 12, 11, 32, 273000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 3.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 31, 12, 4, 31, 73000), 'end': datetime.datetime(2025, 1, 31, 12, 11, 32, 273000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.13333333333333333})])
Animal 1: delivered=0.6000000000000001, target=3.0
Animal 1 is active with 2.4mL remaining
Animal 2: delivered=0.4, target=2.0
Animal 2 is active with 1.6mL remaining
Active animals: dict_items([('1', {'remaining': 2.4, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 1.6, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 1: 0.2mL in 0s
Scheduled delivery for animal 2: 0.13333333333333333mL in 2.1s
Triggering relay unit 1 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 1
Executing trigger 2/4 for relay unit 1
Executing trigger 3/4 for relay unit 1
Executing trigger 4/4 for relay unit 1
Successfully triggered relay unit 1 4 times
2025-01-31 12:05:59.956681 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-31T12:05:59.956840', 'relay_info': 'Successfully triggered relay unit 1 4 times'}
Delivered 0.200mL to animal 1 (Total: 0.800mL)
Triggering relay unit 2 for 0.13333333333333333ml (3 triggers)
Executing trigger 1/3 for relay unit 2
Executing trigger 2/3 for relay unit 2
Executing trigger 3/3 for relay unit 2
Successfully triggered relay unit 2 3 times
2025-01-31 12:06:02.859843 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-31T12:06:02.860000', 'relay_info': 'Successfully triggered relay unit 2 3 times'}
Delivered 0.133mL to animal 2 (Total: 0.533mL)

Staggered Cycle Debug Info:
Current time: 2025-01-31 12:06:23.980879

Cycle Calculation Debug:
Window duration: 421.2 seconds
Max volume to deliver: 3.0ml
Min cycles needed: 15.0
Calculated cycle interval: 28.08 seconds
Checking active animals at 2025-01-31 12:06:23.980879
Window start: 2025-01-31 12:04:31.073000, Window end: 2025-01-31 12:11:32.273000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 31, 12, 4, 31, 73000), 'end': datetime.datetime(2025, 1, 31, 12, 11, 32, 273000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 3.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 31, 12, 4, 31, 73000), 'end': datetime.datetime(2025, 1, 31, 12, 11, 32, 273000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.13333333333333333})])
Animal 1: delivered=0.8, target=3.0
Animal 1 is active with 2.2mL remaining
Animal 2: delivered=0.5333333333333333, target=2.0
Animal 2 is active with 1.4666666666666668mL remaining
Active animals: dict_items([('1', {'remaining': 2.2, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 1.4666666666666668, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 1: 0.2mL in 0s
Scheduled delivery for animal 2: 0.13333333333333333mL in 2.1s
Triggering relay unit 1 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 1
Executing trigger 2/4 for relay unit 1
Executing trigger 3/4 for relay unit 1
Executing trigger 4/4 for relay unit 1
Successfully triggered relay unit 1 4 times
2025-01-31 12:06:27.955547 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-31T12:06:27.955693', 'relay_info': 'Successfully triggered relay unit 1 4 times'}
Delivered 0.200mL to animal 1 (Total: 1.000mL)
Triggering relay unit 2 for 0.13333333333333333ml (3 triggers)
Executing trigger 1/3 for relay unit 2
Executing trigger 2/3 for relay unit 2
Executing trigger 3/3 for relay unit 2
Successfully triggered relay unit 2 3 times
2025-01-31 12:06:30.849283 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-31T12:06:30.849434', 'relay_info': 'Successfully triggered relay unit 2 3 times'}
Delivered 0.133mL to animal 2 (Total: 0.667mL)

Staggered Cycle Debug Info:
Current time: 2025-01-31 12:06:51.980912

Cycle Calculation Debug:
Window duration: 421.2 seconds
Max volume to deliver: 3.0ml
Min cycles needed: 15.0
Calculated cycle interval: 28.08 seconds
Checking active animals at 2025-01-31 12:06:51.980912
Window start: 2025-01-31 12:04:31.073000, Window end: 2025-01-31 12:11:32.273000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 31, 12, 4, 31, 73000), 'end': datetime.datetime(2025, 1, 31, 12, 11, 32, 273000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 3.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 31, 12, 4, 31, 73000), 'end': datetime.datetime(2025, 1, 31, 12, 11, 32, 273000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.13333333333333333})])
Animal 1: delivered=1.0, target=3.0
Animal 1 is active with 2.0mL remaining
Animal 2: delivered=0.6666666666666666, target=2.0
Animal 2 is active with 1.3333333333333335mL remaining
Active animals: dict_items([('1', {'remaining': 2.0, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 1.3333333333333335, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 1: 0.2mL in 0s
Scheduled delivery for animal 2: 0.13333333333333333mL in 2.1s
Triggering relay unit 1 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 1
Executing trigger 2/4 for relay unit 1
Executing trigger 3/4 for relay unit 1
Executing trigger 4/4 for relay unit 1
Successfully triggered relay unit 1 4 times
2025-01-31 12:06:55.943281 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-31T12:06:55.943427', 'relay_info': 'Successfully triggered relay unit 1 4 times'}
Delivered 0.200mL to animal 1 (Total: 1.200mL)
Triggering relay unit 2 for 0.13333333333333333ml (3 triggers)
Executing trigger 1/3 for relay unit 2
Executing trigger 2/3 for relay unit 2
Executing trigger 3/3 for relay unit 2
Successfully triggered relay unit 2 3 times
2025-01-31 12:06:58.856515 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-31T12:06:58.856671', 'relay_info': 'Successfully triggered relay unit 2 3 times'}
Delivered 0.133mL to animal 2 (Total: 0.800mL)

Staggered Cycle Debug Info:
Current time: 2025-01-31 12:07:19.980330

Cycle Calculation Debug:
Window duration: 421.2 seconds
Max volume to deliver: 3.0ml
Min cycles needed: 15.0
Calculated cycle interval: 28.08 seconds
Checking active animals at 2025-01-31 12:07:19.980330
Window start: 2025-01-31 12:04:31.073000, Window end: 2025-01-31 12:11:32.273000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 31, 12, 4, 31, 73000), 'end': datetime.datetime(2025, 1, 31, 12, 11, 32, 273000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 3.0, 'volume_per_cycle': 0.2}), ('2', {'start': datetime.datetime(2025, 1, 31, 12, 4, 31, 73000), 'end': datetime.datetime(2025, 1, 31, 12, 11, 32, 273000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0, 'volume_per_cycle': 0.13333333333333333})])
Animal 1: delivered=1.2, target=3.0
Animal 1 is active with 1.8mL remaining
Animal 2: delivered=0.7999999999999999, target=2.0
Animal 2 is active with 1.2000000000000002mL remaining
Active animals: dict_items([('1', {'remaining': 1.8, 'last_delivery': None, 'relay_unit': 1}), ('2', {'remaining': 1.2000000000000002, 'last_delivery': None, 'relay_unit': 2})])
Scheduled delivery for animal 1: 0.2mL in 0s
Scheduled delivery for animal 2: 0.13333333333333333mL in 2.1s
Triggering relay unit 1 for 0.2ml (4 triggers)
Executing trigger 1/4 for relay unit 1
Executing trigger 2/4 for relay unit 1
Executing trigger 3/4 for relay unit 1
Executing trigger 4/4 for relay unit 1
Successfully triggered relay unit 1 4 times
2025-01-31 12:07:23.850767 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-31T12:07:23.850978', 'relay_info': 'Successfully triggered relay unit 1 4 times'}
Delivered 0.200mL to animal 1 (Total: 1.400mL)
Triggering relay unit 2 for 0.13333333333333333ml (3 triggers)
Executing trigger 1/3 for relay unit 2
Executing trigger 2/3 for relay unit 2
Executing trigger 3/3 for relay unit 2
Successfully triggered relay unit 2 3 times
2025-01-31 12:07:26.794128 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-01-31T12:07:26.794283', 'relay_info': 'Successfully triggered relay unit 2 3 times'}
Delivered 0.133mL to animal 2 (Total: 0.933mL)z





mouseuser@raspberrypi:~/Documents/GitHub/rodRefReg/Project $ sqlite3 rrr_database.db 
SQLite version 3.40.1 2022-12-28 14:03:47
Enter ".help" for usage hints.
sqlite> .schema 
CREATE TABLE dispensing_history (
                            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            schedule_id INTEGER NOT NULL,
                            animal_id INTEGER NOT NULL,
                            relay_unit_id INTEGER NOT NULL,
                            timestamp TEXT NOT NULL,
                            volume_dispensed REAL NOT NULL,
                            status TEXT NOT NULL,
                            cycle_index INTEGER DEFAULT NULL,
                            FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id),
                            FOREIGN KEY(animal_id) REFERENCES animals(animal_id),
                            FOREIGN KEY(relay_unit_id) REFERENCES relay_units(relay_unit_id)
                        );
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE trainers (
                        trainer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trainer_name TEXT UNIQUE NOT NULL,
                        salt TEXT NOT NULL,
                        password TEXT NOT NULL,
                        role TEXT DEFAULT 'normal'
                    );
CREATE TABLE animals (
                        animal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        lab_animal_id TEXT UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        initial_weight REAL,
                        last_weight REAL,
                        last_weighted TEXT,
                        last_watering TEXT,
                        last_water_volume REAL,
                        trainer_id INTEGER,
                        FOREIGN KEY(trainer_id) REFERENCES trainers(trainer_id)
                    );
CREATE TABLE relay_units (
                        relay_unit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        relay_ids TEXT NOT NULL
                    );
CREATE TABLE schedules (
                        schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        water_volume REAL NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT NOT NULL,
                        created_by INTEGER NOT NULL,
                        is_super_user BOOLEAN DEFAULT 0,
                        delivery_mode TEXT DEFAULT 'staggered',
                        dispensing_status TEXT DEFAULT 'pending',
                        FOREIGN KEY(created_by) REFERENCES trainers(trainer_id)
                    );
CREATE TABLE schedule_animals (
                        schedule_id INTEGER NOT NULL,
                        animal_id INTEGER NOT NULL,
                        relay_unit_id INTEGER,
                        PRIMARY KEY (schedule_id, animal_id),
                        FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id),
                        FOREIGN KEY(animal_id) REFERENCES animals(animal_id),
                        FOREIGN KEY(relay_unit_id) REFERENCES relay_units(relay_unit_id)
                    );
CREATE TABLE schedule_desired_outputs (
                        schedule_id INTEGER NOT NULL,
                        animal_id INTEGER NOT NULL,
                        desired_output REAL NOT NULL,
                        interval_minutes INTEGER DEFAULT 60,
                        volume_per_interval REAL,
                        PRIMARY KEY (schedule_id, animal_id),
                        FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id),
                        FOREIGN KEY(animal_id) REFERENCES animals(animal_id)
                    );
CREATE TABLE schedule_instant_deliveries (
                        delivery_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        schedule_id INTEGER NOT NULL,
                        animal_id INTEGER NOT NULL,
                        delivery_datetime TEXT NOT NULL,
                        water_volume REAL NOT NULL,
                        relay_unit_id INTEGER,
                        completed BOOLEAN DEFAULT 0,
                        FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id),
                        FOREIGN KEY(animal_id) REFERENCES animals(animal_id),
                        FOREIGN KEY(relay_unit_id) REFERENCES relay_units(relay_unit_id)
                    );
CREATE TABLE logs (
                        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        action TEXT NOT NULL,
                        super_user_id INTEGER NOT NULL,
                        details TEXT,
                        FOREIGN KEY(super_user_id) REFERENCES trainers(trainer_id)
                    );
CREATE TABLE schedule_staggered_windows (
                        window_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        schedule_id INTEGER NOT NULL,
                        animal_id INTEGER NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT NOT NULL,
                        target_volume REAL NOT NULL,
                        delivered_volume REAL DEFAULT 0,
                        status TEXT DEFAULT 'pending',
                        FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id),
                        FOREIGN KEY(animal_id) REFERENCES animals(animal_id)
                    );
CREATE TABLE cycle_tracking (
                        tracking_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        schedule_id INTEGER NOT NULL,
                        animal_id INTEGER NOT NULL,
                        cycle_index INTEGER NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT NOT NULL,
                        target_volume REAL NOT NULL,
                        delivered_volume REAL DEFAULT 0,
                        status TEXT DEFAULT 'pending',
                        completed_at TEXT,
                        FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id),
                        FOREIGN KEY(animal_id) REFERENCES animals(animal_id)
                    );
sqlite> SELECT * FROM schedule
   ...> ;
Parse error: no such table: schedule
sqlite> SELECT * FROM schedules;
1|terst|3.0|2025-01-31T11:55:40.011000|2025-01-31T12:02:40.859000|1|0|staggered|pending
2|test 1|5.0|2025-01-31T12:04:31.073000|2025-01-31T12:11:32.273000|1|0|staggered|pending
3|time window debug stag|3.0|2025-01-31T12:22:54.975000|2025-01-31T12:30:58.789000|1|0|staggered|pending
sqlite> SELECT * FROM schedules_staggered_windows;
Parse error: no such table: schedules_staggered_windows
sqlite> SELECT * FROM schedule_staggered_windows;
1|1|1|2025-01-31T11:55:40.011000|2025-01-31T12:02:40.859000|2.0|0.0|pending
2|1|2|2025-01-31T11:55:40.011000|2025-01-31T12:02:40.859000|1.0|0.0|pending
3|2|1|2025-01-31T12:04:31.073000|2025-01-31T12:11:32.273000|3.0|0.0|pending
4|2|2|2025-01-31T12:04:31.073000|2025-01-31T12:11:32.273000|2.0|0.0|pending
5|3|1|2025-01-31T12:22:54.975000|2025-01-31T12:30:58.789000|1.0|0.0|pending
6|3|2|2025-01-31T12:22:54.975000|2025-01-31T12:30:58.789000|2.0|0.0|pending



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
Adding staggered schedule: tesrrrr
Animals: [1, 2]
Relay assignments: {'1': 1, '2': 2}
Water outputs: {'1': 2.0, '2': 4.0}
Error details: Traceback (most recent call last):
  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/ui/schedules_tab.py", line 372, in save_current_schedule
    schedule_id = self.database_handler.add_staggered_schedule(schedule)
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/models/database_handler.py", line 977, in add_staggered_schedule
    window_start = animal_window.get('start', schedule.start_time)
                   ^^^^^^^^^^^^^^^^^
AttributeError: 'list' object has no attribute 'get'
