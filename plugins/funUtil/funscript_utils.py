#!/usr/bin/env python3
"""
Shared funscript utilities for Stash plugins.
Import this module to avoid code duplication.
"""

import json
import os
import sys
from typing import Dict, Optional

AXIS_EXTENSIONS = [
    "stroke", "L0", "surge", "L1", "sway",
    "L2", "pitch", "roll", "twist"
]

AXIS_MAPPING = {
    "stroke": "stroke", "L0": "stroke",
    "surge": "surge", "L1": "surge",
    "sway": "sway", "L2": "sway",
    "pitch": "pitch",
    "roll": "roll",
    "twist": "twist"
}


def find_funscript_paths(base_path: str) -> Dict[str, str]:
    """Find all funscript file paths for a given base path."""
    scripts = {}

    main_path = f"{base_path}.funscript"
    if os.path.exists(main_path):
        scripts["main"] = main_path

    for ext in AXIS_EXTENSIONS:
        axis_path = f"{base_path}.{ext}.funscript"
        if os.path.exists(axis_path):
            scripts[ext] = axis_path

    return scripts


def read_funscript_json(file_path: str) -> Optional[Dict]:
    """Read and parse funscript JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def get_funscript_version(funscript_data: Dict) -> str:
    """
    Detect the version of a funscript.

    Returns:
        '1.0' - single-axis
        '1.1' - merged with axes array
        '2.0' - merged with channels object
    """
    if not funscript_data:
        return '1.0'

    version = funscript_data.get('version', '1.0')

    # v2.0 with channels
    if version == '2.0' and 'channels' in funscript_data:
        channels = funscript_data.get('channels', {})
        if isinstance(channels, dict) and len(channels) > 0:
            return '2.0'

    # v1.1 with axes array
    if 'axes' in funscript_data:
        axes = funscript_data.get('axes', [])
        if isinstance(axes, list) and len(axes) > 0:
            return '1.1'

    # v1.1 with metadata containing other axes (legacy check)
    if 'metadata' in funscript_data:
        metadata = funscript_data.get('metadata', {})
        if isinstance(metadata, dict):
            for key in metadata:
                if (isinstance(metadata[key], dict) and
                        'actions' in metadata[key]):
                    return '1.1'

    return '1.0'


def is_merged_funscript(funscript_data: Dict) -> bool:
    """
    Check if funscript contains multiple axes (merged format).

    Returns True if v1.1 or v2.0, False if v1.0

    Args:
        funscript_data: Parsed funscript JSON data

    Returns:
        True if multi-axis merged format, False otherwise
    """
    version = get_funscript_version(funscript_data)
    return version in ('1.1', '2.0')


def merge_funscripts_v20(scripts: Dict[str, Dict]) -> Dict:
    """Merge multiple funscripts into v2.0 format."""
    main_script = scripts.get("main")
    if not main_script:
        main_script = (
            scripts.get("stroke") or scripts.get("L0") or
            list(scripts.values())[0]
        )

    merged = {
        "version": "2.0",
        "actions": main_script.get('actions', []),
        "metadata": main_script.get('metadata', {}),
        "channels": {}
    }

    for axis_name, script in scripts.items():
        if axis_name == "main":
            continue
        channel_name = AXIS_MAPPING.get(axis_name, axis_name)
        merged["channels"][channel_name] = {
            "actions": script.get('actions', [])
        }

    return merged


def convert_funscript_format(
    funscript_data: Dict,
    target_version: str
) -> Optional[Dict]:
    """
    Convert a funscript between v1.1 and v2.0 formats using funlib_py.

    Args:
        funscript_data: Input funscript data (v1.1 or v2.0)
        target_version: Target version ('1.1' or '2.0')

    Returns:
        Converted funscript data or None on error
    """
    sys.path.insert(0, os.path.dirname(__file__))
    from funlib_py import Funscript

    current_version = get_funscript_version(funscript_data)

    if current_version == target_version:
        return funscript_data

    if current_version == '1.0':
        return None

    try:
        script = Funscript(funscript_data)
        converted = script.toJSON({'version': target_version})
        return converted
    except Exception:
        return None


def save_funscript(file_path: str, data: Dict) -> bool:
    """Save funscript to file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def get_merged_channels(funscript_data: Dict) -> list:
    """
    Get list of channel names from a merged funscript.

    Returns:
        List of channel names (e.g., ['stroke', 'surge', 'pitch'])
    """
    version = get_funscript_version(funscript_data)

    if version == '2.0':
        channels = funscript_data.get('channels', {})
        return list(channels.keys())

    if version == '1.1':
        axes = funscript_data.get('axes', [])
        channel_names = []
        for axis in axes:
            axis_id = axis.get('id')
            id_to_channel = {
                0: 'stroke', 1: 'surge', 2: 'sway',
                3: 'pitch', 4: 'roll', 5: 'twist'
            }
            if axis_id in id_to_channel:
                channel_names.append(id_to_channel[axis_id])
        return channel_names
    return []


def unmerge_funscript(funscript_data: Dict, base_path: str) -> Optional[Dict]:
    """
    Split a merged funscript into separate v1.0 scripts using funlib_py.

    Args:
        funscript_data: Merged funscript data (v1.1 or v2.0)
        base_path: Base file path without extension

    Returns:
        Dict mapping channel names to their file paths, or None on error
    """
    sys.path.insert(0, os.path.dirname(__file__))
    from funlib_py import Funscript

    version = get_funscript_version(funscript_data)
    if version == '1.0':
        return None

    try:
        script = Funscript(funscript_data)

        parent_metadata = script.metadata.toJSON()

        scripts_list = script.toJSON({'version': '1.0-list'})

        if not scripts_list or len(scripts_list) == 0:
            return None

        saved_files = {}

        for script_data in scripts_list:
            channel = script_data.get('channel')

            script_data['version'] = '1.0'

            if 'metadata' not in script_data or not script_data['metadata']:
                script_data['metadata'] = dict(parent_metadata)
            else:
                current_metadata = script_data['metadata']
                for key, value in parent_metadata.items():
                    if key not in current_metadata:
                        current_metadata[key] = value

            if 'chapters' in script_data['metadata'] and script_data['metadata']['chapters']:
                chapters_list = script_data['metadata']['chapters']
                if hasattr(chapters_list[0], 'toJSON'):
                    script_data['metadata']['chapters'] = [ch.toJSON() for ch in chapters_list]

            script_data.pop('id', None)
            script_data.pop('axes', None)
            script_data.pop('channels', None)
            script_data.pop('parent', None)
            script_data.pop('channel', None)

            if channel:
                file_path = f"{base_path}.{channel}.funscript"
                channel_key = channel
            else:
                file_path = f"{base_path}.funscript"
                channel_key = 'stroke'

            if save_funscript(file_path, script_data):
                saved_files[channel_key] = file_path

        return saved_files if saved_files else None

    except Exception as e:
        import traceback
        print(f"unmerge_funscript error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None


def save_funscript(file_path: str, data: Dict) -> bool:
    """Save funscript to file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def read_stdin():
    """Read and parse JSON from stdin."""
    input_data = sys.stdin.read()
    return json.loads(input_data)


def write_stdout(data):
    """Write JSON to stdout."""
    print(json.dumps(data), flush=True)


def log(message):
    """
    Log progress message to stderr.

    Progress logs go to stderr so stdout remains clean for final JSON.
    Stash captures stderr based on errLog level setting in YAML.
    """
    print(message, file=sys.stderr, flush=True)

