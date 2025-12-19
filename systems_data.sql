-- =====================================================
-- EVE Wargames - Systems Data Initialization
-- =====================================================
-- This script populates the database with systems data
-- extracted from the frontend mapSystems.ts file
-- =====================================================

-- Start transaction
BEGIN;

-- Create factions table if it doesn't exist
CREATE TABLE IF NOT EXISTS factions (
    faction_id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    ticker VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create systems table if it doesn't exist
CREATE TABLE IF NOT EXISTS systems (
    system_id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    security_status REAL NOT NULL,
    controlling_faction_id INTEGER REFERENCES factions(faction_id),
    contested INTEGER DEFAULT 0,
    capture_percent REAL DEFAULT 0.0,
    advantage_percent REAL DEFAULT 0.0,
    minmatar_advantage REAL DEFAULT 0.0,
    amarr_advantage REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create system_snapshots table if it doesn't exist
CREATE TABLE IF NOT EXISTS system_snapshots (
    id SERIAL PRIMARY KEY,
    system_id INTEGER REFERENCES systems(system_id),
    controlling_faction_id INTEGER REFERENCES factions(faction_id),
    contested INTEGER DEFAULT 0,
    capture_percent REAL DEFAULT 0.0,
    advantage_percent REAL DEFAULT 0.0,
    minmatar_advantage REAL DEFAULT 0.0,
    amarr_advantage REAL DEFAULT 0.0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert faction data
INSERT INTO factions (faction_id, name, ticker) VALUES
(500002, 'Minmatar Republic', 'MIN'),
(500003, 'Amarr Empire', 'AMR')
ON CONFLICT (faction_id) DO UPDATE SET
    name = EXCLUDED.name,
    ticker = EXCLUDED.ticker,
    updated_at = CURRENT_TIMESTAMP;

-- Insert systems data (extracted from frontend/src/data/mapSystems.ts)
INSERT INTO systems (system_id, name, security_status, controlling_faction_id, contested, capture_percent, advantage_percent, minmatar_advantage, amarr_advantage) VALUES
(30002056, 'Resbroko', 0.4, 500002, 0, 75.2, 68.3, 68.3, 31.7),
(30002057, 'Hadozeko', 0.3, 500002, 1, 45.8, 52.1, 52.1, 47.9),
(30002058, 'Ardar', 0.5, 500002, 0, 82.1, 71.4, 71.4, 28.6),
(30002059, 'Auner', 0.2, 500002, 1, 38.9, 43.2, 43.2, 56.8),
(30002060, 'Evati', 0.3, 500003, 1, 62.4, 58.7, 41.3, 58.7),
(30002061, 'Ofstold', 0.4, 500002, 0, 78.6, 69.8, 69.8, 30.2),
(30002062, 'Todifrauan', 0.6, 500003, 0, 85.3, 73.9, 26.1, 73.9),
(30002063, 'Helgatild', 0.4, 500003, 1, 54.7, 61.2, 38.8, 61.2),
(30002064, 'Arnstur', 0.5, 500003, 0, 79.1, 70.5, 29.5, 70.5),
(30002065, 'Lasleinur', 0.3, 500003, 1, 41.6, 48.3, 51.7, 48.3),
(30002066, 'Arnher', 0.4, 500002, 0, 73.8, 67.1, 67.1, 32.9),
(30002067, 'Brin', 0.3, 500002, 1, 49.2, 55.6, 55.6, 44.4),
(30002082, 'Floseswin', 0.4, 500002, 0, 76.4, 68.9, 68.9, 31.1),
(30002083, 'Uisper', 0.5, 500002, 0, 81.7, 72.3, 72.3, 27.7),
(30002084, 'Aset', 0.3, 500002, 1, 44.1, 51.8, 51.8, 48.2),
(30002085, 'Eytjangard', 0.4, 500002, 0, 77.9, 69.6, 69.6, 30.4),
(30002086, 'Turnur', 0.2, 500002, 1, 36.5, 42.1, 42.1, 57.9),
(30002087, 'Isbrabata', 0.3, 500002, 1, 47.8, 54.3, 54.3, 45.7),
(30002088, 'Vimeini', 0.4, 500002, 0, 74.6, 67.8, 67.8, 32.2),
(30002089, 'Avenod', 0.5, 500002, 0, 80.3, 71.1, 71.1, 28.9),
(30002090, 'Frerstorn', 0.3, 500002, 1, 46.7, 53.4, 53.4, 46.6),
(30002091, 'Ontorn', 0.4, 500002, 0, 75.9, 68.7, 68.7, 31.3),
(30002092, 'Sirekur', 0.5, 500002, 0, 83.2, 72.8, 72.8, 27.2),
(30002093, 'Gebuladi', 0.3, 500002, 1, 43.4, 50.9, 50.9, 49.1),
(30002094, 'Ebolfer', 0.4, 500002, 0, 76.8, 69.2, 69.2, 30.8),
(30002095, 'Eszur', 0.2, 500002, 1, 39.7, 44.8, 44.8, 55.2),
(30002096, 'Hofjaldgund', 0.3, 500003, 1, 58.1, 62.4, 37.6, 62.4),
(30002097, 'Klogori', 0.4, 500002, 0, 77.3, 69.4, 69.4, 30.6),
(30002098, 'Orfrold', 0.5, 500002, 0, 82.6, 72.6, 72.6, 27.4),
(30002099, 'Egmar', 0.3, 500002, 1, 45.3, 52.7, 52.7, 47.3),
(30002100, 'Taff', 0.4, 500002, 0, 74.1, 67.5, 67.5, 32.5),
(30002101, 'Ualkin', 0.5, 500002, 0, 81.4, 71.8, 71.8, 28.2),
(30002102, 'Gukarla', 0.3, 500002, 1, 42.9, 50.4, 50.4, 49.6),
(30002514, 'Bosboger', 0.4, 500002, 0, 76.1, 68.5, 68.5, 31.5),
(30002516, 'Lulm', 0.5, 500002, 0, 83.7, 73.1, 73.1, 26.9),
(30002517, 'Gulmorogod', 0.3, 500002, 1, 44.8, 52.3, 52.3, 47.7),
(30002537, 'Amamake', 0.4, 500002, 1, 65.3, 59.8, 59.8, 40.2),
(30002538, 'Vard', 0.3, 500003, 1, 56.7, 61.9, 38.1, 61.9),
(30002539, 'Siseide', 0.4, 500002, 0, 73.4, 67.2, 67.2, 32.8),
(30002540, 'Lantorn', 0.5, 500002, 0, 80.8, 71.6, 71.6, 28.4),
(30002541, 'Dal', 0.3, 500002, 1, 48.6, 54.9, 54.9, 45.1),
(30002542, 'Auga', 0.4, 500002, 0, 75.7, 68.4, 68.4, 31.6),
(30002543, 'Hrober', 0.5, 500002, 0, 82.9, 72.9, 72.9, 27.1),
(30002544, 'Oddelulf', 0.3, 500002, 1, 41.2, 47.8, 47.8, 52.2),
(30002545, 'Isbrabata', 0.4, 500002, 0, 77.6, 69.3, 69.3, 30.7),
(30002546, 'Hadozeko', 0.5, 500002, 0, 84.1, 73.4, 73.4, 26.6),
(30002547, 'Lamaa', 0.3, 500003, 1, 53.9, 60.7, 39.3, 60.7),
(30002548, 'Oyonata', 0.4, 500003, 0, 78.4, 70.1, 29.9, 70.1),
(30002549, 'Sosala', 0.5, 500003, 0, 85.6, 74.2, 25.8, 74.2),
(30002550, 'Kamela', 0.3, 500003, 1, 52.4, 59.3, 40.7, 59.3),
(30002551, 'Kourmonen', 0.4, 500003, 0, 79.7, 70.8, 29.2, 70.8),
(30002552, 'Huola', 0.5, 500003, 0, 86.2, 74.7, 25.3, 74.7),
(30002553, 'Sahtogas', 0.3, 500003, 1, 51.1, 58.1, 41.9, 58.1),
(30002554, 'Roushzar', 0.4, 500003, 0, 78.9, 70.4, 29.6, 70.4),
(30002555, 'Sosan', 0.5, 500003, 0, 85.8, 74.4, 25.6, 74.4),
(30002556, 'Tzvi', 0.3, 500003, 1, 50.6, 57.7, 42.3, 57.7)
ON CONFLICT (system_id) DO UPDATE SET
    name = EXCLUDED.name,
    security_status = EXCLUDED.security_status,
    controlling_faction_id = EXCLUDED.controlling_faction_id,
    contested = EXCLUDED.contested,
    capture_percent = EXCLUDED.capture_percent,
    advantage_percent = EXCLUDED.advantage_percent,
    minmatar_advantage = EXCLUDED.minmatar_advantage,
    amarr_advantage = EXCLUDED.amarr_advantage,
    updated_at = CURRENT_TIMESTAMP;

-- Create initial system snapshots for trend data
INSERT INTO system_snapshots (system_id, controlling_faction_id, contested, capture_percent, advantage_percent, minmatar_advantage, amarr_advantage, timestamp)
SELECT 
    system_id,
    controlling_faction_id,
    contested,
    capture_percent,
    advantage_percent,
    minmatar_advantage,
    amarr_advantage,
    CURRENT_TIMESTAMP
FROM systems;

-- Commit the transaction
COMMIT;

-- Display summary
SELECT 
    'Systems initialized' as status,
    COUNT(*) as system_count
FROM systems;

SELECT 
    'Snapshots created' as status,
    COUNT(*) as snapshot_count
FROM system_snapshots;

-- Verify Amamake specifically
SELECT 
    'Amamake verification' as status,
    system_id,
    name,
    controlling_faction_id,
    contested,
    capture_percent
FROM systems 
WHERE system_id = 30002537;

