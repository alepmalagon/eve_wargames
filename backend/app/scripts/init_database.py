#!/usr/bin/env python3
"""
Database initialization script for EVE Wargames.

This script initializes the database with basic faction warfare data
and can be run to populate the systems table with initial data.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base
from models.faction import Faction
from models.system import System, SystemSnapshot
from models.faction_warfare import FactionWarfareSnapshot
from services.esi_client import esi_client
from services.data_processor import DataProcessor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_database():
    """Initialize the database with basic faction warfare data."""
    logger.info("Starting database initialization...")
    
    # Create all tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Fetch and process initial faction warfare data
        logger.info("Fetching initial faction warfare data from ESI...")
        
        async with esi_client as client:
            # Initialize data processor with ESI client
            data_processor = DataProcessor(db, client)
            
            # Ensure factions exist
            logger.info("Creating faction records...")
            data_processor._ensure_factions_exist()
            
            # Get faction warfare systems from ESI
            fw_systems = await client.get_faction_warfare_systems()
            
            if not fw_systems:
                logger.error("Failed to fetch faction warfare systems from ESI")
                return False
            
            logger.info(f"Fetched {len(fw_systems)} faction warfare systems")
            
            # Get warzone data for advantage information
            warzone_data = await client.get_warzone_data()
            
            if not warzone_data:
                logger.warning("Failed to fetch warzone data - advantage percentages will be 0")
            else:
                logger.info(f"Fetched warzone data for {len(warzone_data)} systems")
            
            # Get faction warfare stats
            fw_stats = await client.get_faction_warfare_stats()
            
            # Process all data together
            logger.info("Processing systems and creating initial data...")
            result = await data_processor.process_faction_warfare_data(
                fw_systems=fw_systems,
                fw_stats=fw_stats,
                warzone_data=warzone_data
            )
            
            logger.info(f"Processed {result['systems_processed']} systems")
            logger.info(f"Created {result['snapshots_created']} snapshots")
            logger.info(f"Updated {result['systems_updated']} systems")
            logger.info(f"Warzone snapshot created: {result['warzone_snapshot_created']}")
            
            # Commit all changes
            db.commit()
            logger.info("Database initialization completed successfully!")
            
            return True
            
    except Exception as e:
        logger.error(f"Error during database initialization: {str(e)}")
        db.rollback()
        return False
        
    finally:
        db.close()


async def check_database_status():
    """Check the current status of the database."""
    db = SessionLocal()
    
    try:
        # Check factions
        factions = db.query(Faction).all()
        logger.info(f"Factions in database: {len(factions)}")
        for faction in factions:
            logger.info(f"  - {faction.name} (ID: {faction.faction_id})")
        
        # Check systems
        systems = db.query(System).all()
        logger.info(f"Systems in database: {len(systems)}")
        
        # Check snapshots
        snapshots = db.query(SystemSnapshot).all()
        logger.info(f"System snapshots in database: {len(snapshots)}")
        
        # Check warzone snapshots
        warzone_snapshots = db.query(FactionWarfareSnapshot).all()
        logger.info(f"Warzone snapshots in database: {len(warzone_snapshots)}")
        
        return {
            "factions": len(factions),
            "systems": len(systems),
            "system_snapshots": len(snapshots),
            "warzone_snapshots": len(warzone_snapshots)
        }
        
    finally:
        db.close()


async def main():
    """Main function to run database initialization."""
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        logger.info("Checking database status...")
        await check_database_status()
        return
    
    logger.info("EVE Wargames Database Initialization")
    logger.info("=" * 50)
    
    # Check current status
    logger.info("Checking current database status...")
    status = await check_database_status()
    
    if status["systems"] > 0:
        logger.info("Database already contains system data.")
        response = input("Do you want to reinitialize? (y/N): ")
        if response.lower() != 'y':
            logger.info("Initialization cancelled.")
            return
    
    # Initialize database
    success = await init_database()
    
    if success:
        logger.info("Database initialization completed successfully!")
        logger.info("You can now start the application and view systems data.")
    else:
        logger.error("Database initialization failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
