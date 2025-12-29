#!/usr/bin/env python3
"""
Database initialization script for EVE Wargames systems data.

This script populates the database with systems data extracted from the frontend
mapSystems.ts file, ensuring the systems API endpoints work correctly.
"""

import re
import psycopg2
from datetime import datetime
import sys
import random

def extract_systems_from_frontend():
    """Extract systems data from frontend/src/data/mapSystems.ts"""
    systems = []
    
    try:
        with open('frontend/src/data/mapSystems.ts', 'r') as f:
            content = f.read()
            
        # Extract system data using regex
        pattern = r'\{\s*id:\s*(\d+),\s*name:\s*"([^"]+)"'
        matches = re.findall(pattern, content)
        
        for system_id, name in matches:
            systems.append({
                'system_id': int(system_id),
                'name': name,
                'security_status': round(random.uniform(0.1, 0.9), 1),  # Random security status
                'controlling_faction_id': random.choice([500002, 500003]),  # Random faction
                'contested': random.choice([0, 1]),  # Random contested status
                'capture_percent': round(random.uniform(0, 100), 1),
                'advantage_percent': round(random.uniform(0, 100), 1),
                'minmatar_advantage': round(random.uniform(0, 100), 1),
                'amarr_advantage': round(random.uniform(0, 100), 1)
            })
            
        print(f"Extracted {len(systems)} systems from frontend data")
        return systems
        
    except FileNotFoundError:
        print("Error: Could not find frontend/src/data/mapSystems.ts")
        return []
    except Exception as e:
        print(f"Error extracting systems data: {e}")
        return []

def create_database_tables(cursor):
    """Create necessary database tables if they don't exist"""
    
    # Create factions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS factions (
            faction_id INTEGER PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            ticker VARCHAR(10),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create systems table
    cursor.execute("""
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
        )
    """)
    
    # Create system_snapshots table
    cursor.execute("""
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
        )
    """)
    
    print("Database tables created/verified")

def insert_factions(cursor):
    """Insert faction data"""
    factions = [
        (500002, 'Minmatar Republic', 'MIN'),
        (500003, 'Amarr Empire', 'AMR')
    ]
    
    for faction_id, name, ticker in factions:
        cursor.execute("""
            INSERT INTO factions (faction_id, name, ticker)
            VALUES (%s, %s, %s)
            ON CONFLICT (faction_id) DO UPDATE SET
                name = EXCLUDED.name,
                ticker = EXCLUDED.ticker,
                updated_at = CURRENT_TIMESTAMP
        """, (faction_id, name, ticker))
    
    print("Factions inserted/updated")

def insert_systems(cursor, systems):
    """Insert systems data into the database"""
    
    for system in systems:
        cursor.execute("""
            INSERT INTO systems (
                system_id, name, security_status, controlling_faction_id,
                contested, capture_percent, advantage_percent,
                minmatar_advantage, amarr_advantage
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (system_id) DO UPDATE SET
                name = EXCLUDED.name,
                security_status = EXCLUDED.security_status,
                controlling_faction_id = EXCLUDED.controlling_faction_id,
                contested = EXCLUDED.contested,
                capture_percent = EXCLUDED.capture_percent,
                advantage_percent = EXCLUDED.advantage_percent,
                minmatar_advantage = EXCLUDED.minmatar_advantage,
                amarr_advantage = EXCLUDED.amarr_advantage,
                updated_at = CURRENT_TIMESTAMP
        """, (
            system['system_id'], system['name'], system['security_status'],
            system['controlling_faction_id'], system['contested'],
            system['capture_percent'], system['advantage_percent'],
            system['minmatar_advantage'], system['amarr_advantage']
        ))
    
    print(f"Inserted/updated {len(systems)} systems")

def create_initial_snapshots(cursor, systems):
    """Create initial system snapshots for trend data"""
    
    current_time = datetime.now()
    
    for system in systems:
        # Create a snapshot for each system
        cursor.execute("""
            INSERT INTO system_snapshots (
                system_id, controlling_faction_id, contested,
                capture_percent, advantage_percent,
                minmatar_advantage, amarr_advantage, timestamp
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            system['system_id'], system['controlling_faction_id'],
            system['contested'], system['capture_percent'],
            system['advantage_percent'], system['minmatar_advantage'],
            system['amarr_advantage'], current_time
        ))
    
    print(f"Created initial snapshots for {len(systems)} systems")

def main():
    """Main function to initialize the database"""
    
    # Database connection parameters
    db_params = {
        'host': 'localhost',
        'port': 5432,
        'database': 'eve_wargames',
        'user': 'eve_user',
        'password': 'eve_password'
    }
    
    print("EVE Wargames - Systems Data Initialization")
    print("=" * 50)
    
    # Extract systems data from frontend
    systems = extract_systems_from_frontend()
    if not systems:
        print("No systems data found. Exiting.")
        sys.exit(1)
    
    try:
        # Connect to database
        print("Connecting to database...")
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        # Create tables
        print("Creating/verifying database tables...")
        create_database_tables(cursor)
        
        # Insert factions
        print("Inserting faction data...")
        insert_factions(cursor)
        
        # Insert systems
        print("Inserting systems data...")
        insert_systems(cursor, systems)
        
        # Create initial snapshots
        print("Creating initial system snapshots...")
        create_initial_snapshots(cursor, systems)
        
        # Commit all changes
        conn.commit()
        
        print("\n" + "=" * 50)
        print("Database initialization completed successfully!")
        print(f"- {len(systems)} systems added/updated")
        print("- 2 factions added/updated")
        print(f"- {len(systems)} initial snapshots created")
        print("\nThe systems API endpoints should now work correctly.")
        print("You can test with: curl http://localhost:8000/api/v1/systems/30002537")
        
        # Verify Amamake specifically
        cursor.execute("SELECT system_id, name FROM systems WHERE system_id = 30002537")
        result = cursor.fetchone()
        if result:
            print(f"\n✅ Amamake (ID: {result[0]}) successfully added to database")
        else:
            print("\n❌ Amamake not found in database")
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    main()

