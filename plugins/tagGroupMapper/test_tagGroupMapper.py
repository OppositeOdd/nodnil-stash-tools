#!/usr/bin/env python3
"""
Test version of tagGroupMapper - simulates API responses without connecting to Stash
"""

import re
from pathlib import Path

def normalize_name(name):
    """Normalize name for matching (lowercase, remove special chars, etc.)"""
    if not name:
        return ""
    
    # Convert to lowercase
    normalized = name.lower()
    
    # Remove special characters but keep spaces, letters, numbers
    normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
    
    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized

def simulate_get_all_tags():
    """Simulate getting tags from Stash (test data)"""
    return [
        {"id": "123", "name": "Xenoblade Chronicles", "aliases": ["XC", "Xenoblade"]},
        {"id": "124", "name": "Final Fantasy", "aliases": ["FF"]},
        {"id": "125", "name": "Pokemon", "aliases": ["Pokémon"]},
        {"id": "126", "name": "Marvel", "aliases": ["Marvel Comics"]},
        {"id": "127", "name": "Nintendo", "aliases": ["Nintendo Games"]},
    ]

def simulate_get_all_groups():
    """Simulate getting groups from Stash (test data)"""
    return [
        {"id": "456", "name": "Xenoblade Chronicles", "aliases": ["Xenoblade Series"]},
        {"id": "457", "name": "Final Fantasy", "aliases": ["FF Series"]},
        {"id": "458", "name": "Pokemon", "aliases": ["Pokemon Games"]},
        {"id": "459", "name": "DC Comics", "aliases": ["DC"]},
        {"id": "460", "name": "Studio Ghibli", "aliases": []},
    ]

def find_matching_groups(tags, groups):
    """Find tags that match groups by name or aliases"""
    matches = []
    
    # Create a lookup dictionary for groups with normalized names
    group_lookup = {}
    for group in groups:
        # Add main name
        normalized_name = normalize_name(group['name'])
        if normalized_name:
            if normalized_name not in group_lookup:
                group_lookup[normalized_name] = []
            group_lookup[normalized_name].append(group)
        
        # Add aliases
        if group.get('aliases'):
            for alias in group['aliases']:
                normalized_alias = normalize_name(alias)
                if normalized_alias:
                    if normalized_alias not in group_lookup:
                        group_lookup[normalized_alias] = []
                    group_lookup[normalized_alias].append(group)
    
    # Find matching tags
    for tag in tags:
        tag_matches = []
        
        # Check tag name against group names/aliases
        normalized_tag_name = normalize_name(tag['name'])
        if normalized_tag_name in group_lookup:
            for group in group_lookup[normalized_tag_name]:
                tag_matches.append({
                    'tag': tag,
                    'group': group,
                    'match_type': 'name',
                    'tag_match': tag['name'],
                    'group_match': group['name']
                })
        
        # Check tag aliases against group names/aliases
        if tag.get('aliases'):
            for tag_alias in tag['aliases']:
                normalized_tag_alias = normalize_name(tag_alias)
                if normalized_tag_alias in group_lookup:
                    for group in group_lookup[normalized_tag_alias]:
                        # Avoid duplicates
                        duplicate = False
                        for existing_match in tag_matches:
                            if existing_match['group']['id'] == group['id']:
                                duplicate = True
                                break
                        
                        if not duplicate:
                            tag_matches.append({
                                'tag': tag,
                                'group': group,
                                'match_type': 'alias',
                                'tag_match': tag_alias,
                                'group_match': group['name']
                            })
        
        matches.extend(tag_matches)
    
    return matches

def test_main():
    """Test the matching logic"""
    print("[INFO] Starting Tag-Group Mapper (TEST MODE)...")
    
    # Get test data
    tags = simulate_get_all_tags()
    groups = simulate_get_all_groups()
    
    print(f"[INFO] Found {len(tags)} tags")
    print(f"[INFO] Found {len(groups)} groups")
    
    # Find matches
    print("[INFO] Finding tag-group matches...")
    matches = find_matching_groups(tags, groups)
    
    if not matches:
        print("[WARNING] No tag-group matches found")
        return
    
    print(f"[INFO] Found {len(matches)} tag-group matches")
    
    # Display matches
    print("\nMATCHES FOUND:")
    print("=" * 50)
    
    config_parts = []
    for i, match in enumerate(matches, 1):
        print(f"{i}. Tag: '{match['tag']['name']}' (ID: {match['tag']['id']})")
        print(f"   Group: '{match['group']['name']}' (ID: {match['group']['id']})")
        print(f"   Match Type: {match['match_type']}")
        print(f"   Tag Match: '{match['tag_match']}'")
        print(f"   Group Match: '{match['group_match']}'")
        print()
        
        config_parts.append(f"{match['tag']['id']}:{match['group']['id']}")
    
    # Show configuration string
    config_string = ",".join(config_parts)
    print("CONFIGURATION STRING FOR stashDynamicGroups:")
    print("=" * 50)
    print(config_string)
    print()
    
    print("INDIVIDUAL MAPPINGS:")
    print("-" * 30)
    for match in matches:
        print(f"{match['tag']['name']} (ID: {match['tag']['id']}) -> {match['group']['name']} (ID: {match['group']['id']})")

if __name__ == "__main__":
    test_main()