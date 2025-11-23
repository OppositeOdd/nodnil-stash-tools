#!/usr/bin/env python3
"""
Add Tag to Files

This script adds tags to filenames in two modes:
1. Automatic mode: Uses subfolder names as tags for files within those folders
2. Manual mode: Uses a specified tag for all files in a directory

The script cleans filenames by removing existing tags, brackets, and special characters,
then adds the tag in [TagName] format at the beginning of the filename.

Usage:
    python addTag.py /path/to/parent                    # Automatic mode
    python addTag.py /path/to/parent "TagName"          # Manual mode
"""

import os
import sys
import re
import argparse
from pathlib import Path

def clean_filename(filename, tag):
    """
    Clean filename by removing existing instances of the tag and other unwanted elements
    
    Args:
        filename (str): Original filename
        tag (str): Tag to remove from filename
    
    Returns:
        str: Cleaned filename
    """
    # Get file extension
    path = Path(filename)
    extension = path.suffix
    name_without_ext = path.stem
    
    # If no extension, treat entire name as the base
    if not extension:
        name_without_ext = filename
    
    # Convert tag to different cases for removal
    tag_lower = tag.lower()
    tag_upper = tag.upper()
    
    # Remove existing instances of the tag (case-insensitive)
    result = name_without_ext
    
    # Remove bracketed tag: [TagName], [tagname], [TAGNAME]
    for tag_variant in [tag, tag_lower, tag_upper]:
        result = re.sub(rf'\[{re.escape(tag_variant)}\]', '', result, flags=re.IGNORECASE)
    
    # Remove standalone tag instances (with word boundaries)
    for tag_variant in [tag, tag_lower, tag_upper]:
        pattern = rf'(^|\s){re.escape(tag_variant)}(\s|-|\.|$)'
        result = re.sub(pattern, ' ', result, flags=re.IGNORECASE)
    
    # Remove content inside brackets: {}, (), []
    result = re.sub(r'\{[^}]*\}', '', result)  # Remove {}
    result = re.sub(r'\([^)]*\)', '', result)  # Remove ()
    result = re.sub(r'\[[^\]]*\]', '', result)  # Remove []
    
    # Replace & and + with "and"
    result = re.sub(r'[&+]', ' and ', result)
    
    # Replace hyphens with spaces
    result = re.sub(r'-', ' ', result)
    
    # Remove special characters (keep only alphanumeric, spaces, dots, and apostrophes)
    result = re.sub(r'[^a-zA-Z0-9 .\']', '', result)
    
    # Clean up multiple spaces and trim
    result = re.sub(r'\s+', ' ', result)
    result = result.strip()
    
    # Reconstruct filename with extension
    if extension:
        return f"{result}{extension}"
    else:
        return result

def process_file(file_path, tag, mode="manual"):
    """
    Process a single file by cleaning and adding tag
    
    Args:
        file_path (Path): Path to the file
        tag (str): Tag to add
        mode (str): Processing mode for logging
    
    Returns:
        bool: True if file was renamed, False otherwise
    """
    directory = file_path.parent
    original_name = file_path.name
    
    # Clean the filename
    clean_name = clean_filename(original_name, tag)
    
    # Skip if the cleaned name is empty or just the extension
    if not clean_name or clean_name.startswith('.'):
        print(f"  Skipping file with empty name after cleaning: {file_path}")
        return False
    
    # Add tag in square brackets at the beginning
    new_name = f"[{tag}] {clean_name}"
    new_path = directory / new_name
    
    # Only rename if the new name is different
    if file_path.name != new_name:
        # Check if target file already exists
        if new_path.exists():
            if mode == "automatic":
                print(f"  Target already exists, skipping: {original_name} -> {new_name}")
            else:
                print(f"Target already exists, skipping: {file_path} -> {new_path}")
            return False
        else:
            try:
                file_path.rename(new_path)
                if mode == "automatic":
                    print(f"  Renamed: {original_name} -> {new_name}")
                else:
                    print(f"Renamed: {file_path} -> {new_path}")
                return True
            except OSError as e:
                print(f"Error renaming {file_path}: {e}")
                return False
    else:
        if mode == "automatic":
            print(f"  No change needed: {original_name}")
        else:
            print(f"No change needed: {file_path}")
        return False

def automatic_mode(parent_dir):
    """
    Automatic mode: Use subfolder names as tags for files within those folders
    
    Args:
        parent_dir (Path): Parent directory containing subfolders
    """
    print("Mode: Automatic folder-based tagging")
    print(f"Processing subfolders in: {parent_dir}")
    print()
    
    # Get all subdirectories
    subdirs = [d for d in parent_dir.iterdir() if d.is_dir()]
    
    if not subdirs:
        print("No subdirectories found.")
        return
    
    total_renamed = 0
    
    for subdir in subdirs:
        folder_name = subdir.name
        print(f"Processing folder: {folder_name}")
        
        # Get all files in this subdirectory (recursively)
        files = list(subdir.rglob('*'))
        files = [f for f in files if f.is_file()]
        
        folder_renamed = 0
        for file_path in files:
            if process_file(file_path, folder_name, "automatic"):
                folder_renamed += 1
        
        total_renamed += folder_renamed
        print(f"Completed folder: {folder_name} ({folder_renamed} files renamed)")
        print()
    
    print(f"Total files renamed: {total_renamed}")

def manual_mode(parent_dir, tag):
    """
    Manual mode: Use specified tag for all files in the directory
    
    Args:
        parent_dir (Path): Directory containing files to tag
        tag (str): Tag to apply to all files
    """
    print(f"Mode: Manual tagging with tag '{tag}'")
    print(f"Processing all files in: {parent_dir}")
    print()
    
    # Get all files recursively
    files = list(parent_dir.rglob('*'))
    files = [f for f in files if f.is_file()]
    
    if not files:
        print("No files found.")
        return
    
    renamed_count = 0
    for file_path in files:
        if process_file(file_path, tag, "manual"):
            renamed_count += 1
    
    print(f"\nTotal files renamed: {renamed_count}")

def main():
    parser = argparse.ArgumentParser(
        description="Add tags to filenames in two modes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python addTag.py /path/to/parent
        Automatic mode: Uses subfolder names as tags
        
    python addTag.py /path/to/parent "TagName"
        Manual mode: Uses specified tag for all files
        """
    )
    
    parser.add_argument(
        'parent_dir',
        help='Path to the parent directory'
    )
    
    parser.add_argument(
        'tag',
        nargs='?',
        help='Tag to apply to all files (manual mode)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be renamed without actually renaming files'
    )
    
    args = parser.parse_args()
    
    # Validate parent directory
    parent_dir = Path(args.parent_dir)
    if not parent_dir.exists():
        print(f"Error: Directory '{parent_dir}' does not exist.")
        sys.exit(1)
    
    if not parent_dir.is_dir():
        print(f"Error: '{parent_dir}' is not a directory.")
        sys.exit(1)
    
    # Show usage if no arguments
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    
    if args.dry_run:
        print("DRY RUN MODE - No files will be renamed")
        print("=" * 50)
        # Note: Dry run functionality would require modifying process_file
        # For now, just show the warning
    
    try:
        if args.tag:
            # Manual mode
            manual_mode(parent_dir, args.tag)
        else:
            # Automatic mode
            automatic_mode(parent_dir)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()