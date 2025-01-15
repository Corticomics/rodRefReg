-- Add relay_unit_id to schedule_animals table
ALTER TABLE schedule_animals ADD COLUMN relay_unit_id INTEGER;

-- Add relay_unit_id to schedule_instant_deliveries table
ALTER TABLE schedule_instant_deliveries ADD COLUMN relay_unit_id INTEGER;

-- Remove relay_unit_id from schedules table
CREATE TABLE schedules_new (
    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    water_volume REAL,
    start_time TEXT,
    end_time TEXT,
    created_by INTEGER,
    is_super_user BOOLEAN,
    delivery_mode TEXT DEFAULT 'staggered',
    FOREIGN KEY (created_by) REFERENCES trainers(trainer_id)
);

INSERT INTO schedules_new 
SELECT schedule_id, name, water_volume, start_time, end_time, created_by, is_super_user, delivery_mode 
FROM schedules;

DROP TABLE schedules;
ALTER TABLE schedules_new RENAME TO schedules;