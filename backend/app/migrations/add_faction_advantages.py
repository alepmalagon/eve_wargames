"""
Migration to add individual faction advantage columns to systems and system_snapshots tables.
"""

import logging
from sqlalchemy import text
from ..database import get_db

logger = logging.getLogger(__name__)

def run_migration():
    """
    Add minmatar_advantage and amarr_advantage columns to systems and system_snapshots tables.
    """
    db = next(get_db())
    
    try:
        # Add columns to systems table
        logger.info("Adding faction advantage columns to systems table...")
        db.execute(text("""
            ALTER TABLE systems 
            ADD COLUMN IF NOT EXISTS minmatar_advantage FLOAT DEFAULT 0.0,
            ADD COLUMN IF NOT EXISTS amarr_advantage FLOAT DEFAULT 0.0
        """))
        
        # Add columns to system_snapshots table
        logger.info("Adding faction advantage columns to system_snapshots table...")
        db.execute(text("""
            ALTER TABLE system_snapshots 
            ADD COLUMN IF NOT EXISTS minmatar_advantage FLOAT DEFAULT 0.0,
            ADD COLUMN IF NOT EXISTS amarr_advantage FLOAT DEFAULT 0.0
        """))
        
        db.commit()
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
