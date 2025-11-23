#!/usr/bin/env python3
"""
Extract Animator Names from File Titles

This script traverses a directory structure and extracts animator names
from file names to create a studios.txt file for bulk import.

Expected folder structure and naming:
Folder/
  Universe1/
    Performer1/
      [AnimatorName] file1.mp4
    Performer2/
      [AnimatorName2] file1.mp4
  Universe2/
    Performer3/
      [AnimatorName3] file1.mp4

Usage:
    python extract_animators.py /path/to/main/folder
    python extract_animators.py /path/to/main/folder --output custom_studios.txt
"""

import os
import sys
import argparse
import re
from pathlib import Path

def extract_animator_names(root_folder, output_file="studios.txt"):
    """
    Extract animator names from file names and write to output file.
    
    Args:
        root_folder (str): Path to the main folder containing universe/performer folders
        output_file (str): Output filename for the animator list
    
    Returns:
        list: List of unique animator names found
    """
    root_path = Path(root_folder)
    
    if not root_path.exists():
        print(f"Error: Directory '{root_folder}' does not exist.")
        return []
    
    if not root_path.is_dir():
        print(f"Error: '{root_folder}' is not a directory.")
        return []
    
    animator_names = set()  # Use set to avoid duplicates
    file_count = 0
    processed_files = 0
    
    print(f"Scanning directory: {root_path}")
    print("-" * 50)
    
    # Define pattern to match [AnimatorName] at the beginning of filename
    animator_pattern = re.compile(r'^\[([^\]]+)\]')
    
    # Recursively walk through all directories
    for current_dir, subdirs, files in os.walk(root_path):
        current_path = Path(current_dir)
        
        # Skip if this is the root directory
        if current_path == root_path:
            continue
            
        # Get relative path for display
        rel_path = current_path.relative_to(root_path)
        
        # Process video files in current directory
        video_files = [f for f in files if f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'))]
        
        if video_files:
            print(f"Processing: {rel_path}")
            
            for filename in video_files:
                file_count += 1
                
                # Extract animator name using regex
                match = animator_pattern.match(filename)
                if match:
                    animator_name = match.group(1).strip()
                    if animator_name:  # Only add non-empty names
                        animator_names.add(animator_name)
                        processed_files += 1
                        print(f"  Found animator: {animator_name} (from: {filename})")
                else:
                    print(f"  No animator found in: {filename}")
    
    # Sort the names alphabetically
    sorted_animators = sorted(animator_names)
    
    print("-" * 50)
    print(f"Processed {file_count} video files")
    print(f"Found animator names in {processed_files} files")
    print(f"Discovered {len(sorted_animators)} unique animators")
    
    # Write to output file
    script_dir = Path(__file__).parent
    output_path = script_dir / output_file
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for name in sorted_animators:
                f.write(f"{name}\n")
        
        print(f"Successfully wrote animator names to: {output_path}")
        return sorted_animators
        
    except Exception as e:
        print(f"Error writing to file '{output_path}': {str(e)}")
        return []

def main():
    parser = argparse.ArgumentParser(
        description="Extract animator names from file titles for Stash bulk import as studios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python extract_animators.py /path/to/content/folder
    python extract_animators.py /path/to/content/folder --output my_studios.txt
    python extract_animators.py /path/to/content/folder --dry-run
        """
    )
    
    parser.add_argument(
        'folder_path',
        help='Path to the main folder containing universe/performer subfolders'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='studios.txt',
        help='Output filename (default: studios.txt)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be extracted without writing to file'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed file processing information'
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("DRY RUN MODE - No file will be written")
        print("=" * 50)
    
    animators = extract_animator_names(args.folder_path, args.output if not args.dry_run else "")
    
    if args.dry_run and animators:
        print("\nAnimators that would be written:")
        for i, name in enumerate(animators, 1):
            print(f"{i:3d}. {name}")
    
    if animators and not args.dry_run:
        print(f"\nNext step: Copy studios.txt to your bulkImportStudios plugin directory")
        print(f"Then run 'Bulk Import Studios' task in Stash")
        print(f"The studios.txt file is ready for import!")

if __name__ == "__main__":
    main()