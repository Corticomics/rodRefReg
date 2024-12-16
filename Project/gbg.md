
conelab-rrr2@raspberrypi:~/Documents/GitHub/rodRefReg/Project $ sqlite3 rrr_database.db
SQLite version 3.40.1 2022-12-28 14:03:47
Enter ".help" for usage hints.
sqlite> SELECT * FROM schedules
   ...> ;
1|test|1|3.0|2024-12-15T19:02:18.860000|2025-12-15T19:03:28.722000|1|0|instant|pending
2|test2|1|0.0|2024-12-15T19:02:23.988557|2024-12-15T19:02:23.988568|1|0|instant|pending
sqlite> SELECT * FROM schedule_instant_delivery;
Parse error: no such table: schedule_instant_delivery
sqlite> SELECT * FROM schedule_instant_deliveries;
1|1|1|2024-12-15 19:02:18.860000|1.0|0
2|1|2|2025-12-15 19:03:28.722000|2.0|0


Relay data for unit 1: {'animals': [<models.animal.Animal object at 0x7fae51e950>], 'desired_water_output': {'1': 0.0}, 'delivery_mode': 'instant', 'delivery_schedule': [{'datetime': datetime.datetime(2024, 12, 15, 19, 21, 4, 971000), 'volume': 1.0}]}
Relay data for unit 2: {'animals': [<models.animal.Animal object at 0x7fae51e990>], 'desired_water_output': {'2': 0.0}, 'delivery_mode': 'instant', 'delivery_schedule': [{'datetime': datetime.datetime(2024, 12, 15, 19, 21, 5, 747000), 'volume': 2.0}]}
Relay data for unit 3: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 4: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 5: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 6: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 7: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
Relay data for unit 8: {'animals': [], 'desired_water_output': {}, 'delivery_mode': 'instant', 'delivery_schedule': []}
save_current_schedule: adding instant deliveries for unit 1
save_current_schedule: adding instant delivery for animal 1 at 2024-12-15 19:21:04.971000 with volume 1.0
save_current_schedule: adding instant deliveries for unit 2
save_current_schedule: adding instant delivery for animal 2 at 2024-12-15 19:21:05.747000 with volume 2.0
Schedule object: instant, test1, 3.0, 2024-12-15T19:21:04.971000, 2024-12-15T19:21:05.747000, 1, False, [], {}, [{'animal_id': 1, 'datetime': datetime.datetime(2024, 12, 15, 19, 21, 4, 971000), 'volume': 1.0}, {'animal_id': 2, 'datetime': datetime.datetime(2024, 12, 15, 19, 21, 5, 747000), 'volume': 2.0}]
Schedule 'test1' added with ID: 3



Dropped schedule in ScheduleDropArea:

{'schedule_id': 3, 'name': 'test1', 'relay_unit_id': 1, 'water_volume': 3.0, 'start_time': '2024-12-15T19:21:04.971000', 'end_time': '2024-12-15T19:21:05.747000', 'created_by': 1, 'is_super_user': 0, 'delivery_mode': 'staggered', 'animals': [], 'desired_water_outputs': {}, 'instant_deliveries': []}