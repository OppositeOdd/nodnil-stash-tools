#!/usr/bin/env python3
"""
Extract Universe Names from Folder Structure

This script traverses a directory structure and extracts universe/franchise names
from top-level folder names to create a groups.txt file for bulk import.

Expected folder structure:
Folder/
  Universe1/
    Performer1/
      file1.mp4
    Performer2/
      file1.mp4
  Universe2/
    Performer3/
      file1.mp4

Usage:
    python extract_universes.py /path/to/main/folder
    python extract_universes.py /path/to/main/folder --output custom_groups.txt
"""

import os
import sys
import argparse
from pathlib import Path

def extract_universe_names(root_folder, output_file="groups.txt"):
    """
    Extract universe names from folder structure and write to output file.
    
    Args:
        root_folder (str): Path to the main folder containing universe/franchise folders
        output_file (str): Output filename for the universe list
    
    Returns:
        list: List of unique universe names found
    """
    root_path = Path(root_folder)
    
    if not root_path.exists():
        print(f"Error: Directory '{root_folder}' does not exist.")
        return []
    
    if not root_path.is_dir():
        print(f"Error: '{root_folder}' is not a directory.")
        return []
    
    universe_names = set()  # Use set to avoid duplicates
    
    print(f"Scanning directory: {root_path}")
    print("-" * 50)
    
    # Iterate through universe/franchise folders (level 1) - these are what we want
    for universe_folder in root_path.iterdir():
        if not universe_folder.is_dir():
            continue
            
        universe_name = universe_folder.name
        universe_names.add(universe_name)
        print(f"Found universe/franchise: {universe_name}")
        
        # Optional: Show what's inside each universe for verification
        performer_count = 0
        try:
            for performer_folder in universe_folder.iterdir():
                if performer_folder.is_dir():
                    performer_count += 1
            if performer_count > 0:
                print(f"  Contains {performer_count} performer folders")
        except PermissionError:
            print(f"  (Permission denied reading contents)")
    
    # Sort the names alphabetically
    sorted_universes = sorted(universe_names)
    
    print("-" * 50)
    print(f"Found {len(sorted_universes)} unique universes/franchises")
    
    # Write to output file
    script_dir = Path(__file__).parent
    output_path = script_dir / output_file
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for name in sorted_universes:
                f.write(f"{name}\n")
        
        print(f"Successfully wrote universe names to: {output_path}")
        return sorted_universes
        
    except Exception as e:
        print(f"Error writing to file '{output_path}': {str(e)}")
        return []

def main():
    parser = argparse.ArgumentParser(
        description="Extract universe/franchise names from folder structure for Stash bulk import as groups",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python extract_universes.py /path/to/content/folder
    python extract_universes.py /path/to/content/folder --output my_groups.txt
    python extract_universes.py /path/to/content/folder --dry-run
        """
    )
    
    parser.add_argument(
        'folder_path',
        help='Path to the main folder containing universe/franchise subfolders'
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
    
    universes = extract_universe_names(args.folder_path, args.output if not args.dry_run else "")
    
    if args.dry_run and universes:
        print("\nUniverses/Franchises that would be written:")
        for i, name in enumerate(universes, 1):
            print(f"{i:3d}. {name}")
    
    if universes and not args.dry_run:
        print(f"\nNext step: Run 'Bulk Import Groups' task in Stash")
        print(f"The groups.txt file is ready for import!")

if __name__ == "__main__":
    main()