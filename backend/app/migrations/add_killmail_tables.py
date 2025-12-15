"""
Migration to add killmail tracking tables for Zkillboard data integration.

This migration creates tables for tracking killmail data, player/corporation/alliance
activity, and aggregated statistics for faction warfare systems.
"""

import logging
from sqlalchemy import text
from ..database import engine

logger = logging.getLogger(__name__)

def run_migration():
    """
    Create killmail tracking tables for Zkillboard integration.
    """
    try:
        with engine.connect() as connection:
            # Start transaction
            trans = connection.begin()
            
            try:
                logger.info("Creating killmail tracking tables...")
                
                # Create players table
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS players (
                        character_id BIGINT PRIMARY KEY,
                        character_name VARCHAR(255) NOT NULL,
                        corporation_id BIGINT,
                        alliance_id BIGINT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """))
                
                # Create corporations table
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS corporations (
                        corporation_id BIGINT PRIMARY KEY,
                        corporation_name VARCHAR(255) NOT NULL,
                        ticker VARCHAR(10),
                        alliance_id BIGINT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """))
                
                # Create alliances table
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS alliances (
                        alliance_id BIGINT PRIMARY KEY,
                        alliance_name VARCHAR(255) NOT NULL,
                        ticker VARCHAR(10),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """))
                
                # Create zkillboard_killmails table
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS zkillboard_killmails (
                        id SERIAL PRIMARY KEY,
                        killmail_id BIGINT UNIQUE NOT NULL,
                        killmail_hash VARCHAR(255) NOT NULL,
                        system_id INTEGER NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        victim_character_id BIGINT,
                        victim_corporation_id BIGINT,
                        victim_alliance_id BIGINT,
                        victim_faction_id INTEGER,
                        attacker_character_id BIGINT,
                        attacker_corporation_id BIGINT,
                        attacker_alliance_id BIGINT,
                        attacker_faction_id INTEGER,
                        total_value BIGINT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        
                        FOREIGN KEY (system_id) REFERENCES systems(system_id),
                        FOREIGN KEY (victim_character_id) REFERENCES players(character_id),
                        FOREIGN KEY (victim_corporation_id) REFERENCES corporations(corporation_id),
                        FOREIGN KEY (victim_alliance_id) REFERENCES alliances(alliance_id),
                        FOREIGN KEY (attacker_character_id) REFERENCES players(character_id),
                        FOREIGN KEY (attacker_corporation_id) REFERENCES corporations(corporation_id),
                        FOREIGN KEY (attacker_alliance_id) REFERENCES alliances(alliance_id)
                    );
                """))
                
                # Create system_kill_stats table
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS system_kill_stats (
                        id SERIAL PRIMARY KEY,
                        system_id INTEGER NOT NULL,
                        time_window_start TIMESTAMP NOT NULL,
                        time_window_end TIMESTAMP NOT NULL,
                        total_kills INTEGER DEFAULT 0,
                        total_isk_killed BIGINT DEFAULT 0,
                        minmatar_kills INTEGER DEFAULT 0,
                        minmatar_losses INTEGER DEFAULT 0,
                        minmatar_isk_killed BIGINT DEFAULT 0,
                        minmatar_isk_lost BIGINT DEFAULT 0,
                        amarr_kills INTEGER DEFAULT 0,
                        amarr_losses INTEGER DEFAULT 0,
                        amarr_isk_killed BIGINT DEFAULT 0,
                        amarr_isk_lost BIGINT DEFAULT 0,
                        unique_players INTEGER DEFAULT 0,
                        unique_corporations INTEGER DEFAULT 0,
                        unique_alliances INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        
                        FOREIGN KEY (system_id) REFERENCES systems(system_id),
                        UNIQUE(system_id, time_window_start, time_window_end)
                    );
                """))
                
                # Create player_kill_stats table
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS player_kill_stats (
                        id SERIAL PRIMARY KEY,
                        system_id INTEGER NOT NULL,
                        character_id BIGINT NOT NULL,
                        time_window_start TIMESTAMP NOT NULL,
                        time_window_end TIMESTAMP NOT NULL,
                        kills INTEGER DEFAULT 0,
                        losses INTEGER DEFAULT 0,
                        isk_killed BIGINT DEFAULT 0,
                        isk_lost BIGINT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        
                        FOREIGN KEY (system_id) REFERENCES systems(system_id),
                        FOREIGN KEY (character_id) REFERENCES players(character_id),
                        UNIQUE(system_id, character_id, time_window_start, time_window_end)
                    );
                """))
                
                # Create corporation_kill_stats table
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS corporation_kill_stats (
                        id SERIAL PRIMARY KEY,
                        system_id INTEGER NOT NULL,
                        corporation_id BIGINT NOT NULL,
                        time_window_start TIMESTAMP NOT NULL,
                        time_window_end TIMESTAMP NOT NULL,
                        kills INTEGER DEFAULT 0,
                        losses INTEGER DEFAULT 0,
                        isk_killed BIGINT DEFAULT 0,
                        isk_lost BIGINT DEFAULT 0,
                        unique_players INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        
                        FOREIGN KEY (system_id) REFERENCES systems(system_id),
                        FOREIGN KEY (corporation_id) REFERENCES corporations(corporation_id),
                        UNIQUE(system_id, corporation_id, time_window_start, time_window_end)
                    );
                """))
                
                # Create alliance_kill_stats table
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS alliance_kill_stats (
                        id SERIAL PRIMARY KEY,
                        system_id INTEGER NOT NULL,
                        alliance_id BIGINT NOT NULL,
                        time_window_start TIMESTAMP NOT NULL,
                        time_window_end TIMESTAMP NOT NULL,
                        kills INTEGER DEFAULT 0,
                        losses INTEGER DEFAULT 0,
                        isk_killed BIGINT DEFAULT 0,
                        isk_lost BIGINT DEFAULT 0,
                        unique_players INTEGER DEFAULT 0,
                        unique_corporations INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        
                        FOREIGN KEY (system_id) REFERENCES systems(system_id),
                        FOREIGN KEY (alliance_id) REFERENCES alliances(alliance_id),
                        UNIQUE(system_id, alliance_id, time_window_start, time_window_end)
                    );
                """))
                
                # Create indexes for performance
                logger.info("Creating indexes for killmail tables...")
                
                # Indexes for zkillboard_killmails
                connection.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_zkillboard_killmails_system_timestamp 
                    ON zkillboard_killmails(system_id, timestamp);
                """))
                
                connection.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_zkillboard_killmails_attacker_faction 
                    ON zkillboard_killmails(attacker_faction_id, timestamp);
                """))
                
                connection.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_zkillboard_killmails_victim_faction 
                    ON zkillboard_killmails(victim_faction_id, timestamp);
                """))
                
                # Indexes for stats tables
                connection.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_system_kill_stats_system_time 
                    ON system_kill_stats(system_id, time_window_start);
                """))
                
                connection.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_player_kill_stats_system_time 
                    ON player_kill_stats(system_id, time_window_start);
                """))
                
                connection.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_corporation_kill_stats_system_time 
                    ON corporation_kill_stats(system_id, time_window_start);
                """))
                
                connection.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_alliance_kill_stats_system_time 
                    ON alliance_kill_stats(system_id, time_window_start);
                """))
                
                # Commit transaction
                trans.commit()
                logger.info("Killmail tables migration completed successfully!")
                
            except Exception as e:
                trans.rollback()
                raise e
                
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise e

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migration()
