System Messages
Loaded 2 animals for all trainers (guest mode)
Displaying all animals (guest mode)
Loaded 2 animals for all trainers (guest mode)
Initiating authentication for username: admin
Authentication successful.
Retrieved 2 animals from the database for trainer_id 2
Loaded 2 animals for trainer 2
Login successful: {'username': 'admin', 'trainer_id': 2, 'role': 'normal'}
Logged in as: admin
Displaying animals for trainer ID 2
About to load animals for trainer_id: 2 (type: <class 'int'>)
Retrieved 2 animals from the database for trainer_id 2
Loaded 2 animals for trainer ID 2
Schedule object: staggered, st2, 3.0, 2025-01-24T10:42:34, 2025-01-25T10:43:34, 2, False, [1, 2], {'1': 1.0, '2': 2.0}, []
Running program with schedule: st2, mode: Staggered, window_start: 1737740554, window_end: 1737827014
Program Started
Starting staggered cycle
[DEBUG] Current time: 1737740500, Window: 1737740554 - 1737827014
[DEBUG] Scheduling first cycle in 54 seconds
[DEBUG] Current time: 1737740553, Window: 1737740554 - 1737827014
[DEBUG] Scheduling first cycle in 1 seconds
[DEBUG] Current time: 1737740554, Window: 1737740554 - 1737827014
[DEBUG] Starting cleanup process
[DEBUG] All relays deactivated
[DEBUG] All timers stopped
[DEBUG] Worker was already deleted or disconnected: wrapped C/C++ object of type RelayWorker has been deleted
[DEBUG] Cleanup completed. Program ready for the next job.System Messages
Loaded 2 animals for all trainers (guest mode)
Displaying all animals (guest mode)
Loaded 2 animals for all trainers (guest mode)
Initiating authentication for username: admin
Authentication successful.
Retrieved 2 animals from the database for trainer_id 2
Loaded 2 animals for trainer 2
Login successful: {'username': 'admin', 'trainer_id': 2, 'role': 'normal'}
Logged in as: admin
Displaying animals for trainer ID 2
About to load animals for trainer_id: 2 (type: <class 'int'>)
Retrieved 2 animals from the database for trainer_id 2
Loaded 2 animals for trainer ID 2
Schedule object: staggered, st2, 3.0, 2025-01-24T10:42:34, 2025-01-25T10:43:34, 2, False, [1, 2], {'1': 1.0, '2': 2.0}, []
Running program with schedule: st2, mode: Staggered, window_start: 1737740554, window_end: 1737827014
Program Started
Starting staggered cycle
[DEBUG] Current time: 1737740500, Window: 1737740554 - 1737827014
[DEBUG] Scheduling first cycle in 54 seconds
[DEBUG] Current time: 1737740553, Window: 1737740554 - 1737827014
[DEBUG] Scheduling first cycle in 1 seconds
[DEBUG] Current time: 1737740554, Window: 1737740554 - 1737827014
[DEBUG] Starting cleanup process
[DEBUG] All relays deactivated
[DEBUG] All timers stopped
[DEBUG] Worker was already deleted or disconnected: wrapped C/C++ object of type RelayWorker has been deleted
[DEBUG] Cleanup completed. Program ready for the next job.



sqlite> .schema
CREATE TABLE trainers (
                        trainer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trainer_name TEXT UNIQUE NOT NULL,
                        salt TEXT NOT NULL,
                        password TEXT NOT NULL,
                        role TEXT DEFAULT 'normal'
                    );
CREATE TABLE sqlite_sequence(name,seq);
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
CREATE TABLE dispensing_history (
                        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        schedule_id INTEGER NOT NULL,
                        animal_id INTEGER NOT NULL,
                        relay_unit_id INTEGER NOT NULL,
                        timestamp TEXT NOT NULL,
                        volume_dispensed REAL NOT NULL,
                        status TEXT NOT NULL,
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
sqlite> SELECT * FROM schedules;
1|e|3.0|2025-01-23T14:11:00.417000|2025-01-23T14:11:59.729000|2|0|instant|pending
2|22|3.0|2025-01-23T14:10:32.555972|2025-01-23T14:10:32.555972|2|0|staggered|pending
3|q|3.0|2025-01-23T14:19:49|2025-01-23T14:20:49|2|0|staggered|pending
4|ss|5.0|2025-01-23T14:27:22|2025-01-24T14:28:22|2|0|staggered|pending
5|l.|3.0|2025-01-23T14:28:18.286000|2025-01-23T14:28:19.086000|2|0|instant|pending
6|a|3.0|2025-01-23T14:36:35|2025-01-23T14:37:35|2|0|staggered|pending
7|ssssss|3.0|2025-01-23T14:47:26|2025-01-23T14:48:26|2|0|staggered|pending
8|2222|3.0|2025-01-23T14:56:01|2025-01-24T14:56:01|2|0|staggered|pending
9|33333|3.0|2025-01-23T14:58:05|2025-01-23T14:59:05|2|0|staggered|pending
10|cccccc|3.0|2025-01-23T15:00:13|2025-01-23T15:02:13|2|0|staggered|pending
11|ins1|3.0|2025-01-24T10:34:44.102000|2025-01-24T10:35:45.063000|2|0|instant|pending
12|stag1|3.0|2025-01-24T10:41:41|2025-01-25T10:42:41|2|0|staggered|pending
13|st2|3.0|2025-01-24T10:42:34|2025-01-25T10:43:34|2|0|staggered|pending
14|i2|5.0|2025-01-24T10:47:08.813000|2025-01-24T10:47:09.485000|2|0|instant|pending
15|st3|3.0|2025-01-24T11:16:30|2025-01-24T11:17:30|2|0|staggered|pending
16|test|3.0|2025-01-24T11:18:22.456000|2025-01-24T11:19:23.688000|2|0|instant|pending

System Messages
Loaded 2 animals for all trainers (guest mode)
Displaying all animals (guest mode)
Loaded 2 animals for all trainers (guest mode)
Initiating authentication for username: adm
Authentication failed: hashed password does not match.
Authentication failed: invalid username or password.
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
Schedule object: staggered, test, 3.0, 2025-01-25T12:48:00.879000, 2025-01-25T13:48:01.666000, 1, False, [1, 2], {'1': 0.0, '2': 0.0}, []
No delivery windows configured for staggered mode