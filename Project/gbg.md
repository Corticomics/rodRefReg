tarting schedule execution with mode: Staggered, window_start: 1737847021.774, window_end: 1737850502.416
Animals: [1, 2]
Relay assignments: {'1': 2, '2': 1}
Water outputs: {'1': 2.0, '2': 1.0}
Running program with schedule: testekrl, mode: Staggered
Program Started
Starting staggered cycle

Staggered Cycle Debug Info:
Current time: 2025-01-25 16:20:27.004480
Settings: {'mode': 'Staggered', 'window_start': 1737847021.774, 'window_end': 1737850502.416, 'min_trigger_interval_ms': 500, 'cycle_interval': 3600, 'stagger_interval': 0.5, 'water_volume': 6.0, 'relay_unit_assignments': {'1': 2, '2': 1}}
Initializing animal windows
Relay assignments: {'1': 2, '2': 1}
Desired outputs: {}
Created window for animal 1: {'start': datetime.datetime(2025, 1, 25, 16, 17, 1, 774000), 'end': datetime.datetime(2025, 1, 25, 17, 15, 2, 416000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 0.0}
Created window for animal 2: {'start': datetime.datetime(2025, 1, 25, 16, 17, 1, 774000), 'end': datetime.datetime(2025, 1, 25, 17, 15, 2, 416000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 0.0}
Checking active animals at 2025-01-25 16:20:27.004480
Window start: 2025-01-25 16:17:01.774000, Window end: 2025-01-25 17:15:02.416000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 25, 16, 17, 1, 774000), 'end': datetime.datetime(2025, 1, 25, 17, 15, 2, 416000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 0.0}), ('2', {'start': datetime.datetime(2025, 1, 25, 16, 17, 1, 774000), 'end': datetime.datetime(2025, 1, 25, 17, 15, 2, 416000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 0.0})])
Animal 1: delivered=0, target=0.0
Animal 2: delivered=0, target=0.0
Active animals: dict_items([])
No active animals in current time window
WARNING:root:No active animals found
