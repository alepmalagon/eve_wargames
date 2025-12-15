-- Migration script to create killmail_attackers table
-- This table stores individual attacker records for each killmail
-- allowing proper tracking of all participants, not just final blow attackers

BEGIN;

-- Create the killmail_attackers table
CREATE TABLE IF NOT EXISTS killmail_attackers (
    id SERIAL PRIMARY KEY,
    killmail_id INTEGER NOT NULL,
    
    -- Attacker information
    character_id INTEGER,
    corporation_id INTEGER,
    alliance_id INTEGER,
    faction_id INTEGER,  -- 500002 (Minmatar) or 500003 (Amarr)
    
    -- Combat details
    damage_done INTEGER DEFAULT 0,
    final_blow BOOLEAN DEFAULT FALSE,
    security_status REAL,
    ship_type_id INTEGER,
    weapon_type_id INTEGER,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_attackers_killmail 
        FOREIGN KEY (killmail_id) 
        REFERENCES zkillboard_killmails(killmail_id) 
        ON DELETE CASCADE,
    
    CONSTRAINT fk_attackers_character 
        FOREIGN KEY (character_id) 
        REFERENCES players(character_id) 
        ON DELETE SET NULL,
    
    CONSTRAINT fk_attackers_corporation 
        FOREIGN KEY (corporation_id) 
        REFERENCES corporations(corporation_id) 
        ON DELETE SET NULL,
    
    CONSTRAINT fk_attackers_alliance 
        FOREIGN KEY (alliance_id) 
        REFERENCES alliances(alliance_id) 
        ON DELETE SET NULL
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_attackers_killmail ON killmail_attackers(killmail_id);
CREATE INDEX IF NOT EXISTS idx_attackers_character ON killmail_attackers(character_id);
CREATE INDEX IF NOT EXISTS idx_attackers_corporation ON killmail_attackers(corporation_id);
CREATE INDEX IF NOT EXISTS idx_attackers_alliance ON killmail_attackers(alliance_id);
CREATE INDEX IF NOT EXISTS idx_attackers_faction ON killmail_attackers(faction_id);

-- Create composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_attackers_char_faction ON killmail_attackers(character_id, faction_id);
CREATE INDEX IF NOT EXISTS idx_attackers_corp_faction ON killmail_attackers(corporation_id, faction_id);
CREATE INDEX IF NOT EXISTS idx_attackers_alliance_faction ON killmail_attackers(alliance_id, faction_id);

-- Add comment to the table
COMMENT ON TABLE killmail_attackers IS 'Individual attacker records for each killmail, enabling accurate participation statistics';
COMMENT ON COLUMN killmail_attackers.killmail_id IS 'Reference to the main killmail record';
COMMENT ON COLUMN killmail_attackers.character_id IS 'EVE character ID of the attacker (nullable for NPC kills)';
COMMENT ON COLUMN killmail_attackers.corporation_id IS 'Corporation ID of the attacker';
COMMENT ON COLUMN killmail_attackers.alliance_id IS 'Alliance ID of the attacker (nullable if not in alliance)';
COMMENT ON COLUMN killmail_attackers.faction_id IS 'Faction ID: 500002 (Minmatar) or 500003 (Amarr)';
COMMENT ON COLUMN killmail_attackers.damage_done IS 'Damage dealt by this attacker';
COMMENT ON COLUMN killmail_attackers.final_blow IS 'Whether this attacker dealt the final blow';
COMMENT ON COLUMN killmail_attackers.security_status IS 'Character security status at time of kill';
COMMENT ON COLUMN killmail_attackers.ship_type_id IS 'Type ID of ship used by attacker';
COMMENT ON COLUMN killmail_attackers.weapon_type_id IS 'Type ID of weapon used by attacker';

COMMIT;

-- Verify the table was created successfully
SELECT 
    table_name, 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'killmail_attackers' 
ORDER BY ordinal_position;

