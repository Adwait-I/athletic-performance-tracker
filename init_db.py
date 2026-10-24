#!/usr/bin/env python3
"""
Database Initialization & Seeder for the Athletic Performance Tracker.

Running this script will:
  1. Drop all existing tables (cascade).
  2. Re-create the full 6-table schema.
  3. Insert 20+ rows of realistic dummy data into every table.
"""

from db import get_db_cursor

# ─────────────────────────────────────────────
# DDL – Schema Creation
# ─────────────────────────────────────────────

DROP_ALL = """
DROP TABLE IF EXISTS WorkoutSets CASCADE;
DROP TABLE IF EXISTS RecoveryLogs CASCADE;
DROP TABLE IF EXISTS Biometrics CASCADE;
DROP TABLE IF EXISTS TrainingSessions CASCADE;
DROP TABLE IF EXISTS Exercises CASCADE;
DROP TABLE IF EXISTS Athletes CASCADE;
"""

CREATE_ATHLETES = """
CREATE TABLE IF NOT EXISTS Athletes (
    athlete_id SERIAL PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    height     DECIMAL(5,2) NOT NULL,
    weight     DECIMAL(5,2) NOT NULL
);
"""

CREATE_TRAINING_SESSIONS = """
CREATE TABLE IF NOT EXISTS TrainingSessions (
    session_id   SERIAL PRIMARY KEY,
    athlete_id   INT NOT NULL REFERENCES Athletes(athlete_id) ON DELETE CASCADE,
    date         DATE NOT NULL,
    session_type VARCHAR(50) NOT NULL,
    duration     INT NOT NULL
);
"""

CREATE_EXERCISES = """
CREATE TABLE IF NOT EXISTS Exercises (
    exercise_id  SERIAL PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    muscle_group VARCHAR(50) NOT NULL,
    mechanics    VARCHAR(50) NOT NULL
);
"""

CREATE_WORKOUT_SETS = """
CREATE TABLE IF NOT EXISTS WorkoutSets (
    set_id      SERIAL PRIMARY KEY,
    session_id  INT NOT NULL REFERENCES TrainingSessions(session_id) ON DELETE CASCADE,
    exercise_id INT NOT NULL REFERENCES Exercises(exercise_id) ON DELETE CASCADE,
    weight      DECIMAL(6,2) NOT NULL,
    reps        INT NOT NULL,
    rpe         INT CHECK (rpe BETWEEN 1 AND 10)
);
"""

CREATE_RECOVERY_LOGS = """
CREATE TABLE IF NOT EXISTS RecoveryLogs (
    recovery_id    SERIAL PRIMARY KEY,
    athlete_id     INT UNIQUE NOT NULL REFERENCES Athletes(athlete_id) ON DELETE CASCADE,
    date           DATE NOT NULL,
    sleep_hours    DECIMAL(4,2) NOT NULL,
    soreness_level INT CHECK (soreness_level BETWEEN 1 AND 10)
);
"""

CREATE_BIOMETRICS = """
CREATE TABLE IF NOT EXISTS Biometrics (
    bio_id     SERIAL PRIMARY KEY,
    athlete_id INT NOT NULL REFERENCES Athletes(athlete_id) ON DELETE CASCADE,
    date       DATE NOT NULL,
    resting_hr INT NOT NULL,
    weight     DECIMAL(5,2) NOT NULL
);
"""

# ─────────────────────────────────────────────
# DML – Seed Data
# ─────────────────────────────────────────────

SEED_ATHLETES = """
INSERT INTO Athletes (name, height, weight) VALUES
('Marcus Thompson',   188.50, 92.30),
('Elena Rodriguez',   170.20, 65.40),
('James Okafor',      195.80, 105.20),
('Sofia Petrov',      165.00, 58.70),
('Daniel Kim',        178.30, 79.50),
('Aisha Johnson',     175.60, 70.20),
('Liam O''Brien',     182.10, 86.40),
('Priya Sharma',      162.50, 55.30),
('Noah Williams',     190.40, 97.80),
('Camila Santos',     168.90, 62.10),
('Ryan Mitchell',     185.20, 88.60),
('Yuki Tanaka',       172.40, 68.90),
('Oliver Grant',      180.00, 82.50),
('Zara Ahmed',        167.30, 60.40),
('Ethan Brooks',      193.60, 100.70),
('Isabella Costa',    169.80, 63.80),
('Carlos Mendez',     176.50, 76.20),
('Fatima Al-Rashid',  164.20, 57.50),
('Lucas Bergström',   187.90, 91.40),
('Maya Patel',        171.00, 66.70);
"""

SEED_EXERCISES = """
INSERT INTO Exercises (name, muscle_group, mechanics) VALUES
('Barbell Back Squat',       'Legs',      'Compound'),
('Conventional Deadlift',    'Back',      'Compound'),
('Bench Press',              'Chest',     'Compound'),
('Overhead Press',           'Shoulders', 'Compound'),
('Barbell Row',              'Back',      'Compound'),
('Romanian Deadlift',        'Legs',      'Compound'),
('Pull-ups',                 'Back',      'Compound'),
('Power Clean',              'Full Body', 'Compound'),
('Front Squat',              'Legs',      'Compound'),
('Incline Dumbbell Press',   'Chest',     'Compound'),
('Bulgarian Split Squat',    'Legs',      'Compound'),
('Lateral Raise',            'Shoulders', 'Isolation'),
('Barbell Curl',             'Arms',      'Isolation'),
('Tricep Dips',              'Arms',      'Compound'),
('Leg Press',                'Legs',      'Compound'),
('Cable Fly',                'Chest',     'Isolation'),
('Hanging Leg Raise',        'Core',      'Isolation'),
('Face Pull',                'Shoulders', 'Isolation'),
('Hip Thrust',               'Legs',      'Compound'),
('Dumbbell Shoulder Press',  'Shoulders', 'Compound');
"""

SEED_TRAINING_SESSIONS = """
INSERT INTO TrainingSessions (athlete_id, date, session_type, duration) VALUES
(1,  '2026-10-01', 'Hypertrophy',      75),
(1,  '2026-10-03', 'Max Strength',     60),
(2,  '2026-10-01', 'Conditioning',     50),
(2,  '2026-10-04', 'Hypertrophy',      65),
(3,  '2026-10-02', 'Max Strength',     80),
(3,  '2026-10-05', 'Explosive Power',  55),
(4,  '2026-10-01', 'Endurance',        90),
(4,  '2026-10-06', 'Hypertrophy',      70),
(5,  '2026-10-03', 'Max Strength',     65),
(5,  '2026-10-07', 'Conditioning',     45),
(6,  '2026-10-02', 'Hypertrophy',      70),
(7,  '2026-10-04', 'Explosive Power',  60),
(8,  '2026-10-05', 'Endurance',        85),
(9,  '2026-10-06', 'Max Strength',     75),
(10, '2026-10-07', 'Hypertrophy',      65),
(11, '2026-10-08', 'Conditioning',     50),
(12, '2026-10-09', 'Max Strength',     70),
(13, '2026-10-10', 'Hypertrophy',      60),
(14, '2026-10-11', 'Endurance',        80),
(15, '2026-10-12', 'Explosive Power',  55);
"""

SEED_WORKOUT_SETS = """
INSERT INTO WorkoutSets (session_id, exercise_id, weight, reps, rpe) VALUES
(1,  1,  120.00, 10, 7),
(1,  6,   80.00, 12, 7),
(1, 11,   40.00, 10, 8),
(2,  1,  160.00,  3, 9),
(2,  2,  180.00,  3, 10),
(3,  8,   60.00,  5, 8),
(3,  7,    0.00, 15, 7),
(4,  3,   45.00,  10, 7),
(4, 10,   20.00,  12, 6),
(5,  2,  220.00,   2, 10),
(5,  5,  140.00,   5, 9),
(6,  8,  100.00,   3, 9),
(6,  9,   90.00,   5, 8),
(7, 19,   60.00,  15, 6),
(7, 15,  120.00,  12, 7),
(8,  1,   70.00,  10, 7),
(8, 16,   12.00,  15, 6),
(9,  3,  100.00,   5, 9),
(9,  4,   70.00,   5, 8),
(10, 7,    0.00,  20, 7),
(10,18,   10.00,  15, 6),
(11, 1,   80.00,  10, 7),
(11,19,   80.00,  12, 7),
(12, 8,   90.00,   3, 9),
(12, 9,   80.00,   5, 8),
(13,15,   90.00,  15, 6),
(13,17,    0.00,  20, 7),
(14, 2,  200.00,   3, 10),
(14, 5,  120.00,   5, 9),
(15, 3,   50.00,  12, 7),
(15,12,    8.00,  15, 6),
(16, 7,    0.00,  12, 7),
(16,18,   12.00,  15, 6),
(17, 1,  140.00,   5, 9),
(17, 6,  100.00,   8, 8),
(18, 3,   90.00,  10, 7),
(18, 4,   60.00,  10, 7),
(19,15,  100.00,  15, 6),
(19,17,    0.00,  20, 7),
(20, 8,  110.00,   3, 9);
"""

SEED_RECOVERY_LOGS = """
INSERT INTO RecoveryLogs (athlete_id, date, sleep_hours, soreness_level) VALUES
(1,  '2026-10-04', 8.00, 3),
(2,  '2026-10-05', 7.00, 6),
(3,  '2026-10-06', 9.00, 4),
(4,  '2026-10-07', 6.80, 5),
(5,  '2026-10-08', 7.50, 4),
(6,  '2026-10-03', 7.80, 5),
(7,  '2026-10-05', 8.20, 6),
(8,  '2026-10-06', 9.20, 2),
(9,  '2026-10-07', 7.00, 7),
(10, '2026-10-08', 6.50, 5),
(11, '2026-10-09', 7.80, 4),
(12, '2026-10-10', 8.50, 6),
(13, '2026-10-11', 7.20, 3),
(14, '2026-10-12', 8.00, 5),
(15, '2026-10-13', 7.50, 7),
(16, '2026-10-14', 8.10, 3),
(17, '2026-10-14', 6.90, 6),
(18, '2026-10-13', 7.40, 4),
(19, '2026-10-14', 8.50, 5),
(20, '2026-10-14', 7.70, 3);
"""

SEED_BIOMETRICS = """
INSERT INTO Biometrics (athlete_id, date, resting_hr, weight) VALUES
(1,  '2026-10-01', 52, 92.10),
(1,  '2026-10-03', 50, 92.30),
(2,  '2026-10-01', 58, 65.20),
(2,  '2026-10-04', 56, 65.40),
(3,  '2026-10-02', 48, 105.50),
(3,  '2026-10-05', 46, 105.20),
(4,  '2026-10-01', 62, 58.50),
(4,  '2026-10-06', 60, 58.70),
(5,  '2026-10-03', 55, 79.30),
(5,  '2026-10-07', 54, 79.50),
(6,  '2026-10-02', 57, 70.00),
(7,  '2026-10-04', 53, 86.20),
(8,  '2026-10-05', 65, 55.10),
(9,  '2026-10-06', 49, 97.60),
(10, '2026-10-07', 60, 62.30),
(11, '2026-10-08', 54, 88.40),
(12, '2026-10-09', 58, 69.10),
(13, '2026-10-10', 56, 82.30),
(14, '2026-10-11', 63, 60.20),
(15, '2026-10-12', 47, 100.50);
"""


def initialize_database():
    """Drop all tables, recreate the schema, and seed with dummy data."""
    print("🗑️  Dropping existing tables...")
    with get_db_cursor() as cur:
        cur.execute(DROP_ALL)
    print("   ✓ Tables dropped.\n")

    print("🏗️  Creating tables...")
    with get_db_cursor() as cur:
        cur.execute(CREATE_ATHLETES)
        cur.execute(CREATE_TRAINING_SESSIONS)
        cur.execute(CREATE_EXERCISES)
        cur.execute(CREATE_WORKOUT_SETS)
        cur.execute(CREATE_RECOVERY_LOGS)
        cur.execute(CREATE_BIOMETRICS)
    print("   ✓ All 6 tables created.\n")

    print("🌱 Seeding data...")
    with get_db_cursor() as cur:
        cur.execute(SEED_ATHLETES)
        print("   ✓ Athletes          – 20 rows")
        cur.execute(SEED_EXERCISES)
        print("   ✓ Exercises         – 20 rows")
        cur.execute(SEED_TRAINING_SESSIONS)
        print("   ✓ TrainingSessions  – 20 rows")
        cur.execute(SEED_WORKOUT_SETS)
        print("   ✓ WorkoutSets       – 40 rows")
        cur.execute(SEED_RECOVERY_LOGS)
        print("   ✓ RecoveryLogs      – 20 rows")
        cur.execute(SEED_BIOMETRICS)
        print("   ✓ Biometrics        – 20 rows")

    print("\n✅ Database initialized successfully!")

    # Verification counts
    with get_db_cursor(commit=False) as cur:
        for table in ["Athletes", "TrainingSessions", "Exercises",
                       "WorkoutSets", "RecoveryLogs", "Biometrics"]:
            cur.execute(f"SELECT COUNT(*) FROM {table};")
            count = cur.fetchone()[0]
            print(f"   {table:25s} → {count} rows")


if __name__ == "__main__":
    initialize_database()
