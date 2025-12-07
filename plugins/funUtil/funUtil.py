#!/usr/bin/env python3
"""
FunUtil - Funscript Utilities Python Backend

Provides file system operations for funscript plugins:
- Read funscript files from disk
- Save funscripts and heatmaps
- File management operations
"""

import json
import os
import sys
from typing import Dict


def read_stdin():
    """Read JSON input from stdin"""
    input_data = sys.stdin.read()
    return json.loads(input_data)


def write_stdout(data):
    """Write JSON output to stdout"""
    print(json.dumps(data), flush=True)


def read_funscripts(base_path: str) -> Dict:
    """
    Read all funscript files for a given base path.

    Args:
        base_path: Path to video file without extension

    Returns:
        Dictionary with axis names as keys and funscript content as
        values
    """
    try:
        axis_extensions = [
            "stroke", "L0", "surge", "L1", "sway",
            "L2", "pitch", "roll", "twist"
        ]
        scripts = {}

        # Check main funscript
        main_path = f"{base_path}.funscript"
        if os.path.exists(main_path):
            with open(main_path, 'r', encoding='utf-8') as f:
                scripts["main"] = f.read()

        # Check all axis funscripts
        for ext in axis_extensions:
            axis_path = f"{base_path}.{ext}.funscript"
            if os.path.exists(axis_path):
                with open(axis_path, 'r', encoding='utf-8') as f:
                    scripts[ext] = f.read()

        return {"success": True, "scripts": scripts}
    except Exception as e:
        return {"success": False, "error": str(e)}


def save_funscript(path: str, content: str) -> Dict:
    """Save funscript content to file"""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"success": True, "message": f"Saved funscript to {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def save_heatmap(plugin_dir: str, filename: str, svg_content: str) -> Dict:
    """Save heatmap SVG to assets directory"""
    try:
        heatmap_dir = os.path.join(plugin_dir, 'assets', 'heatmaps')
        os.makedirs(heatmap_dir, exist_ok=True)

        filepath = os.path.join(heatmap_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        return {"success": True, "path": filepath}
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_directory(path: str) -> Dict:
    """Create directory recursively"""
    try:
        os.makedirs(path, exist_ok=True)
        return {"success": True, "message": f"Created directory {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def move_file(source_path: str, dest_path: str) -> Dict:
    """Move file from source to destination"""
    try:
        import shutil
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.move(source_path, dest_path)
        return {
            "success": True,
            "message": f"Moved {source_path} to {dest_path}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_file(path: str) -> Dict:
    """Delete file"""
    try:
        if os.path.exists(path):
            os.remove(path)
            return {"success": True, "message": f"Deleted {path}"}
        else:
            return {"success": False, "error": f"File not found: {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def rename_file(old_path: str, new_path: str) -> Dict:
    """Rename/move file"""
    try:
        os.rename(old_path, new_path)
        return {
            "success": True,
            "message": f"Renamed {old_path} to {new_path}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def file_exists(path: str) -> Dict:
    """Check if file exists"""
    try:
        exists = os.path.exists(path)
        return {"success": True, "exists": exists}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    """Main entry point for Python plugin"""
    try:
        request = read_stdin()
        action = request.get('action')

        # Route to appropriate function
        handlers = {
            'read_funscripts': lambda r: read_funscripts(r['base_path']),
            'save_funscript': lambda r: save_funscript(
                r['path'], r['content']
            ),
            'save_heatmap': lambda r: save_heatmap(
                r['plugin_dir'], r['filename'], r['svg_content']
            ),
            'create_directory': lambda r: create_directory(r['path']),
            'move_file': lambda r: move_file(
                r['source_path'], r['dest_path']
            ),
            'delete_file': lambda r: delete_file(r['path']),
            'rename_file': lambda r: rename_file(
                r['old_path'], r['new_path']
            ),
            'file_exists': lambda r: file_exists(r['path']),
        }

        if action in handlers:
            result = handlers[action](request)
        else:
            result = {"success": False, "error": f"Unknown action: {action}"}
            log(f"Error: Unknown action '{action}'")

        write_stdout(result)
    except Exception as e:
        log(f"Error in funUtil: {str(e)}")
        write_stdout({"success": False, "error": str(e)})
        sys.exit(1)


if __name__ == '__main__':
    main()
