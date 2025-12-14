#!/usr/bin/env python3
"""
Standalone database migration script to add faction advantage columns.
This script can run independently of the Docker environment.
"""

import psycopg2
import sys
import os

def run_migration():
    """
    Add minmatar_advantage and amarr_advantage columns to systems and system_snapshots tables.
    """
    # Database connection parameters
    db_params = {
        'host': 'localhost',
        'port': 5432,
        'database': 'eve_wargames',
        'user': 'eve_user',
        'password': 'eve_password'
    }
    
    try:
        # Connect to the database
        print("Connecting to database...")
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        # Add columns to systems table
        print("Adding faction advantage columns to systems table...")
        cursor.execute("""
            ALTER TABLE systems 
            ADD COLUMN IF NOT EXISTS minmatar_advantage REAL DEFAULT 0.0,
            ADD COLUMN IF NOT EXISTS amarr_advantage REAL DEFAULT 0.0
        """)
        
        # Add columns to system_snapshots table
        print("Adding faction advantage columns to system_snapshots table...")
        cursor.execute("""
            ALTER TABLE system_snapshots 
            ADD COLUMN IF NOT EXISTS minmatar_advantage REAL DEFAULT 0.0,
            ADD COLUMN IF NOT EXISTS amarr_advantage REAL DEFAULT 0.0
        """)
        
        # Commit the changes
        conn.commit()
        print("Migration completed successfully!")
        
        # Verify the columns were added
        print("Verifying columns were added...")
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'systems' 
            AND column_name IN ('minmatar_advantage', 'amarr_advantage')
        """)
        systems_columns = cursor.fetchall()
        
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'system_snapshots' 
            AND column_name IN ('minmatar_advantage', 'amarr_advantage')
        """)
        snapshots_columns = cursor.fetchall()
        
        print(f"Systems table columns added: {[col[0] for col in systems_columns]}")
        print(f"System_snapshots table columns added: {[col[0] for col in snapshots_columns]}")
        
        return True
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        print(f"Migration failed: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
