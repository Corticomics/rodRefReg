{'schedule_id': 1, 'name': 'test', 'relay_unit_id': 1, 'water_volume': 3.0, 'start_time': '2024-12-03T16:45:28.522000', 'end_time': '2024-12-03T16:53:29.405000', 'created_by': 1, 'is_super_user': 0, 'delivery_mode': 'staggered', 'animals': [], 'desired_water_outputs': {}, 'instant_deliveries': []}
RRR_Automated_Watering_System/
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
                        trainer_id INTEGER, last_watering TEXT,
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
CREATE TABLE schedule_desired_outputs (
                        schedule_id INTEGER NOT NULL,
                        animal_id INTEGER NOT NULL,
                        desired_output REAL NOT NULL,
                        PRIMARY KEY (schedule_id, animal_id),
                        FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id),
                        FOREIGN KEY(animal_id) REFERENCES animals(animal_id)
                    );
