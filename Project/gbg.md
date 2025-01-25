DEBUG INFO:
Schedule: {'schedule_id': 17, 'name': 'grahhhhhhh', 'water_volume': 12.0, 'start_time': '2025-01-25T16:40:07.922000', 'end_time': '2025-01-25T16:45:08.609000', 'created_by': 1, 'is_super_user': 0, 'delivery_mode': 'staggered', 'cycles_per_day': 1, 'animals': [1, 2], 'desired_water_outputs': {'1': 2.0, '2': 4.0}, 'instant_deliveries': [], 'relay_unit_assignments': {'1': 2, '2': 1}, 'status': 'pending', 'delivered_volumes': {}, 'last_delivery': {}, 'window_data': {}}
Mode: Staggered

Schedule Debug Info:
Desired water outputs: {'1': 2.0, '2': 4.0}
Relay assignments: {'1': 2, '2': 1}

Settings Debug Info:
Settings desired water outputs: {'1': 2.0, '2': 4.0}
Settings relay assignments: {'1': 2, '2': 1}
Starting schedule execution with mode: Staggered, window_start: 1737848407.922, window_end: 1737848708.609
Animals: [1, 2]
Relay assignments: {'1': 2, '2': 1}
Water outputs: {'1': 2.0, '2': 4.0}
Running program with schedule: grahhhhhhh, mode: Staggered

Worker Settings Debug:
Mode: Staggered
Desired outputs: {'1': 2.0, '2': 4.0}
Relay assignments: {'1': 2, '2': 1}

Program Started
Starting staggered cycle

Staggered Cycle Debug Info:
Current time: 2025-01-25 16:37:26.407293
Settings: {'mode': 'Staggered', 'window_start': 1737848407.922, 'window_end': 1737848708.609, 'min_trigger_interval_ms': 500, 'database_handler': <models.database_handler.DatabaseHandler object at 0x7fabb85c50>, 'pump_controller': None, 'cycle_interval': 3600, 'stagger_interval': 0.5, 'water_volume': 12.0, 'relay_unit_assignments': {'1': 2, '2': 1}, 'desired_water_outputs': {'1': 2.0, '2': 4.0}}
Initializing animal windows
Relay assignments: {'1': 2, '2': 1}
Desired outputs: {'1': 2.0, '2': 4.0}
Created window for animal 1: {'start': datetime.datetime(2025, 1, 25, 16, 40, 7, 922000), 'end': datetime.datetime(2025, 1, 25, 16, 45, 8, 609000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0}
Created window for animal 2: {'start': datetime.datetime(2025, 1, 25, 16, 40, 7, 922000), 'end': datetime.datetime(2025, 1, 25, 16, 45, 8, 609000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 4.0}
Checking active animals at 2025-01-25 16:37:26.407293
Window start: 2025-01-25 16:40:07.922000, Window end: 2025-01-25 16:45:08.609000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 25, 16, 40, 7, 922000), 'end': datetime.datetime(2025, 1, 25, 16, 45, 8, 609000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0}), ('2', {'start': datetime.datetime(2025, 1, 25, 16, 40, 7, 922000), 'end': datetime.datetime(2025, 1, 25, 16, 45, 8, 609000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 4.0})])
Current time (2025-01-25 16:37:26.407293) is before window start (2025-01-25 16:40:07.922000)

Staggered Cycle Debug Info:
Current time: 2025-01-25 16:40:07.994130
Settings: {'mode': 'Staggered', 'window_start': 1737848407.922, 'window_end': 1737848708.609, 'min_trigger_interval_ms': 500, 'database_handler': <models.database_handler.DatabaseHandler object at 0x7fabb85c50>, 'pump_controller': None, 'cycle_interval': 3600, 'stagger_interval': 0.5, 'water_volume': 12.0, 'relay_unit_assignments': {'1': 2, '2': 1}, 'desired_water_outputs': {'1': 2.0, '2': 4.0}}
Checking active animals at 2025-01-25 16:40:07.994130
Window start: 2025-01-25 16:40:07.922000, Window end: 2025-01-25 16:45:08.609000
Animal windows: dict_items([('1', {'start': datetime.datetime(2025, 1, 25, 16, 40, 7, 922000), 'end': datetime.datetime(2025, 1, 25, 16, 45, 8, 609000), 'last_delivery': None, 'relay_unit': 2, 'target_volume': 2.0}), ('2', {'start': datetime.datetime(2025, 1, 25, 16, 40, 7, 922000), 'end': datetime.datetime(2025, 1, 25, 16, 45, 8, 609000), 'last_delivery': None, 'relay_unit': 1, 'target_volume': 4.0})])
Animal 1: delivered=0, target=2.0
Animal 1 is active with 2.0mL remaining
Animal 2: delivered=0, target=4.0
Animal 2 is active with 4.0mL remaining
Active animals: dict_items([('1', {'remaining': 2.0, 'last_delivery': None, 'relay_unit': 2}), ('2', {'remaining': 4.0, 'last_delivery': None, 'relay_unit': 1})])
Scheduling delivery for animal 1: 0.2mL in 0ms
Scheduling delivery for animal 2: 0.2mL in 1000ms
Scheduling next cycle in 3600.0 seconds
sys:1: RuntimeWarning: coroutine 'RelayWorker.execute_delivery' was never awaited
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
