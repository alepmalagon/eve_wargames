#!/usr/bin/env python3
"""
Test script for the frontline classifier.

This script tests the frontline classification functionality using the generated
adjacency data and some sample system control data.
"""

import json
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "app"))

from app.utils.frontline_classifier import get_frontline_classifier, SystemClassification


def test_frontline_classifier():
    """Test the frontline classifier with sample data."""
    print("Testing Frontline Classifier")
    print("=" * 50)
    
    # Get the classifier
    classifier = get_frontline_classifier()
    
    # Check if adjacency data was loaded
    if not classifier.adjacency_map:
        print("❌ ERROR: No adjacency data loaded!")
        return False
    
    print(f"✅ Loaded adjacency data for {len(classifier.adjacency_map)} systems")
    
    # Test with sample system control data (using real system IDs from our data)
    sample_systems = [
        {"solar_system_id": 30002537, "occupier_faction_id": 500002},  # Amamake - Minmatar
        {"solar_system_id": 30002538, "occupier_faction_id": 500002},  # Vard - Minmatar
        {"solar_system_id": 30002539, "occupier_faction_id": 500003},  # Siseide - Amarr
        {"solar_system_id": 30002540, "occupier_faction_id": 500003},  # Lantorn - Amarr
        {"solar_system_id": 30002541, "occupier_faction_id": 500002},  # Dal - Minmatar
        {"solar_system_id": 30002542, "occupier_faction_id": 500002},  # Auga - Minmatar
    ]
    
    print(f"\n📊 Testing with {len(sample_systems)} sample systems:")
    for system in sample_systems:
        system_id = system["solar_system_id"]
        faction_id = system["occupier_faction_id"]
        faction_name = "Minmatar" if faction_id == 500002 else "Amarr"
        system_info = classifier.get_system_info(system_id)
        system_name = system_info.get('name', f'System_{system_id}') if system_info else f'System_{system_id}'
        print(f"  {system_name} ({system_id}): {faction_name}")
    
    # Classify systems
    classifications = classifier.classify_systems(sample_systems)
    
    print(f"\n🎯 Classification Results:")
    for system_id, classification in classifications.items():
        system_info = classifier.get_system_info(system_id)
        system_name = system_info.get('name', f'System_{system_id}') if system_info else f'System_{system_id}'
        adjacent_systems = classifier.get_system_adjacency(system_id)
        
        print(f"  {system_name} ({system_id}): {classification.value.upper()}")
        print(f"    Adjacent to {len(adjacent_systems)} systems: {adjacent_systems}")
    
    # Get statistics
    stats = classifier.get_classification_stats(classifications)
    print(f"\n📈 Statistics:")
    for stat_name, count in stats.items():
        print(f"  {stat_name}: {count}")
    
    # Test specific adjacency
    print(f"\n🔗 Testing Adjacency for Amamake (30002537):")
    amamake_adjacent = classifier.get_system_adjacency(30002537)
    print(f"  Adjacent systems: {amamake_adjacent}")
    
    for adj_id in amamake_adjacent:
        adj_info = classifier.get_system_info(adj_id)
        adj_name = adj_info.get('name', f'System_{adj_id}') if adj_info else f'System_{adj_id}'
        print(f"    {adj_name} ({adj_id})")
    
    print(f"\n✅ Frontline classifier test completed successfully!")
    return True


def test_with_real_data():
    """Test with the actual generated adjacency data."""
    print("\n" + "=" * 50)
    print("Testing with Real Adjacency Data")
    print("=" * 50)
    
    # Load the generated adjacency data
    adjacency_file = Path(__file__).parent / "data" / "system_adjacency.json"
    
    if not adjacency_file.exists():
        print("❌ ERROR: Adjacency data file not found!")
        return False
    
    with open(adjacency_file, 'r') as f:
        data = json.load(f)
    
    print(f"✅ Loaded adjacency data from file")
    print(f"  Generated at: {data['metadata']['generated_at']}")
    print(f"  Total systems: {data['metadata']['total_systems']}")
    print(f"  Frontline systems: {data['metadata']['frontline_systems']}")
    print(f"  Command operations: {data['metadata']['command_operations_systems']}")
    print(f"  Rearguard systems: {data['metadata']['rearguard_systems']}")
    
    # Show some examples from each classification
    classifications = data['classifications']
    system_info = data['system_info']
    
    print(f"\n🔴 Sample Frontline Systems:")
    frontline_count = 0
    for system_id, classification in classifications.items():
        if classification == "frontline" and frontline_count < 3:
            name = system_info[system_id]['name']
            faction_id = system_info[system_id]['occupier_faction_id']
            faction_name = "Minmatar" if faction_id == 500002 else "Amarr"
            print(f"  {name} ({system_id}) - {faction_name}")
            frontline_count += 1
    
    print(f"\n🟡 Sample Command Operations Systems:")
    command_count = 0
    for system_id, classification in classifications.items():
        if classification == "command_operations" and command_count < 3:
            name = system_info[system_id]['name']
            faction_id = system_info[system_id]['occupier_faction_id']
            faction_name = "Minmatar" if faction_id == 500002 else "Amarr"
            print(f"  {name} ({system_id}) - {faction_name}")
            command_count += 1
    
    print(f"\n🟢 Sample Rearguard Systems:")
    rearguard_count = 0
    for system_id, classification in classifications.items():
        if classification == "rearguard" and rearguard_count < 3:
            name = system_info[system_id]['name']
            faction_id = system_info[system_id]['occupier_faction_id']
            faction_name = "Minmatar" if faction_id == 500002 else "Amarr"
            print(f"  {name} ({system_id}) - {faction_name}")
            rearguard_count += 1
    
    return True


if __name__ == "__main__":
    print("🚀 Starting Frontline Classifier Tests")
    
    success = test_frontline_classifier()
    if success:
        success = test_with_real_data()
    
    if success:
        print(f"\n🎉 All tests passed!")
    else:
        print(f"\n❌ Some tests failed!")
        sys.exit(1)
