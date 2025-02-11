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
save_current_schedule: adding instant delivery for animal 1 at 2025-02-11 13:12:20.965000 with volume 1.0
save_current_schedule: adding instant deliveries for unit 2
save_current_schedule: adding instant delivery for animal 2 at 2025-02-11 13:12:22.751000 with volume 2.0
save_current_schedule: adding instant schedule with details:<models.Schedule.Schedule object at 0x7f8ca4ab10>

DEBUG INFO:
Schedule: {'schedule_id': 10, 'name': '2', 'water_volume': 3.0, 'start_time': '2025-02-11T13:12:20.965000', 'end_time': '2025-02-11T13:12:22.751000', 'created_by': 1, 'is_super_user': 0, 'delivery_mode': 'instant', 'cycles_per_day': 1, 'animals': [1, 2], 'desired_water_outputs': {}, 'window_data': {}, 'instant_deliveries': [{'animal_id': 1, 'datetime': datetime.datetime(2025, 2, 11, 13, 12, 20, 965000), 'volume': 1.0, 'relay_unit_id': 1}, {'animal_id': 2, 'datetime': datetime.datetime(2025, 2, 11, 13, 12, 22, 751000), 'volume': 2.0, 'relay_unit_id': 2}], 'relay_unit_assignments': {'1': 1, '2': 2}, 'status': 'pending', 'delivered_volumes': {}, 'last_delivery': {}}
Mode: Instant

Schedule Debug Info:
Desired water outputs: {}
Relay assignments: {'1': 1, '2': 2}

Settings Debug Info:
Settings desired water outputs: {}
Settings relay assignments: {'1': 1, '2': 2}
Running program with schedule: 2, mode: Instant
Failed to run program: 'ProjectsController' object has no attribute 'pump_controller'
2025-02-11 13:10:49.010161 - Failed to send Slack message: not_authed
Logged pump trigger: {'timestamp': '2025-02-11T13:10:49.010989', 'relay_info': "Program error: 'ProjectsController' object has no attribute 'pump_controller'"}