#!/usr/bin/env python3
"""
Extract Performer Names from Folder Structure

This script traverses a directory structure and extracts performer names
from folder names to create a performers.txt file for bulk import.

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
    python extract_performers.py /path/to/main/folder
    python extract_performers.py /path/to/main/folder --output custom_performers.txt
"""

import os
import sys
import argparse
from pathlib import Path

def extract_performer_names(root_folder, output_file="performers.txt"):
    """
    Extract performer names from folder structure and write to output file.
    
    Args:
        root_folder (str): Path to the main folder containing universe/franchise folders
        output_file (str): Output filename for the performers list
    
    Returns:
        list: List of unique performer names found
    """
    root_path = Path(root_folder)
    
    if not root_path.exists():
        print(f"Error: Directory '{root_folder}' does not exist.")
        return []
    
    if not root_path.is_dir():
        print(f"Error: '{root_folder}' is not a directory.")
        return []
    
    performer_names = set()  # Use set to avoid duplicates
    
    print(f"Scanning directory: {root_path}")
    print("-" * 50)
    
    # Iterate through universe/franchise folders (level 1)
    for universe_folder in root_path.iterdir():
        if not universe_folder.is_dir():
            continue
            
        print(f"Processing universe/franchise: {universe_folder.name}")
        
        # Iterate through performer folders (level 2)
        for performer_folder in universe_folder.iterdir():
            if not performer_folder.is_dir():
                continue
                
            performer_name = performer_folder.name
            performer_names.add(performer_name)
            print(f"  Found performer: {performer_name}")
    
    # Sort the names alphabetically
    sorted_performers = sorted(performer_names)
    
    print("-" * 50)
    print(f"Found {len(sorted_performers)} unique performers")
    
    # Write to output file
    script_dir = Path(__file__).parent
    output_path = script_dir / output_file
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for name in sorted_performers:
                f.write(f"{name}\n")
        
        print(f"Successfully wrote performer names to: {output_path}")
        return sorted_performers
        
    except Exception as e:
        print(f"Error writing to file '{output_path}': {str(e)}")
        return []

def main():
    parser = argparse.ArgumentParser(
        description="Extract performer names from folder structure for Stash bulk import",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python extract_performers.py /path/to/content/folder
    python extract_performers.py /path/to/content/folder --output my_performers.txt
    python extract_performers.py /path/to/content/folder --dry-run
        """
    )
    
    parser.add_argument(
        'folder_path',
        help='Path to the main folder containing universe/franchise subfolders'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='performers.txt',
        help='Output filename (default: performers.txt)'
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
    
    performers = extract_performer_names(args.folder_path, args.output if not args.dry_run else "")
    
    if args.dry_run and performers:
        print("\nPerformers that would be written:")
        for i, name in enumerate(performers, 1):
            print(f"{i:3d}. {name}")
    
    if performers and not args.dry_run:
        print(f"\nNext step: Run 'Bulk Import Performers' task in Stash")
        print(f"The performers.txt file is ready for import!")

if __name__ == "__main__":
    main()