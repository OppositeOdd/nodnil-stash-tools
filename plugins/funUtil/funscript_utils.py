#!/usr/bin/env python3
"""
Shared funscript utilities for Stash plugins.
Import this module to avoid code duplication.
"""

import json
import os
import sys
from typing import Dict, List, Optional

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

def extract_variant_suffix(filename: str, base_name: str) -> str:
    if filename == f"{base_name}.funscript":
        return ""

    if not filename.startswith(base_name):
        return None

    suffix = filename[len(base_name):]

    if suffix.startswith("."):
        return None

    if suffix.endswith(".funscript"):
        return suffix[:-len(".funscript")]

    return None


def find_script_variants_and_axes(directory: str, base_name: str) -> tuple:
    """
    Find all funscript variants and axis scripts in a directory.
    
    Variants are scripts with the same base name but different suffixes, like:
    - Scene.funscript (default variant, no suffix)
    - Scene (Intense).funscript (variant with suffix " (Intense)")
    - Scene - Easy.funscript (variant with suffix " - Easy")
    
    Axis scripts are secondary motion axis files like:
    - Scene.surge.funscript
    - Scene.sway.funscript
    - Scene.pitch.funscript
    
    Args:
        directory: Directory to search for scripts
        base_name: Base name without extension (e.g., "Scene" for "Scene.mp4")
    
    Returns:
        Tuple of (variants_dict, axes_dict) where:
        - variants_dict: {variant_key: {'path': str, 'filename': str, 'suffix': str}}
        - axes_dict: {axis_name: full_path}
    """
    from typing import Dict, Tuple
    
    variants = {}
    axes = {}

    try:
        all_files = os.listdir(directory)
    except OSError:
        return {}, {}

    # Filter to just funscript files matching base name
    all_scripts = []
    for filename in all_files:
        if filename.startswith(base_name) and filename.endswith('.funscript'):
            # Skip .max.funscript files (intermediate merge files)
            if '.max.funscript' not in filename:
                all_scripts.append(filename)

    # Separate variants from axis scripts
    for filename in all_scripts:
        full_path = os.path.join(directory, filename)
        
        # Check if it's an axis script
        is_axis = False
        for axis in AXIS_EXTENSIONS:
            if filename == f"{base_name}.{axis}.funscript":
                axes[axis] = full_path
                is_axis = True
                break

        if is_axis:
            continue

        # It's a variant - extract suffix
        variant_suffix = extract_variant_suffix(filename, base_name)

        if variant_suffix is None:
            continue  # Doesn't match expected pattern

        variant_key = variant_suffix if variant_suffix else "default"
        variants[variant_key] = {
            'path': full_path,
            'filename': filename,
            'suffix': variant_suffix
        }

    return variants, axes

def read_stdin():
    """Read and parse JSON from stdin."""
    input_data = sys.stdin.read()
    return json.loads(input_data)


def write_stdout(data):
    """Write JSON to stdout."""
    print(json.dumps(data), flush=True)


def query_interactive_scenes(server_url: str, cookies: Dict = None, filter_has_funscripts: bool = True) -> List[Dict]:
    """
    Query Stash for all interactive scenes using GraphQL.
    
    Args:
        server_url: Stash GraphQL endpoint URL (e.g., "http://localhost:9999/graphql")
        cookies: Optional session cookies for authentication
        filter_has_funscripts: If True, only return scenes with actual funscript files
    
    Returns:
        List of dicts with scene data:
        - id: Scene ID
        - title: Scene title (optional)
        - oshash: File oshash fingerprint
        - file_path: Full path to video file
        
    Example:
        >>> scenes = query_interactive_scenes("http://localhost:9999/graphql")
        >>> for scene in scenes:
        ...     print(f"Scene {scene['id']}: {scene['file_path']}")
    """
    try:
        import requests
    except ImportError:
        log("Error: requests module not available for query_interactive_scenes")
        return []
    
    query = """
    query FindScenes($filter: FindFilterType, $scene_filter: SceneFilterType) {
        findScenes(filter: $filter, scene_filter: $scene_filter) {
            count
            scenes {
                id
                title
                files {
                    path
                    fingerprints {
                        type
                        value
                    }
                }
                interactive
            }
        }
    }
    """
    
    variables = {
        "filter": {"per_page": -1},
        "scene_filter": {"interactive": True}
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(
            server_url,
            json={"query": query, "variables": variables},
            headers=headers,
            cookies=cookies,
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        
        if 'errors' in data:
            log(f"GraphQL errors: {data['errors']}")
            return []
        
        scenes = data.get('data', {}).get('findScenes', {}).get('scenes', [])
        log(f"Found {len(scenes)} interactive scenes")
        
        result = []
        for idx, scene in enumerate(scenes, 1):
            if idx % 100 == 0:
                log(f"  Processing scene {idx}/{len(scenes)}...")
            
            if not scene.get('files'):
                continue
            
            file = scene['files'][0]
            file_path = file['path']
            
            # Extract oshash fingerprint
            oshash = None
            for fp in file.get('fingerprints', []):
                if fp['type'] == 'oshash':
                    oshash = fp['value']
                    break
            
            if not oshash:
                continue
            
            # Check if scene has funscripts (if filtering enabled)
            if filter_has_funscripts:
                base_path = os.path.splitext(file_path)[0]
                scripts = find_funscript_paths(base_path)
                if not scripts:
                    continue
            
            result.append({
                'id': scene['id'],
                'title': scene.get('title', ''),
                'oshash': oshash,
                'file_path': file_path
            })
        
        log(f"Found {len(result)} scenes" + (" with funscripts" if filter_has_funscripts else ""))
        return result
    
    except (requests.RequestException, ValueError, KeyError) as e:
        log(f"Error querying scenes: {e}")
        return []


def merge_funscripts(scripts: Dict[str, Dict], target_version: str = '1.1') -> Dict:
    """
    Merge multiple funscript files into v1.1 or v2.0 format using funlib_py.
    
    This function combines a main stroke axis with additional motion axes (pitch, roll, sway, etc.)
    into a single merged funscript file in either v1.1 or v2.0 format.
    
    Args:
        scripts: Dictionary mapping axis names to funscript JSON data
                 Example: {'main': {...}, 'pitch': {...}, 'roll': {...}}
                 The 'main' axis (or 'stroke'/'L0') will be the primary axis
        target_version: Target funscript format version
                       '1.1' = TCode v0.3 format (traditional multi-axis)
                       '2.0' = TCode v0.4 format (channel-based)
    
    Returns:
        Merged funscript as a JSON-compatible dict in the target format
        
    Raises:
        ImportError: If funlib_py is not available
        
    Example:
        >>> main_data = read_funscript_json("Scene.funscript")
        >>> pitch_data = read_funscript_json("Scene.pitch.funscript")
        >>> merged = merge_funscripts({'main': main_data, 'pitch': pitch_data}, '2.0')
        >>> save_funscript("Scene.max.funscript", merged)
    
    Note:
        - The main axis is detected automatically from 'stroke', 'L0', or 'main' keys
        - If none found, the first axis in the dictionary is used as main
        - Additional axes are added as channels with their axis name as the channel ID
        - Empty channel data is filtered out automatically
    """
    try:
        from funlib_py import Funscript
    except ImportError:
        raise ImportError("funlib_py is required for merge_funscripts")
    
    # Find the main axis (stroke/L0/main take priority)
    main_axis = None
    for axis in ['stroke', 'L0', 'main']:
        if axis in scripts:
            main_axis = axis
            break
    
    if not main_axis:
        main_axis = list(scripts.keys())[0]
    
    main_script_data = scripts[main_axis]
    
    # Build channels list for additional axes
    channels_data = []
    for axis_name, script_data in scripts.items():
        if axis_name == main_axis:
            continue
        
        # Create channel with proper ID and channel name
        channel_script = dict(script_data)
        channel_script['id'] = axis_name
        channel_script['channel'] = axis_name
        channels_data.append(channel_script)
    
    # Create merged Funscript object
    if channels_data:
        merged = Funscript(main_script_data, {'channels': channels_data})
    else:
        merged = Funscript(main_script_data)
    
    # Export to target version
    result = merged.toJSON({'version': target_version})
    
    return result


def log(message):
    """
    Log progress message to stderr.

    Progress logs go to stderr so stdout remains clean for final JSON.
    Stash captures stderr based on errLog level setting in YAML.
    """
    print(message, file=sys.stderr, flush=True)


def load_plugin_settings(
    server_connection: Dict,
    plugin_name: str,
    default_settings: Dict
) -> Dict:
    """
    Load plugin settings from Stash's GraphQL configuration API.
    
    This function queries Stash's configuration to retrieve plugin-specific settings,
    falling back to defaults if the API is unavailable or settings are not configured.
    
    Args:
        server_connection: Stash server connection info dict containing:
                          - Scheme: 'http' or 'https'
                          - Host: Server hostname (default: 'localhost')
                          - Port: Server port (default: 9999)
                          - SessionCookie: Dict with 'Name' and 'Value' for auth
        plugin_name: Name of the plugin (e.g., 'alternateHeatmaps', 'funscriptMerger')
        default_settings: Dict of default setting values to use as fallback
    
    Returns:
        Dict containing the plugin settings (either from API or defaults)
        
    Example:
        >>> server_conn = {
        ...     'Scheme': 'http',
        ...     'Port': 9999,
        ...     'SessionCookie': {'Name': 'session', 'Value': 'abc123'}
        ... }
        >>> defaults = {'showChapters': True, 'supportMultipleScriptVersions': False}
        >>> settings = load_plugin_settings(server_conn, 'alternateHeatmaps', defaults)
        >>> print(settings['showChapters'])
        True
    
    Note:
        - Requires 'requests' library to be available
        - Automatically converts setting values to appropriate types (bool, int)
        - Logs warnings if settings cannot be loaded
        - Returns default_settings unmodified if API call fails
    """
    try:
        import requests
    except ImportError:
        log(f"Warning: requests module not available, using default settings")
        return default_settings.copy()
    
    scheme = server_connection.get('Scheme', 'http')
    host = server_connection.get('Host', 'localhost')
    port = server_connection.get('Port', 9999)
    session_cookie = server_connection.get('SessionCookie', {})
    
    cookies = None
    if session_cookie and session_cookie.get('Name') and session_cookie.get('Value'):
        cookies = {session_cookie['Name']: session_cookie['Value']}
    
    server_url = f"{scheme}://{host}:{port}/graphql"
    
    config_query = """
    query Configuration {
        configuration {
            plugins
        }
    }
    """
    
    try:
        response = requests.post(
            server_url,
            json={'query': config_query},
            headers={'Content-Type': 'application/json'},
            cookies=cookies,
            timeout=10
        )
        
        if response.status_code != 200:
            log(f"Warning: Configuration API returned status {response.status_code}, using defaults")
            return default_settings.copy()
        
        data = response.json()
        plugins_config = data.get('data', {}).get('configuration', {}).get('plugins', {})
        plugin_settings = plugins_config.get(plugin_name, {})
        
        if not plugin_settings:
            log(f"No settings found for {plugin_name}, using defaults")
            return default_settings.copy()
        
        # Merge plugin settings with defaults, preserving types
        settings = default_settings.copy()
        for key, default_value in default_settings.items():
            if key in plugin_settings:
                # Convert to appropriate type based on default
                if isinstance(default_value, bool):
                    settings[key] = bool(plugin_settings[key])
                elif isinstance(default_value, int):
                    settings[key] = int(plugin_settings[key])
                else:
                    settings[key] = plugin_settings[key]
        
        # Log loaded settings
        settings_str = ', '.join(f"{k}={v}" for k, v in settings.items())
        log(f"Loaded settings: {settings_str}")
        
        return settings
        
    except Exception as e:
        log(f"Warning: Could not load settings from configuration API: {e}")
        log("Using default settings")
        return default_settings.copy()

