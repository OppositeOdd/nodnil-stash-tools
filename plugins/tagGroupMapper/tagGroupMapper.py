#!/usr/bin/env python3
"""
Tag-Group Mapper Plugin for Stash

This plugin automatically maps tags to groups by matching names and aliases,
then generates the proper configuration format for the stashDynamicGroups plugin.

Usage:
- Run the plugin from Stash UI
- It will generate a 'tag_group_mappings.txt' file with the configuration
- Copy the contents to stashDynamicGroups plugin's SetGroupTagRelationship setting
"""

import sys
import os
import json
import subprocess
import re
from pathlib import Path

# Auto-install dependencies if missing
def ensure_dependencies():
    """Ensure required dependencies are installed"""
    required_packages = ['requests']
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            print(f"Installing missing package: {package}")
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", package, 
                    "--break-system-packages", "--quiet"
                ])
                print(f"Successfully installed: {package}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to install {package}: {e}")

# Install dependencies before importing
ensure_dependencies()

import requests

# Try to import configuration, fall back to defaults
try:
    from config import STASH_URL, STASH_API_KEY
except ImportError:
    STASH_URL = "http://localhost:9999"
    STASH_API_KEY = ""

def call_graphql(query, variables=None):
    """Make GraphQL request to Stash"""
    headers = {'Content-Type': 'application/json'}
    if STASH_API_KEY:
        headers['ApiKey'] = STASH_API_KEY
    
    data = {'query': query}
    if variables:
        data['variables'] = variables
    
    response = requests.post(f"{STASH_URL}/graphql", 
                           headers=headers, 
                           json=data)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"GraphQL request failed: {response.status_code}")
        return None

def log_info(message):
    """Simple logging function"""
    print(f"[INFO] {message}")

def log_error(message):
    """Simple error logging function"""
    print(f"[ERROR] {message}")

def log_warning(message):
    """Simple warning logging function"""
    print(f"[WARNING] {message}")

def get_all_tags():
    """Get all tags with their IDs, names, and aliases"""
    query = """
    query FindTags {
        findTags(filter: { per_page: -1 }) {
            tags {
                id
                name
                aliases
            }
        }
    }
    """
    
    result = call_graphql(query)
    
    if result and 'data' in result and 'findTags' in result['data']:
        return result['data']['findTags']['tags']
    return []

def get_all_groups():
    """Get all groups with their IDs, names, and aliases"""
    query = """
    query FindGroups {
        findGroups(filter: { per_page: -1 }) {
            groups {
                id
                name
                aliases
            }
        }
    }
    """
    
    result = call_graphql(query)
    
    if result and 'data' in result and 'findGroups' in result['data']:
        return result['data']['findGroups']['groups']
    return []

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

def generate_mappings_file(matches, output_dir):
    """Generate the mappings file for stashDynamicGroups plugin"""
    
    # Create output directory if it doesn't exist
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate configuration string
    config_parts = []
    for match in matches:
        tag_id = match['tag']['id']
        group_id = match['group']['id']
        config_parts.append(f"{tag_id}:{group_id}")
    
    config_string = ",".join(config_parts)
    
    # Write detailed report
    report_file = output_dir / "tag_group_mappings_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("TAG-GROUP MAPPING REPORT\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total matches found: {len(matches)}\n\n")
        
        f.write("DETAILED MATCHES:\n")
        f.write("-" * 30 + "\n")
        for i, match in enumerate(matches, 1):
            f.write(f"{i}. Tag: '{match['tag']['name']}' (ID: {match['tag']['id']})\n")
            f.write(f"   Group: '{match['group']['name']}' (ID: {match['group']['id']})\n")
            f.write(f"   Match Type: {match['match_type']}\n")
            f.write(f"   Tag Match: '{match['tag_match']}'\n")
            f.write(f"   Group Match: '{match['group_match']}'\n")
            f.write("\n")
    
    # Write configuration file for stashDynamicGroups
    config_file = output_dir / "tag_group_mappings.txt"
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write("# Configuration for stashDynamicGroups plugin\n")
        f.write("# Copy the line below to SetGroupTagRelationship setting\n\n")
        f.write(config_string + "\n\n")
        f.write("# Individual mappings:\n")
        for match in matches:
            f.write(f"# {match['tag']['name']} (ID: {match['tag']['id']}) -> {match['group']['name']} (ID: {match['group']['id']})\n")
    
    return config_file, report_file, len(matches)

def main():
    """Main function to generate tag-group mappings"""
    log_info("Starting Tag-Group Mapper...")
    
    # Get current directory for output
    script_dir = Path(__file__).parent
    
    # Fetch all tags
    log_info("Fetching all tags...")
    tags = get_all_tags()
    if not tags:
        log_warning("No tags found in Stash instance")
        return
    
    log_info(f"Found {len(tags)} tags")
    
    # Fetch all groups
    log_info("Fetching all groups...")
    groups = get_all_groups()
    if not groups:
        log_warning("No groups found in Stash instance")
        return
    
    log_info(f"Found {len(groups)} groups")
    
    # Find matches
    log_info("Finding tag-group matches...")
    matches = find_matching_groups(tags, groups)
    
    if not matches:
        log_warning("No tag-group matches found")
        return
    
    log_info(f"Found {len(matches)} tag-group matches")
    
    # Generate output files
    log_info("Generating output files...")
    config_file, report_file, match_count = generate_mappings_file(matches, script_dir)
    
    # Summary
    log_info("=" * 50)
    log_info("Tag-Group Mapping complete!")
    log_info(f"Total matches found: {match_count}")
    log_info(f"Configuration file: {config_file}")
    log_info(f"Detailed report: {report_file}")
    log_info("=" * 50)
    log_info("Next steps:")
    log_info("1. Open the configuration file")
    log_info("2. Copy the configuration string")
    log_info("3. Paste it into stashDynamicGroups plugin's SetGroupTagRelationship setting")

if __name__ == "__main__":
    main()