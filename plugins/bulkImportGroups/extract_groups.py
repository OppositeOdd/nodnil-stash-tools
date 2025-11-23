#!/usr/bin/env python3
"""
Extract Group Names from Folder Structure

This script traverses a directory structure and extracts group names
from folder names to create a groups.txt file for bulk import.

Expected folder structure:
Folder/
  GroupType1/
    Group1/
      content files
    Group2/
      content files
  GroupType2/
    Group3/
      content files

Usage:
    python extract_groups.py /path/to/main/folder
    python extract_groups.py /path/to/main/folder --output custom_groups.txt
"""

import os
import sys
import argparse
from pathlib import Path

def extract_group_names(root_folder, output_file="groups.txt"):
    """
    Extract group names from folder structure and write to output file.
    
    Args:
        root_folder (str): Path to the main folder containing group type folders
        output_file (str): Output filename for the groups list
    
    Returns:
        list: List of unique group names found
    """
    root_path = Path(root_folder)
    
    if not root_path.exists():
        print(f"Error: Directory '{root_folder}' does not exist.")
        return []
    
    if not root_path.is_dir():
        print(f"Error: '{root_folder}' is not a directory.")
        return []
    
    group_names = set()  # Use set to avoid duplicates
    
    print(f"Scanning directory: {root_path}")
    print("-" * 50)
    
    # Iterate through group type folders (level 1)
    for group_type_folder in root_path.iterdir():
        if not group_type_folder.is_dir():
            continue
            
        print(f"Processing group type: {group_type_folder.name}")
        
        # Iterate through group folders (level 2)
        for group_folder in group_type_folder.iterdir():
            if not group_folder.is_dir():
                continue
                
            group_name = group_folder.name
            group_names.add(group_name)
            print(f"  Found group: {group_name}")
    
    # Sort the names alphabetically
    sorted_groups = sorted(group_names)
    
    print("-" * 50)
    print(f"Found {len(sorted_groups)} unique groups")
    
    # Write to output file
    script_dir = Path(__file__).parent
    output_path = script_dir / output_file
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for name in sorted_groups:
                f.write(f"{name}\n")
        
        print(f"Successfully wrote group names to: {output_path}")
        return sorted_groups
        
    except Exception as e:
        print(f"Error writing to file '{output_path}': {str(e)}")
        return []

def main():
    parser = argparse.ArgumentParser(
        description="Extract group names from folder structure for Stash bulk import",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python extract_groups.py /path/to/content/folder
    python extract_groups.py /path/to/content/folder --output my_groups.txt
    python extract_groups.py /path/to/content/folder --dry-run
        """
    )
    
    parser.add_argument(
        'folder_path',
        help='Path to the main folder containing group type subfolders'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='groups.txt',
        help='Output filename (default: groups.txt)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be extracted without writing to file'
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("DRY RUN MODE - No file will be written")
        print("=" * 50)
    
    groups = extract_group_names(args.folder_path, args.output if not args.dry_run else "")
    
    if args.dry_run and groups:
        print("\nGroups that would be written:")
        for i, name in enumerate(groups, 1):
            print(f"{i:3d}. {name}")
    
    if groups and not args.dry_run:
        print(f"\nNext step: Run 'Bulk Import Groups' task in Stash")
        print(f"The groups.txt file is ready for import!")

if __name__ == "__main__":
    main()