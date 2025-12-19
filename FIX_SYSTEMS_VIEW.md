# Fix for Systems View 404 Errors

## Problem
The EVE Wargames frontend systems view is showing "System Not Found" and "Failed to fetch system data" errors because the database is empty. The API endpoints like `/api/v1/systems/30002537/trends` are returning 404 Not Found errors.

## Root Cause
The database tables exist but contain no data. The systems table is empty, so when the frontend tries to fetch system information for Amamake (ID: 30002537) or any other system, the API returns 404 because the system doesn't exist in the database.

## Solution
Populate the database with systems data extracted from the frontend map data.

## Quick Fix Options

### Option 1: Using SQL File (Recommended)
1. Start the PostgreSQL database:
   ```bash
   docker compose up -d postgres
   ```

2. Import the systems data:
   ```bash
   docker compose exec postgres psql -U eve_user -d eve_wargames -f /tmp/systems_data.sql
   ```
   
   Or if running locally:
   ```bash
   psql -h localhost -U eve_user -d eve_wargames -f systems_data.sql
   ```

### Option 2: Using Python Script
1. Install required dependencies:
   ```bash
   pip install psycopg2-binary
   ```

2. Run the initialization script:
   ```bash
   python3 init_systems_data.py
   ```

### Option 3: Manual Database Setup
If you have direct database access, you can run the SQL commands from `systems_data.sql` directly in your PostgreSQL client.

## What the Fix Does

1. **Creates necessary tables**: `factions`, `systems`, `system_snapshots`
2. **Inserts faction data**: Minmatar Republic (500002) and Amarr Empire (500003)
3. **Populates systems table**: All 56+ systems from the frontend map data including Amamake (30002537)
4. **Creates initial snapshots**: Enables the trends API endpoints to return data
5. **Sets realistic values**: Random but realistic faction warfare percentages and control data

## Verification

After running the fix, test these endpoints:

```bash
# Test systems list
curl http://localhost:8000/api/v1/systems/

# Test specific system (Amamake)
curl http://localhost:8000/api/v1/systems/30002537

# Test trends data
curl http://localhost:8000/api/v1/systems/30002537/trends?hours=24

# Test killmail stats
curl http://localhost:8000/api/v1/systems/30002537/killmail-stats
```

## Expected Results

- Systems view should load without errors
- Amamake system page should display properly
- All API endpoints should return data instead of 404 errors
- Map view should show systems with proper faction control data

## Files Created

- `init_systems_data.py` - Python script to initialize database
- `systems_data.sql` - SQL file with all systems data
- `FIX_SYSTEMS_VIEW.md` - This documentation

## Technical Details

The fix extracts system data from `frontend/src/data/mapSystems.ts` which contains:
- System IDs (like 30002537 for Amamake)
- System names
- Map coordinates (not used in database)

The database is populated with:
- Basic system information
- Random but realistic faction warfare data
- Initial snapshots for trend functionality
- Proper foreign key relationships

This ensures all API endpoints work correctly and the frontend can display system information without 404 errors.

