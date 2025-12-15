-- =====================================================
-- EVE Wargames - Killmail Tables Migration
-- =====================================================
-- This script creates all necessary tables for Zkillboard
-- killmail data integration and faction warfare analytics
-- =====================================================

-- Start transaction
BEGIN;

-- =====================================================
-- Entity Tables (Players, Corporations, Alliances)
-- =====================================================

-- Create players table for EVE character tracking
CREATE TABLE IF NOT EXISTS players (
    character_id BIGINT PRIMARY KEY,
    character_name VARCHAR(255) NOT NULL,
    corporation_id BIGINT,
    alliance_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create corporations table
CREATE TABLE IF NOT EXISTS corporations (
    corporation_id BIGINT PRIMARY KEY,
    corporation_name VARCHAR(255) NOT NULL,
    ticker VARCHAR(10),
    alliance_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create alliances table
CREATE TABLE IF NOT EXISTS alliances (
    alliance_id BIGINT PRIMARY KEY,
    alliance_name VARCHAR(255) NOT NULL,
    ticker VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- Killmail Data Table
-- =====================================================

-- Create zkillboard_killmails table for individual killmail records
CREATE TABLE IF NOT EXISTS zkillboard_killmails (
    id SERIAL PRIMARY KEY,
    killmail_id BIGINT UNIQUE NOT NULL,
    killmail_hash VARCHAR(255) NOT NULL,
    system_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    
    -- Victim information
    victim_character_id BIGINT,
    victim_corporation_id BIGINT,
    victim_alliance_id BIGINT,
    victim_faction_id INTEGER,
    
    -- Attacker information (final blow)
    attacker_character_id BIGINT,
    attacker_corporation_id BIGINT,
    attacker_alliance_id BIGINT,
    attacker_faction_id INTEGER,
    
    -- Kill value
    total_value BIGINT DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_zkillboard_killmails_system 
        FOREIGN KEY (system_id) REFERENCES systems(system_id),
    CONSTRAINT fk_zkillboard_killmails_victim_character 
        FOREIGN KEY (victim_character_id) REFERENCES players(character_id),
    CONSTRAINT fk_zkillboard_killmails_victim_corporation 
        FOREIGN KEY (victim_corporation_id) REFERENCES corporations(corporation_id),
    CONSTRAINT fk_zkillboard_killmails_victim_alliance 
        FOREIGN KEY (victim_alliance_id) REFERENCES alliances(alliance_id),
    CONSTRAINT fk_zkillboard_killmails_attacker_character 
        FOREIGN KEY (attacker_character_id) REFERENCES players(character_id),
    CONSTRAINT fk_zkillboard_killmails_attacker_corporation 
        FOREIGN KEY (attacker_corporation_id) REFERENCES corporations(corporation_id),
    CONSTRAINT fk_zkillboard_killmails_attacker_alliance 
        FOREIGN KEY (attacker_alliance_id) REFERENCES alliances(alliance_id)
);

-- =====================================================
-- Aggregated Statistics Tables
-- =====================================================

-- Create system_kill_stats table for system-wide kill statistics
CREATE TABLE IF NOT EXISTS system_kill_stats (
    id SERIAL PRIMARY KEY,
    system_id INTEGER NOT NULL,
    time_window_start TIMESTAMP NOT NULL,
    time_window_end TIMESTAMP NOT NULL,
    
    -- Overall statistics
    total_kills INTEGER DEFAULT 0,
    total_isk_killed BIGINT DEFAULT 0,
    
    -- Minmatar faction statistics (faction_id: 500002)
    minmatar_kills INTEGER DEFAULT 0,
    minmatar_losses INTEGER DEFAULT 0,
    minmatar_isk_killed BIGINT DEFAULT 0,
    minmatar_isk_lost BIGINT DEFAULT 0,
    
    -- Amarr faction statistics (faction_id: 500003)
    amarr_kills INTEGER DEFAULT 0,
    amarr_losses INTEGER DEFAULT 0,
    amarr_isk_killed BIGINT DEFAULT 0,
    amarr_isk_lost BIGINT DEFAULT 0,
    
    -- Participation metrics
    unique_players INTEGER DEFAULT 0,
    unique_corporations INTEGER DEFAULT 0,
    unique_alliances INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_system_kill_stats_system 
        FOREIGN KEY (system_id) REFERENCES systems(system_id),
    
    -- Unique constraint to prevent duplicate time windows
    CONSTRAINT uk_system_kill_stats_time_window 
        UNIQUE(system_id, time_window_start, time_window_end)
);

-- Create player_kill_stats table for per-player activity tracking
CREATE TABLE IF NOT EXISTS player_kill_stats (
    id SERIAL PRIMARY KEY,
    system_id INTEGER NOT NULL,
    character_id BIGINT NOT NULL,
    time_window_start TIMESTAMP NOT NULL,
    time_window_end TIMESTAMP NOT NULL,
    
    -- Player statistics
    kills INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    isk_killed BIGINT DEFAULT 0,
    isk_lost BIGINT DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_player_kill_stats_system 
        FOREIGN KEY (system_id) REFERENCES systems(system_id),
    CONSTRAINT fk_player_kill_stats_character 
        FOREIGN KEY (character_id) REFERENCES players(character_id),
    
    -- Unique constraint to prevent duplicate records
    CONSTRAINT uk_player_kill_stats_time_window 
        UNIQUE(system_id, character_id, time_window_start, time_window_end)
);

-- Create corporation_kill_stats table for per-corporation activity tracking
CREATE TABLE IF NOT EXISTS corporation_kill_stats (
    id SERIAL PRIMARY KEY,
    system_id INTEGER NOT NULL,
    corporation_id BIGINT NOT NULL,
    time_window_start TIMESTAMP NOT NULL,
    time_window_end TIMESTAMP NOT NULL,
    
    -- Corporation statistics
    kills INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    isk_killed BIGINT DEFAULT 0,
    isk_lost BIGINT DEFAULT 0,
    unique_players INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_corporation_kill_stats_system 
        FOREIGN KEY (system_id) REFERENCES systems(system_id),
    CONSTRAINT fk_corporation_kill_stats_corporation 
        FOREIGN KEY (corporation_id) REFERENCES corporations(corporation_id),
    
    -- Unique constraint to prevent duplicate records
    CONSTRAINT uk_corporation_kill_stats_time_window 
        UNIQUE(system_id, corporation_id, time_window_start, time_window_end)
);

-- Create alliance_kill_stats table for per-alliance activity tracking
CREATE TABLE IF NOT EXISTS alliance_kill_stats (
    id SERIAL PRIMARY KEY,
    system_id INTEGER NOT NULL,
    alliance_id BIGINT NOT NULL,
    time_window_start TIMESTAMP NOT NULL,
    time_window_end TIMESTAMP NOT NULL,
    
    -- Alliance statistics
    kills INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    isk_killed BIGINT DEFAULT 0,
    isk_lost BIGINT DEFAULT 0,
    unique_players INTEGER DEFAULT 0,
    unique_corporations INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_alliance_kill_stats_system 
        FOREIGN KEY (system_id) REFERENCES systems(system_id),
    CONSTRAINT fk_alliance_kill_stats_alliance 
        FOREIGN KEY (alliance_id) REFERENCES alliances(alliance_id),
    
    -- Unique constraint to prevent duplicate records
    CONSTRAINT uk_alliance_kill_stats_time_window 
        UNIQUE(system_id, alliance_id, time_window_start, time_window_end)
);

-- =====================================================
-- Performance Indexes
-- =====================================================

-- Indexes for zkillboard_killmails table
CREATE INDEX IF NOT EXISTS idx_zkillboard_killmails_system_timestamp 
    ON zkillboard_killmails(system_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_zkillboard_killmails_attacker_faction 
    ON zkillboard_killmails(attacker_faction_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_zkillboard_killmails_victim_faction 
    ON zkillboard_killmails(victim_faction_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_zkillboard_killmails_killmail_id 
    ON zkillboard_killmails(killmail_id);

-- Indexes for system_kill_stats table
CREATE INDEX IF NOT EXISTS idx_system_kill_stats_system_time 
    ON system_kill_stats(system_id, time_window_start);

CREATE INDEX IF NOT EXISTS idx_system_kill_stats_time_range 
    ON system_kill_stats(time_window_start, time_window_end);

-- Indexes for player_kill_stats table
CREATE INDEX IF NOT EXISTS idx_player_kill_stats_system_time 
    ON player_kill_stats(system_id, time_window_start);

CREATE INDEX IF NOT EXISTS idx_player_kill_stats_character_time 
    ON player_kill_stats(character_id, time_window_start);

-- Indexes for corporation_kill_stats table
CREATE INDEX IF NOT EXISTS idx_corporation_kill_stats_system_time 
    ON corporation_kill_stats(system_id, time_window_start);

CREATE INDEX IF NOT EXISTS idx_corporation_kill_stats_corporation_time 
    ON corporation_kill_stats(corporation_id, time_window_start);

-- Indexes for alliance_kill_stats table
CREATE INDEX IF NOT EXISTS idx_alliance_kill_stats_system_time 
    ON alliance_kill_stats(system_id, time_window_start);

CREATE INDEX IF NOT EXISTS idx_alliance_kill_stats_alliance_time 
    ON alliance_kill_stats(alliance_id, time_window_start);

-- Indexes for entity tables
CREATE INDEX IF NOT EXISTS idx_players_corporation 
    ON players(corporation_id);

CREATE INDEX IF NOT EXISTS idx_players_alliance 
    ON players(alliance_id);

CREATE INDEX IF NOT EXISTS idx_corporations_alliance 
    ON corporations(alliance_id);

-- =====================================================
-- Commit Transaction
-- =====================================================

COMMIT;

-- =====================================================
-- Migration Complete
-- =====================================================
-- All killmail tracking tables have been created successfully!
-- 
-- Tables created:
-- - players (character tracking)
-- - corporations (corporation data)
-- - alliances (alliance information)
-- - zkillboard_killmails (individual killmail records)
-- - system_kill_stats (system-wide statistics)
-- - player_kill_stats (per-player metrics)
-- - corporation_kill_stats (per-corporation metrics)
-- - alliance_kill_stats (per-alliance metrics)
--
-- Performance indexes have been added for optimal query performance.
-- Foreign key constraints ensure data integrity.
-- =====================================================

