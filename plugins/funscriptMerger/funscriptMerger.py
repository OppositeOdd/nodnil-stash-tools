#!/usr/bin/env python3
"""
Funscript Merger - Python Backend

Merges multi-axis funscripts into v1.1 or v2.0 format.
Handles file operations (move/delete originals).
"""

import os
import sys
import shutil
from typing import Dict

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'funUtil')
)
from funscript_utils import (
    find_funscript_paths,
    read_funscript_json,
    is_merged_funscript,
    save_funscript,
    read_stdin,
    write_stdout,
    log
)

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'funUtil')
)
from funlib_py import Funscript


def merge_funscripts(scripts: Dict[str, Dict], target_version: str = '1.1') -> Dict:
    """
    Merge funscripts into v1.1 or v2.0 format using funlib_py.

    Args:
        scripts: Dictionary of axis name to funscript data
        target_version: Target version ('1.1' or '2.0')

    Returns:
        Merged funscript in target format
    """
    import json

    main_axis = None
    for axis in ['stroke', 'L0', 'main']:
        if axis in scripts:
            main_axis = axis
            break

    if not main_axis:
        main_axis = list(scripts.keys())[0]

    main_script_data = scripts[main_axis]

    channels_data = []
    for axis_name, script_data in scripts.items():
        if axis_name == main_axis:
            continue


        channel_script = dict(script_data)
        channel_script['id'] = axis_name
        channel_script['channel'] = axis_name
        channels_data.append(channel_script)

    if channels_data:
        merged = Funscript(main_script_data, {'channels': channels_data})
    else:
        merged = Funscript(main_script_data)

    result = merged.toJSON({'version': target_version})

    return result


def handle_original_files(
    scripts: Dict[str, str],
    mode: int,
    base_path: str,
    max_path: str
):
    """
    Handle original funscript files based on mode.

    Args:
        scripts: Dictionary of axis name to file path
        mode: 0=keep, 1=move to folder, 2=delete
        base_path: Base path without extension
        max_path: Path to .max.funscript file
    """
    if mode == 0:
        log("  Mode 0: Keeping originals and .max.funscript")
        return

    if mode == 1:
        originals_dir = os.path.join(
            os.path.dirname(base_path),
            'originalFunscripts'
        )
        os.makedirs(originals_dir, exist_ok=True)

        for file_path in scripts.values():
            filename = os.path.basename(file_path)
            dest = os.path.join(originals_dir, filename)
            try:
                shutil.move(file_path, dest)
                log(f"  Moved {filename} to 'originalFunscripts/'")
            except (OSError, IOError) as e:
                log(f"  Error moving {file_path}: {e}")

        final_path = f"{base_path}.funscript"
        try:
            shutil.move(max_path, final_path)
            log("  Renamed .max.funscript to .funscript")
        except (OSError, IOError) as e:
            log(f"  Error renaming: {e}")

    elif mode == 2:
        for file_path in scripts.values():
            try:
                os.remove(file_path)
                log(f"  Deleted {os.path.basename(file_path)}")
            except (OSError, IOError) as e:
                log(f"  Error deleting {file_path}: {e}")

        final_path = f"{base_path}.funscript"
        try:
            shutil.move(max_path, final_path)
            log("  Renamed .max.funscript to .funscript")
        except (OSError, IOError) as e:
            log(f"  Error renaming: {e}")


def process_scene(
    scene_id: str,
    base_path: str,
    settings: Dict
) -> bool:
    """
    Process a scene to merge multi-axis funscripts.

    Args:
        scene_id: Stash scene ID
        base_path: Base path to funscript files
        settings: Plugin settings dict

    Returns:
        True if merged successfully, False if skipped or error
    """
    log(
        f"Processing scene {scene_id}: "
        f"{os.path.basename(base_path)}"
    )

    merge_mode = settings.get('mergingMode', 1)

    if merge_mode == 0:
        log("  ⊘ Merging disabled (mode 0), skipping")
        return False

    max_path = f"{base_path}.max.funscript"
    main_path = f"{base_path}.funscript"
    file_mode = settings.get('fileHandlingMode', 0)

    if os.path.exists(max_path):
        from funscript_utils import get_funscript_version, convert_funscript_format, get_merged_channels

        data = read_funscript_json(max_path)
        if not data:
            log("  ✗ Error: Could not read .max.funscript")
            return False

        current_version = get_funscript_version(data)
        target_version = '1.1' if merge_mode == 1 else '2.0'
        needs_conversion = current_version != target_version

        if needs_conversion:
            log(f"  ⟳ Converting .max.funscript from v{current_version} to v{target_version}...")
            converted = convert_funscript_format(data, target_version)
            if not converted:
                log("  ✗ Failed to convert .max.funscript")
                return False
            merged_channels = get_merged_channels(converted)
        else:

            merged_channels = get_merged_channels(data)
            converted = data

        log(f"  → Merged script contains: {', '.join(merged_channels) if merged_channels else 'stroke only'}")

        scripts_to_handle = {}

        if os.path.exists(main_path):
            scripts_to_handle['main'] = main_path

        for channel in merged_channels:
            channel_path = f"{base_path}.{channel}.funscript"
            if os.path.exists(channel_path):
                scripts_to_handle[channel] = channel_path

        originals_dir = os.path.join(os.path.dirname(base_path), 'originalFunscripts')
        if os.path.exists(originals_dir):
            base_name = os.path.basename(base_path)
            original_main = os.path.join(originals_dir, f"{base_name}.funscript")
            if os.path.exists(original_main) and 'main' not in scripts_to_handle:
                scripts_to_handle['main'] = original_main

            for channel in merged_channels:
                original_channel = os.path.join(originals_dir, f"{base_name}.{channel}.funscript")
                if os.path.exists(original_channel) and channel not in scripts_to_handle:
                    scripts_to_handle[channel] = original_channel

        if not needs_conversion and not scripts_to_handle:
            log(f"  ⊘ .max.funscript already in v{target_version} format and no originals to handle, skipping")
            return False

        if needs_conversion:
            if not save_funscript(max_path, converted):
                log("  ✗ Failed to save converted .max.funscript")
                return False
            log(f"  ✓ Converted to v{target_version} format")

        if file_mode == 0:
            log("  → Mode 0: Keeping .max.funscript and originals")
            return needs_conversion

        elif file_mode == 1:
            if scripts_to_handle:
                originals_dir = os.path.join(os.path.dirname(base_path), 'originalFunscripts')
                os.makedirs(originals_dir, exist_ok=True)

                for axis, file_path in scripts_to_handle.items():
                    if 'originalFunscripts' in file_path:
                        continue

                    filename = os.path.basename(file_path)
                    dest = os.path.join(originals_dir, filename)
                    try:
                        shutil.move(file_path, dest)
                        log(f"  → Moved {filename} to originalFunscripts/")
                    except (OSError, IOError) as e:
                        log(f"  ✗ Error moving {filename}: {e}")

            try:
                if os.path.exists(main_path):
                    os.remove(main_path)
                shutil.move(max_path, main_path)
                log(f"  ✓ Renamed .max.funscript to .funscript")
                return True
            except (OSError, IOError) as e:
                log(f"  ✗ Error renaming .max.funscript: {e}")
                return False

        elif file_mode == 2:
            if scripts_to_handle:
                for axis, file_path in scripts_to_handle.items():
                    try:
                        os.remove(file_path)
                        log(f"  → Deleted {os.path.basename(file_path)}")
                    except (OSError, IOError) as e:
                        log(f"  ✗ Error deleting {os.path.basename(file_path)}: {e}")

            try:
                if os.path.exists(main_path):
                    os.remove(main_path)
                shutil.move(max_path, main_path)
                log(f"  ✓ Renamed .max.funscript to .funscript")
                return True
            except (OSError, IOError) as e:
                log(f"  ✗ Error renaming .max.funscript: {e}")
                return False

    scripts_paths = find_funscript_paths(base_path)

    if not scripts_paths:
        log("  ⊘ No funscripts found")
        return False

    if len(scripts_paths) == 1:
        single_path = list(scripts_paths.values())[0]
        data = read_funscript_json(single_path)
        if data and is_merged_funscript(data):
            from funscript_utils import get_funscript_version, convert_funscript_format

            current_version = get_funscript_version(data)
            target_version = '1.1' if merge_mode == 1 else '2.0'

            if current_version == target_version:
                log(f"  ⊘ Already in v{target_version} format, skipping")
                return False

            log(f"  ⟳ Converting from v{current_version} to v{target_version}...")
            converted = convert_funscript_format(data, target_version)

            if converted and save_funscript(single_path, converted):
                log(f"  ✓ Converted to v{target_version} format")
                return True
            else:
                log("  ✗ Failed to convert format")
                return False

        log("  ⊘ Single funscript found, skipping merge")
        return False

    if 'main' in scripts_paths:
        main_data = read_funscript_json(scripts_paths['main'])
        if main_data and is_merged_funscript(main_data):
            from funscript_utils import get_funscript_version, get_merged_channels, unmerge_funscript

            log("  → Main funscript is already merged, but found additional axis files")
            merged_channels = get_merged_channels(main_data)
            log(f"  → Merged script contains: {', '.join(merged_channels) if merged_channels else 'stroke only'}")

            originals_dir = os.path.join(os.path.dirname(base_path), 'originalFunscripts')
            base_name = os.path.basename(base_path)
            original_scripts = {}

            original_main = os.path.join(originals_dir, f"{base_name}.funscript")
            if os.path.exists(original_main):
                original_scripts['main'] = original_main

            for channel in merged_channels:
                original_channel = os.path.join(originals_dir, f"{base_name}.{channel}.funscript")
                if os.path.exists(original_channel):
                    original_scripts[channel] = original_channel

            all_originals_found = 'main' in original_scripts and all(
                channel in original_scripts for channel in merged_channels)

            if all_originals_found:
                log(f"  ✓ Found all {len(original_scripts)} original 1.0 scripts in originalFunscripts/")
                log("  → Deleting merged script and recreating from originals + new axes")

                try:
                    os.remove(scripts_paths['main'])
                    log(f"  → Deleted merged {os.path.basename(scripts_paths['main'])}")
                except (OSError, IOError) as e:
                    log(f"  ✗ Error deleting merged script: {e}")
                    return False

                for axis, original_path in original_scripts.items():
                    dest_name = os.path.basename(original_path)
                    dest_path = os.path.join(os.path.dirname(base_path), dest_name)
                    try:
                        shutil.move(original_path, dest_path)
                        log(f"  → Moved {dest_name} from originalFunscripts/")
                    except (OSError, IOError) as e:
                        log(f"  ✗ Error moving {dest_name}: {e}")
                        return False

                scripts_paths = find_funscript_paths(base_path)
                if not scripts_paths:
                    log("  ✗ Error: No scripts found after cleanup")
                    return False

                log(f"  → Re-scanning: found {len(scripts_paths)} funscripts to merge")

            else:
                log("  ⚠ Original 1.0 scripts not found, will unmerge to extract them")

                if not scripts_paths['main'].endswith('.max.funscript'):
                    try:
                        shutil.move(scripts_paths['main'], max_path)
                        log(f"  → Renamed to .max.funscript for unmerging")
                    except (OSError, IOError) as e:
                        log(f"  ✗ Error renaming to .max.funscript: {e}")
                        return False
                else:
                    max_path = scripts_paths['main']

                log(f"  ⟳ Unmerging v{get_funscript_version(main_data)} script...")
                saved_files = unmerge_funscript(main_data, base_path)

                if not saved_files:
                    log("  ✗ Unmerge failed")
                    return False

                log(f"  ✓ Extracted {len(saved_files)} v1.0 scripts:")
                for channel, path in saved_files.items():
                    log(f"     - {os.path.basename(path)}")

                try:
                    os.remove(max_path)
                    log(f"  → Deleted merged script after unmerge")
                except (OSError, IOError) as e:
                    log(f"  ✗ Error deleting merged script: {e}")

                scripts_paths = find_funscript_paths(base_path)
                if not scripts_paths:
                    log("  ✗ Error: No scripts found after unmerge")
                    return False

                log(f"  → Re-scanning: found {len(scripts_paths)} funscripts to merge")

    log(
        f"  → Found {len(scripts_paths)} funscripts: "
        f"{', '.join(scripts_paths.keys())}"
    )

    scripts_data = {}
    for axis, path in scripts_paths.items():
        data = read_funscript_json(path)
        if data:
            scripts_data[axis] = data

    if not scripts_data:
        log("  ✗ Error: Could not read any funscripts")
        return False

    target_version = '1.1' if merge_mode == 1 else '2.0'
    log(
        f"  ⟳ Merging to v{target_version} format"
        + (" (requires MFP v1.33.9+ or XTP v0.55b+)..." if target_version == '2.0' else "...")
    )
    merged = merge_funscripts(scripts_data, target_version)

    if save_funscript(max_path, merged):
        log(f"  ✓ Saved merged funscript: {os.path.basename(max_path)}")
    else:
        log("  ✗ Failed to save merged funscript")
        return False

    file_mode = settings.get('fileHandlingMode', 0)
    handle_original_files(scripts_paths, file_mode, base_path, max_path)

    return True


def unmerge_scene(
    scene_id: str,
    base_path: str,
    settings: Dict
) -> bool:
    """
    Unmerge a merged funscript into separate v1.0 files.

    Args:
        scene_id: Stash scene ID
        base_path: Base path to funscript files
        settings: Plugin settings dict

    Returns:
        True if unmerged successfully, False if skipped or error
    """
    from funscript_utils import (
        get_funscript_version,
        get_merged_channels,
        unmerge_funscript
    )

    log(
        f"Processing scene {scene_id}: "
        f"{os.path.basename(base_path)}"
    )

    enable_unmerge = settings.get('enableUnmerge', False)
    if not enable_unmerge:
        log("  ⊘ Unmerge disabled in settings, skipping")
        return False

    main_path = f"{base_path}.funscript"
    if not os.path.exists(main_path):
        log("  ⊘ No main funscript found")
        return False

    data = read_funscript_json(main_path)
    if not data:
        log("  ✗ Error: Could not read funscript")
        return False

    version = get_funscript_version(data)
    if version == '1.0':
        log("  ⊘ Not a merged funscript, skipping")
        return False

    merged_channels = get_merged_channels(data)
    log(f"  → Merged script contains: {', '.join(merged_channels)}")

    existing_files = []
    file_mode = settings.get('fileHandlingMode', 0)

    for channel in merged_channels:
        channel_path = f"{base_path}.{channel}.funscript"
        if os.path.exists(channel_path):
            existing_files.append(channel)

    if file_mode == 1:
        originals_dir = os.path.join(
            os.path.dirname(base_path),
            'originalFunscripts'
        )
        if os.path.exists(originals_dir):
            for channel in merged_channels:
                filename = f"{os.path.basename(base_path)}.{channel}.funscript"
                channel_path = os.path.join(originals_dir, filename)
                if os.path.exists(channel_path) and channel not in existing_files:
                    existing_files.append(channel)

    if existing_files:
        log(f"  ⊘ Files already exist: {', '.join(existing_files)}")
        return False

    max_path = f"{base_path}.max.funscript"
    try:
        shutil.move(main_path, max_path)
        log(f"  → Renamed {os.path.basename(main_path)} to .max.funscript")
    except (OSError, IOError) as e:
        log(f"  ✗ Error renaming: {e}")
        return False

    log(f"  ⟳ Splitting v{version} merged script...")
    saved_files = unmerge_funscript(data, base_path)

    if saved_files:
        log(f"  ✓ Created {len(saved_files)} funscript files:")
        for channel, path in saved_files.items():
            log(f"     - {os.path.basename(path)}")

        try:
            os.remove(max_path)
            log(f"  → Deleted merged script after unmerge")
        except (OSError, IOError) as e:
            log(f"  ✗ Warning: Could not delete merged script: {e}")
        return True
    else:
        try:
            shutil.move(max_path, main_path)
            log("  ✗ Unmerge failed, restored original")
        except (OSError, IOError):
            log("  ✗ Unmerge failed, could not restore original")
        return False


def query_interactive_scenes(server_url: str, cookies: Dict = None):
    """
    Query Stash for all interactive scenes.

    Args:
        server_url: Stash GraphQL endpoint
        cookies: Session cookies for authentication

    Returns:
        List of scenes with interactive funscripts
    """
    import requests

    query = """
    query FindScenes($filter: FindFilterType) {
        findScenes(filter: $filter, scene_filter: {interactive: true}) {
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
            }
        }
    }
    """

    variables = {
        "filter": {
            "per_page": -1
        }
    }

    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(
            server_url,
            json={'query': query, 'variables': variables},
            headers=headers,
            cookies=cookies,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if 'errors' in data:
            log(f"GraphQL errors: {data['errors']}")
            return []

        scenes = data.get('data', {}).get('findScenes', {}).get('scenes', [])
        return scenes

    except requests.exceptions.RequestException as e:
        log(f"Error querying Stash: {e}")
        return []


def batch_merge_scenes(server_connection: Dict, settings: Dict):
    """
    Batch process all interactive scenes for merging.

    Args:
        server_connection: Stash server connection info
        settings: Plugin settings
    """
    scheme = server_connection.get('Scheme', 'http')
    port = server_connection.get('Port', 9999)
    session_cookie = server_connection.get('SessionCookie', {})

    # Build cookies dict from session cookie
    cookies = None
    if session_cookie and session_cookie.get('Name') and session_cookie.get('Value'):
        cookies = {session_cookie['Name']: session_cookie['Value']}

    server_url = f"{scheme}://localhost:{port}/graphql"

    log("=" * 60)
    log("Funscript Merger - Batch Processing")
    log("=" * 60)
    log("Querying Stash for interactive scenes...")

    scenes = query_interactive_scenes(server_url, cookies)

    if not scenes:
        log("No interactive scenes found")
        return

    log(f"Found {len(scenes)} interactive scene(s)")
    log("")

    merged_count = 0
    skipped_count = 0
    error_count = 0

    for idx, scene in enumerate(scenes, 1):
        scene_id = scene.get('id')
        title = scene.get('title', 'Untitled')
        files = scene.get('files', [])

        if not files:
            log(f"[{idx}/{len(scenes)}] Scene {scene_id}: No files")
            skipped_count += 1
            continue

        video_path = files[0].get('path')
        if not video_path:
            log(f"[{idx}/{len(scenes)}] Scene {scene_id}: No path")
            skipped_count += 1
            continue

        base_path = os.path.splitext(video_path)[0]

        log(f"[{idx}/{len(scenes)}] {title}")

        try:
            if process_scene(scene_id, base_path, settings):
                merged_count += 1
            else:
                skipped_count += 1
        except Exception as e:
            log(f"  ✗ Error: {e}")
            error_count += 1

        log("")

    log("=" * 60)
    log("Summary:")
    log(f"  Merged:  {merged_count}")
    log(f"  Skipped: {skipped_count}")
    log(f"  Errors:  {error_count}")
    log("=" * 60)


def batch_unmerge_scenes(server_connection: Dict, settings: Dict):
    """
    Batch process all interactive scenes for unmerging.

    Args:
        server_connection: Stash server connection info
        settings: Plugin settings
    """
    scheme = server_connection.get('Scheme', 'http')
    port = server_connection.get('Port', 9999)
    session_cookie = server_connection.get('SessionCookie', {})

    cookies = None
    if session_cookie and session_cookie.get('Name') and session_cookie.get('Value'):
        cookies = {session_cookie['Name']: session_cookie['Value']}

    server_url = f"{scheme}://localhost:{port}/graphql"

    log("=" * 60)
    log("Funscript Merger - Batch Unmerge (Experimental)")
    log("=" * 60)
    log("Querying Stash for interactive scenes...")

    scenes = query_interactive_scenes(server_url, cookies)

    if not scenes:
        log("No interactive scenes found")
        return

    log(f"Found {len(scenes)} interactive scene(s)")
    log("")

    unmerged_count = 0
    skipped_count = 0
    error_count = 0

    for idx, scene in enumerate(scenes, 1):
        scene_id = scene.get('id')
        title = scene.get('title', 'Untitled')
        files = scene.get('files', [])

        if not files:
            log(f"[{idx}/{len(scenes)}] Scene {scene_id}: No files")
            skipped_count += 1
            continue

        video_path = files[0].get('path')
        if not video_path:
            log(f"[{idx}/{len(scenes)}] Scene {scene_id}: No path")
            skipped_count += 1
            continue

        base_path = os.path.splitext(video_path)[0]

        log(f"[{idx}/{len(scenes)}] {title}")

        try:
            if unmerge_scene(scene_id, base_path, settings):
                unmerged_count += 1
            else:
                skipped_count += 1
        except Exception as e:
            log(f"  ✗ Error: {e}")
            error_count += 1

        log("")

    log("=" * 60)
    log("Summary:")
    log(f"  Unmerged: {unmerged_count}")
    log(f"  Skipped:  {skipped_count}")
    log(f"  Errors:   {error_count}")
    log("=" * 60)


def main():
    """Main entry point for funscript merger."""
    try:
        input_data = read_stdin()
        args = input_data.get('args', {})
        mode = args.get('mode')
        server_connection = input_data.get('server_connection', {})

        settings = {
            'mergingMode': 1,
            'fileHandlingMode': 0,
            'enableUnmerge': False
        }

        try:
            import requests
            scheme = server_connection.get('Scheme', 'http')
            port = server_connection.get('Port', 9999)
            session_cookie = server_connection.get('SessionCookie', {})

            cookies = None
            if session_cookie and session_cookie.get('Name') and session_cookie.get('Value'):
                cookies = {session_cookie['Name']: session_cookie['Value']}

            server_url = f"{scheme}://localhost:{port}/graphql"

            config_query = """
            query Configuration {
                configuration {
                    plugins
                }
            }
            """

            response = requests.post(
                server_url,
                json={'query': config_query},
                headers={'Content-Type': 'application/json'},
                cookies=cookies,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                plugins_config = data.get('data', {}).get('configuration', {}).get('plugins', {})
                plugin_settings = plugins_config.get('funscriptMerger', {})

                if plugin_settings:
                    settings['mergingMode'] = int(plugin_settings.get('mergingMode', 1))
                    settings['fileHandlingMode'] = int(plugin_settings.get('fileHandlingMode', 0))
                    settings['enableUnmerge'] = bool(plugin_settings.get('enableUnmerge', False))
                    log(
                        f"Loaded settings: mergingMode={settings['mergingMode']}, "
                        f"fileHandlingMode={settings['fileHandlingMode']}, "
                        f"enableUnmerge={settings['enableUnmerge']}"
                    )
        except Exception as e:
            log(f"Could not load plugin settings, using defaults: {e}")

        if mode == 'merge_all':
            batch_merge_scenes(server_connection, settings)
            write_stdout({
                "output": "Batch merge completed",
                "error": None
            })
        elif mode == 'unmerge_all':
            batch_unmerge_scenes(server_connection, settings)
            write_stdout({
                "output": "Batch unmerge completed",
                "error": None
            })
        else:
            write_stdout({
                "output": None,
                "error": f"Unknown mode: {mode}"
            })

    except Exception as e:
        write_stdout({
            "output": None,
            "error": str(e)
        })
        sys.exit(1)


if __name__ == '__main__':
    main()
