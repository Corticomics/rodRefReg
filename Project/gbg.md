Authentication result for test: None
Authentication failed: invalid username or password.
Initiating authentication for username: jose
Authenticating username: jose
Retrieved data for jose: (1, 'b8de9ccfdc7a9fb03fd494d50fe328ba', '4f5c7ee47a119fdcd3d70ae30057c9f8357204a6977677030db1e9774bccaed4')
Authentication failed: hashed password does not match.
Authentication result for jose: None
Authentication failed: invalid username or password.

conelab@raspberrypi:~/Documents/GitHub/new_rrr/RRR/Project $ sqlite3 rrr_database.db
SQLite version 3.40.1 2022-12-28 14:03:47
Enter ".help" for usage hints.
sqlite> .schema
CREATE TABLE trainers (
                trainer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                trainer_name TEXT UNIQUE NOT NULL,
                salt TEXT NOT NULL,
                password TEXT NOT NULL
                );
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE animals (
                    ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    lab_animal_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    initial_weight REAL,
                    last_weight REAL,
                    last_weighted TEXT,
                    trainer_id INTEGER,
                    FOREIGN KEY(trainer_id) REFERENCES trainers(trainer_id)
                );
CREATE TABLE schedules (
                    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    relay TEXT NOT NULL,
                    animals TEXT NOT NULL
                );
