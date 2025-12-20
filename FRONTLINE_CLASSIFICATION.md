# Frontline Classification System

This document describes the frontline classification system implemented for the EVE Wargames project, which replicates the algorithm used by EVE Online's official frontlines map.

## Overview

The frontline classification system categorizes warzone systems into three types based on their proximity to enemy-controlled territory:

- **🔴 Frontline**: Systems directly adjacent to enemy-controlled systems
- **🟡 Command Operations**: Systems adjacent to frontline systems  
- **🟢 Rearguard**: All other systems in the warzone

## Implementation

### 1. System Adjacency Data Generation

The system uses a static adjacency map generated from EVE Online's ESI API:

```bash
cd backend
python scripts/generate_system_adjacency.py
```

This script:
- Fetches all 70 Minmatar/Amarr warzone systems from ESI
- For each system, queries the stargate connections
- Builds a complete adjacency map of system connections
- Calculates initial frontline classifications
- Saves the data to `backend/data/system_adjacency.json`

### 2. Dynamic Classification

The `FrontlineClassifier` class provides real-time classification based on current system control:

```python
from app.utils.frontline_classifier import get_frontline_classifier

classifier = get_frontline_classifier()
classifications = classifier.classify_systems(system_control_data)
```

### 3. API Endpoints

New API endpoints provide access to frontline data:

- `GET /api/v1/frontlines/` - Overview of all system classifications
- `GET /api/v1/frontlines/live` - Live classification using current ESI data
- `GET /api/v1/frontlines/system/{system_id}` - Specific system info
- `GET /api/v1/frontlines/adjacency/{system_id}` - System adjacency data
- `GET /api/v1/frontlines/stats` - Classification statistics

## Algorithm Details

### Classification Rules

1. **Frontline Systems**: A system is classified as frontline if it is directly adjacent to a system controlled by the enemy faction.

2. **Command Operations**: A system is classified as command operations if it is adjacent to any frontline system (but not frontline itself).

3. **Rearguard**: All remaining systems that don't meet the above criteria.

### Example

```
Minmatar System A ← Adjacent → Amarr System B
```

- System A = Frontline (adjacent to enemy)
- System B = Frontline (adjacent to enemy)

```
Minmatar System C ← Adjacent → Minmatar System A (Frontline)
```

- System C = Command Operations (adjacent to frontline)

### Faction IDs

The system uses militia faction IDs:
- Minmatar: `500002` (Tribal Liberation Force)
- Amarr: `500003` (24th Imperial Crusade)

## Data Structure

### Adjacency Data File

```json
{
  "metadata": {
    "generated_at": "2025-12-20T21:22:57.655170",
    "total_systems": 70,
    "frontline_systems": 16,
    "command_operations_systems": 15,
    "rearguard_systems": 39,
    "description": "System adjacency and frontline classification data"
  },
  "adjacency_map": {
    "30002537": [30002517, 30002538, 30002539, 30002541, 30002542],
    // ... more systems
  },
  "classifications": {
    "30002537": "frontline",
    // ... more systems
  },
  "system_info": {
    "30002537": {
      "name": "Amamake",
      "occupier_faction_id": 500002,
      "owner_faction_id": 500002,
      "contested": 0
    }
    // ... more systems
  }
}
```

### API Response Format

```json
{
  "statistics": {
    "frontline": 16,
    "command_operations": 15,
    "rearguard": 39,
    "total": 70
  },
  "systems": {
    "frontline": [
      {
        "system_id": 30002537,
        "name": "Amamake",
        "security_status": 0.4,
        "controlling_faction_id": 500002,
        "contested": 0,
        "classification": "frontline",
        "adjacent_systems": [30002517, 30002538, 30002539, 30002541, 30002542]
      }
    ],
    "command_operations": [...],
    "rearguard": [...]
  }
}
```

## Testing

Run the test script to verify the classification system:

```bash
cd backend
python test_frontline_classifier.py
```

This will test:
- Adjacency data loading
- Classification algorithm with sample data
- Integration with the generated adjacency file

## Usage Examples

### Get Current Frontline Overview

```bash
curl http://localhost:8000/api/v1/frontlines/
```

### Get Live Classification Data

```bash
curl http://localhost:8000/api/v1/frontlines/live
```

### Get Specific System Info

```bash
curl http://localhost:8000/api/v1/frontlines/system/30002537
```

### Get System Adjacency

```bash
curl http://localhost:8000/api/v1/frontlines/adjacency/30002537
```

## Integration with Frontend

The frontend can use this data to:

1. **Color-code systems** on the warzone map based on classification
2. **Display frontline statistics** in the UI
3. **Show system adjacency** when hovering over systems
4. **Update classifications** in real-time based on system control changes

### Suggested Color Scheme

- **Frontline**: Red (`#FF4444`)
- **Command Operations**: Yellow/Orange (`#FFA500`) 
- **Rearguard**: Green (`#44AA44`)

## Performance Considerations

- **Static Adjacency Data**: The adjacency map is static and only needs regeneration if CCP adds/removes systems
- **Cached Classifications**: Consider caching classification results for a few minutes to reduce computation
- **Efficient Algorithm**: The classification algorithm is O(n) where n is the number of systems

## Future Enhancements

1. **Historical Tracking**: Store frontline classification changes over time
2. **Notification System**: Alert when systems change classification
3. **Advanced Metrics**: Calculate frontline stability, contested zones, etc.
4. **Visual Improvements**: Add frontline "heat maps" showing battle intensity

## Files Added/Modified

### New Files
- `backend/scripts/generate_system_adjacency.py` - Adjacency data generation script
- `backend/app/utils/frontline_classifier.py` - Classification utility module
- `backend/app/api/frontlines.py` - API endpoints for frontline data
- `backend/data/system_adjacency.json` - Static adjacency data (generated)
- `backend/test_frontline_classifier.py` - Test script

### Modified Files
- `backend/main.py` - Added frontlines router registration

## Conclusion

This implementation successfully replicates EVE Online's frontline classification algorithm, providing the eve_wargames project with the ability to display accurate frontline information on the warzone map. The system is efficient, well-tested, and ready for integration with the frontend mapping interface.
