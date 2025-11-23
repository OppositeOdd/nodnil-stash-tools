#!/usr/bin/env python3
"""
Extract Studio Names from Folder Structure

This script traverses a directory structure and extracts studio names
from folder names to create a studios.txt file for bulk import.

Expected folder structure:
Folder/
  StudioType1/
    Studio1/
      content files
    Studio2/
      content files
  StudioType2/
    Studio3/
      content files

Or alternatively:
Folder/
  Studio1/
    scenes/content
  Studio2/
    scenes/content

Usage:
    python extract_studios.py /path/to/main/folder
    python extract_studios.py /path/to/main/folder --output custom_studios.txt
"""

import os
import sys
import argparse
from pathlib import Path

def extract_studio_names(root_folder, output_file="studios.txt", level=2):
    """
    Extract studio names from folder structure and write to output file.
    
    Args:
        root_folder (str): Path to the main folder containing studio folders
        output_file (str): Output filename for the studios list
        level (int): Folder level to extract (1 for top-level, 2 for second-level)
    
    Returns:
        list: List of unique studio names found
    """
    root_path = Path(root_folder)
    
    if not root_path.exists():
        print(f"Error: Directory '{root_folder}' does not exist.")
        return []
    
    if not root_path.is_dir():
        print(f"Error: '{root_folder}' is not a directory.")
        return []
    
    studio_names = set()  # Use set to avoid duplicates
    
    print(f"Scanning directory: {root_path}")
    print(f"Extracting from level {level} folders")
    print("-" * 50)
    
    if level == 1:
        # Extract top-level folders as studios
        for studio_folder in root_path.iterdir():
            if not studio_folder.is_dir():
                continue
                
            studio_name = studio_folder.name
            studio_names.add(studio_name)
            print(f"Found studio: {studio_name}")
    
    else:  # level == 2
        # Extract second-level folders as studios
        for category_folder in root_path.iterdir():
            if not category_folder.is_dir():
                continue
                
            print(f"Processing category: {category_folder.name}")
            
            for studio_folder in category_folder.iterdir():
                if not studio_folder.is_dir():
                    continue
                    
                studio_name = studio_folder.name
                studio_names.add(studio_name)
                print(f"  Found studio: {studio_name}")
    
    # Sort the names alphabetically
    sorted_studios = sorted(studio_names)
    
    print("-" * 50)
    print(f"Found {len(sorted_studios)} unique studios")
    
    # Write to output file
    script_dir = Path(__file__).parent
    output_path = script_dir / output_file
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for name in sorted_studios:
                f.write(f"{name}\n")
        
        print(f"Successfully wrote studio names to: {output_path}")
        return sorted_studios
        
    except Exception as e:
        print(f"Error writing to file '{output_path}': {str(e)}")
        return []

def main():
    parser = argparse.ArgumentParser(
        description="Extract studio names from folder structure for Stash bulk import",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python extract_studios.py /path/to/content/folder
    python extract_studios.py /path/to/content/folder --output my_studios.txt
    python extract_studios.py /path/to/content/folder --level 1 --dry-run
        """
    )
    
    parser.add_argument(
        'folder_path',
        help='Path to the main folder containing studio folders'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='studios.txt',
        help='Output filename (default: studios.txt)'
    )
    
    parser.add_argument(
        '--level', '-l',
        type=int,
        choices=[1, 2],
        default=2,
        help='Folder level to extract studios from (1=top-level, 2=second-level, default: 2)'
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
    
    studios = extract_studio_names(
        args.folder_path, 
        args.output if not args.dry_run else "", 
        args.level
    )
    
    if args.dry_run and studios:
        print("\nStudios that would be written:")
        for i, name in enumerate(studios, 1):
            print(f"{i:3d}. {name}")
    
    if studios and not args.dry_run:
        print(f"\nNext step: Run 'Bulk Import Studios' task in Stash")
        print(f"The studios.txt file is ready for import!")

if __name__ == "__main__":
    main()