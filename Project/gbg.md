conelab@raspberrypi:~/Documents/GitHub/new_rrr/RRR/Project $ sudo python3 main.py
QStandardPaths: XDG_RUNTIME_DIR not set, defaulting to '/tmp/runtime-root'
Tables created or confirmed to exist.
Tables created or confirmed to exist.
Running in Guest mode. Displaying all data.
Initialized relay hat 0
Error retrieving all animals: no such column: ID
Traceback (most recent call last):
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/models/database_handler.py", line 323, in get_all_animals
    cursor.execute('SELECT ID, lab_animal_id, name, initial_weight, last_weight, last_weighted FROM animals')
sqlite3.OperationalError: no such column: ID
Error retrieving all animals: no such column: ID
Traceback (most recent call last):
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/models/database_handler.py", line 323, in get_all_animals
    cursor.execute('SELECT ID, lab_animal_id, name, initial_weight, last_weight, last_weighted FROM animals')
sqlite3.OperationalError: no such column: ID
About to load animals for trainer_id: None (type: <class 'NoneType'>)
Error retrieving all animals: no such column: ID
Traceback (most recent call last):
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/models/database_handler.py", line 323, in get_all_animals
    cursor.execute('SELECT ID, lab_animal_id, name, initial_weight, last_weight, last_weighted FROM animals')
sqlite3.OperationalError: no such column: ID


conelab@raspberrypi:~/Documents/GitHub/new_rrr/RRR/Project $ sqlite3 rrr_database.db
SQLite version 3.40.1 2022-12-28 14:03:47
Enter ".help" for usage hints.
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
                        relay_unit_id INTEGER NOT NULL,
                        water_volume REAL NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT NOT NULL,
                        created_by INTEGER NOT NULL,
                        is_super_user BOOLEAN DEFAULT 0,
                        FOREIGN KEY(relay_unit_id) REFERENCES relay_units(relay_unit_id),
                        FOREIGN KEY(created_by) REFERENCES trainers(trainer_id)
                    );
CREATE TABLE schedule_animals (
                        schedule_id INTEGER NOT NULL,
                        animal_id INTEGER NOT NULL,
                        PRIMARY KEY (schedule_id, animal_id),
                        FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id),
                        FOREIGN KEY(animal_id) REFERENCES animals(animal_id)
                    );
CREATE TABLE logs (
                        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        action TEXT NOT NULL,
                        super_user_id INTEGER NOT NULL,
                        details TEXT,
                        FOREIGN KEY(super_user_id) REFERENCES trainers(trainer_id)
                    );
