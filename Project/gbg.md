-- Add role column to trainers table
ALTER TABLE trainers ADD COLUMN role TEXT DEFAULT 'normal';

-- Create relay_units table
CREATE TABLE IF NOT EXISTS relay_units (
    relay_unit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    relay_ids TEXT NOT NULL
);

-- Modify schedules table
DROP TABLE IF EXISTS schedules;
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

-- Create schedule_animals table
CREATE TABLE IF NOT EXISTS schedule_animals (
    schedule_id INTEGER NOT NULL,
    animal_id INTEGER NOT NULL,
    PRIMARY KEY (schedule_id, animal_id),
    FOREIGN KEY(schedule_id) REFERENCES schedules(schedule_id),
    FOREIGN KEY(animal_id) REFERENCES animals(animal_id)
);

-- Create logs table
CREATE TABLE IF NOT EXISTS logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,
    super_user_id INTEGER NOT NULL,
    details TEXT,
    FOREIGN KEY(super_user_id) REFERENCES trainers(trainer_id)
);