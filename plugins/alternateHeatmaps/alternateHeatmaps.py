#!/usr/bin/env python3
"""
Alternate Heatmaps - Python Backend

Generates heatmap SVGs from funscripts using funlib.
Supports both merged and multi-file funscripts.
"""

import sys
import os
import json
import traceback
from typing import Dict, List, Tuple

# TEST MODE: Set to True to limit batch processing to 10 scenes
TEST_MODE = False

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'funUtil')
)
from funscript_utils import (  # noqa: E402
    find_funscript_paths,
    read_funscript_json,
    is_merged_funscript,
    read_stdin,
    write_stdout,
    log,
    AXIS_EXTENSIONS
)

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'funUtil')
)
from funlib_py import Funscript  # noqa: E402


KNOWN_AXES = set(AXIS_EXTENSIONS)


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


def find_script_variants(directory: str, base_name: str) -> Tuple[Dict[str, Dict], List[str]]:
    variants = {}
    axis_scripts = []

    try:
        all_files = os.listdir(directory)
    except OSError:
        return {}, []

    all_scripts = []
    for filename in all_files:
        if filename.startswith(base_name) and filename.endswith('.funscript'):
            all_scripts.append(filename)

    for filename in all_scripts:
        is_axis = False
        for axis in KNOWN_AXES:
            if filename == f"{base_name}.{axis}.funscript":
                axis_scripts.append(filename)
                is_axis = True
                break

        if is_axis:
            continue

        variant_suffix = extract_variant_suffix(filename, base_name)

        if variant_suffix is None:
            continue

        variant_key = variant_suffix if variant_suffix else "default"
        variants[variant_key] = {
            'filename': filename,
            'suffix': variant_suffix,
            'path': os.path.join(directory, filename)
        }

    return variants, axis_scripts


def generate_heatmap_python(
    funscript_data: Dict,
    output_path: str,
    heatmap_type: str = 'overlay',
    show_chapters: bool = True
) -> bool:
    """
    Generate heatmap using Python funlib port.

    Args:
        funscript_data: Funscript JSON data
        output_path: Path to save SVG file
        heatmap_type: 'overlay' (compact) or 'full' (with stats)
        show_chapters: Whether to include chapter bar

    Returns:
        True if successful, False otherwise
    """
    try:
        from funlib_py.svg import toSvgElement, SvgOptions

        script = Funscript(funscript_data)

        # Extract title from funscript metadata or filename
        title = ''
        if 'metadata' in funscript_data and 'title' in funscript_data['metadata']:
            title = funscript_data['metadata']['title']
        elif hasattr(script, 'metadata') and hasattr(script.metadata, 'title'):
            title = script.metadata.title
        elif 'metadata' in funscript_data and 'script_url' in funscript_data['metadata']:
            import os
            title = os.path.basename(funscript_data['metadata']['script_url'])

        if heatmap_type == 'overlay':
            # Compact overlay for video scrubber - no title, no axis labels, just heatmap
            ops = SvgOptions(
                title='',  # No title for overlay
                lineWidth=0.5,
                graphOpacity=0.7,
                titleOpacity=0,
                mergeLimit=500,
                showChapters=show_chapters,
                normalize=True,
                width=1176,  # Wide overlay for video player scrubber
                height=19,  # Slim height for overlay
                titleHeight=0,
                iconWidth=0,  # No axis labels for simple overlay
                chapterHeight=6 if show_chapters else 0
            )
        else:
            # Full heatmap with stats and title
            ops = SvgOptions(
                title=title if title else None,  # Show filename as title
                lineWidth=0.5,
                graphOpacity=0.2,
                titleOpacity=0.7,
                mergeLimit=500,
                showChapters=show_chapters,
                normalize=True,
                width=1380,  # Double standard width
                height=104,  # Double standard height
                titleHeight=40,  # Double standard title
                iconWidth=92,  # Double icon width
                chapterHeight=20 if show_chapters else 0
            )

        svg_content = toSvgElement(script, ops)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)

        return True

    except Exception as e:
        log(f"Error generating Python heatmap: {e}")
        import traceback
        log(traceback.format_exc())
        return False


def generate_heatmap(
    scene_id: str,
    base_path: str,
    oshash: str,
    settings: Dict,
    heatmap_dir: str
) -> bool:
    """
    Generate heatmap SVG from funscript(s).

    Tries merged funscript first, falls back to merging multiple files.

    Args:
        scene_id: Stash scene ID
        base_path: Base path to funscript files (without extension)
        oshash: Scene oshash for heatmap filename
        settings: Plugin settings (showChapters, etc.)
        heatmap_dir: Directory to save heatmap SVG

    Returns:
        True if successful, False otherwise
    """
    log(
        f"Generating heatmap for scene {scene_id}: "
        f"{os.path.basename(base_path)}"
    )

    show_chapters = settings.get('showChapters', True)

    merged_candidates = [
        f"{base_path}.max.funscript",
        f"{base_path}.funscript"
    ]

    funscript_data = None
    funscript_filename = None
    for merged_path in merged_candidates:
        if os.path.exists(merged_path):
            log(f"  Found {os.path.basename(merged_path)}")
            data = read_funscript_json(merged_path)
            if data and is_merged_funscript(data):
                log(
                    f"  Using merged funscript: "
                    f"{os.path.basename(merged_path)}"
                )
                funscript_data = data
                funscript_filename = os.path.basename(merged_path)
                break
            elif data:
                log(
                    f"  {os.path.basename(merged_path)} is single-axis "
                    f"v1.0, checking for multi-axis files"
                )

    # If no merged file found, look for individual axis files
    if not funscript_data:
        log("  No merged funscript found, searching for individual files")
        scripts_paths = find_funscript_paths(base_path)

        if not scripts_paths:
            log("  No funscripts found")
            return False

        if len(scripts_paths) == 1:
            single_key = list(scripts_paths.keys())[0]
            single_path = list(scripts_paths.values())[0]
            log(f"  Using single funscript: {single_key}")
            funscript_data = read_funscript_json(single_path)
            funscript_filename = os.path.basename(single_path)
            if not funscript_data:
                return False
        else:
            log(
                f"  Found {len(scripts_paths)} funscripts: "
                f"{', '.join(scripts_paths.keys())}"
            )
            log("  Creating temporary merge for heatmap generation")

            scripts_data = {}
            for axis, path in scripts_paths.items():
                data = read_funscript_json(path)
                if data:
                    scripts_data[axis] = data

            if not scripts_data:
                log("  Error: Could not read any funscripts")
                return False

            # Merge using funlib_py
            log("  ⟳ Merging multi-axis scripts...")
            main_axis = None
            for axis in ['stroke', 'L0', 'main']:
                if axis in scripts_data:
                    main_axis = axis
                    break

            if not main_axis:
                main_axis = list(scripts_data.keys())[0]

            main_script_data = scripts_data[main_axis]
            channels_data = []
            for axis_name, script_data in scripts_data.items():
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

            funscript_data = merged.toJSON({'version': '2.0'})
            funscript_filename = f"{os.path.basename(base_path)}.funscript"

    # Add filename to metadata if not present
    if funscript_data and funscript_filename:
        if 'metadata' not in funscript_data:
            funscript_data['metadata'] = {}
        if 'title' not in funscript_data['metadata']:
            funscript_data['metadata']['title'] = funscript_filename

    overlay_path = os.path.join(heatmap_dir, oshash, f"{oshash}.svg")
    full_path = os.path.join(heatmap_dir, oshash, f"{oshash}_full.svg")
    
    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)

    log("  ⟳ Generating heatmaps...")
    overlay_success = generate_heatmap_python(
        funscript_data,
        overlay_path,
        'overlay',
        show_chapters
    )
    full_success = generate_heatmap_python(
        funscript_data,
        full_path,
        'full',
        show_chapters
    )

    if overlay_success:
        log(f"  ✓ Saved overlay: {oshash}.svg")
    else:
        log("  ✗ Failed to generate overlay")

    if full_success:
        log(f"  ✓ Saved full heatmap: {oshash}_full.svg")
    else:
        log("  ✗ Failed to generate full heatmap")

    return overlay_success and full_success


def generate_heatmaps_with_variants(
    base_path: str,
    oshash: str,
    heatmap_dir: str,
    show_chapters: bool = True,
    support_variants: bool = False
) -> bool:
    directory = os.path.dirname(base_path)
    base_name = os.path.basename(base_path)
    
    oshash_dir = os.path.join(heatmap_dir, oshash)
    os.makedirs(oshash_dir, exist_ok=True)
    
    if not support_variants:
        return generate_heatmap(base_path, oshash, heatmap_dir, show_chapters)
    
    variants, axis_scripts = find_script_variants(directory, base_name)
    
    if not variants:
        log("  ⊘ No funscript variants found")
        return False
    
    log(f"  → Found {len(variants)} variant(s): {', '.join(variants.keys())}")
    if axis_scripts:
        log(f"  → Found {len(axis_scripts)} axis script(s) (excluded from heatmaps)")
    
    mapping = {
        "oshash": oshash,
        "default": None,
        "variants": []
    }
    
    success_count = 0
    
    for idx, (variant_key, variant_data) in enumerate(sorted(variants.items())):
        variant_filename = variant_data['filename']
        variant_path = variant_data['path']
        is_default = variant_key == "default"
        
        if is_default:
            variant_id = ""
            suffix_display = ""
        else:
            variant_id = f"_var{idx}"
            suffix_display = f" ({variant_key})"
        
        log(f"  ⟳ Generating heatmaps for{suffix_display}...")
        
        scripts_paths = find_funscript_paths(variant_path)
        
        if not scripts_paths:
            log(f"  ✗ No funscript data found for{suffix_display}")
            continue
        
        funscript_data = None
        
        if len(scripts_paths) == 1:
            funscript_data = read_funscript_json(scripts_paths[0])
        else:
            scripts_data = {}
            for script_path in scripts_paths:
                data = read_funscript_json(script_path)
                if data:
                    axis_name = 'main'
                    for axis in KNOWN_AXES:
                        if script_path.endswith(f".{axis}.funscript"):
                            axis_name = axis
                            break
                    scripts_data[axis_name] = data
            
            if scripts_data:
                merged = Funscript.fromList(list(scripts_data.values()))
                funscript_data = merged.toJSON({'version': '2.0'})
        
        if not funscript_data:
            log(f"  ✗ Could not read funscript data for{suffix_display}")
            continue
        
        if 'metadata' not in funscript_data:
            funscript_data['metadata'] = {}
        if 'title' not in funscript_data['metadata']:
            funscript_data['metadata']['title'] = variant_filename
        
        overlay_path = os.path.join(oshash_dir, f"{oshash}{variant_id}.svg")
        full_path = os.path.join(oshash_dir, f"{oshash}{variant_id}_full.svg")
        
        overlay_success = generate_heatmap_python(
            funscript_data,
            overlay_path,
            'overlay',
            show_chapters
        )
        full_success = generate_heatmap_python(
            funscript_data,
            full_path,
            'full',
            show_chapters
        )
        
        if overlay_success and full_success:
            log(f"  ✓ Saved heatmaps for{suffix_display}")
            success_count += 1
            
            if is_default:
                mapping["default"] = variant_filename
            else:
                mapping["variants"].append({
                    "id": variant_id.lstrip("_"),
                    "path": variant_filename,
                    "suffix": variant_data['suffix']
                })
        else:
            log(f"  ✗ Failed to generate heatmaps for{suffix_display}")
    
    if success_count > 0:
        map_path = os.path.join(oshash_dir, f"{oshash}_map.json")
        with open(map_path, 'w') as f:
            json.dump(mapping, f, indent=2)
        log(f"  ✓ Saved mapping file")
        return True
    
    return False


def query_interactive_scenes(server_url: str, cookies: Dict = None) -> list:
    """
    Query Stash for all interactive scenes using GraphQL.

    Returns:
        List of dicts with scene_id, oshash, and file path
    """
    import requests  # type: ignore

    query = """
    query FindScenes($filter: FindFilterType, $scene_filter: SceneFilterType) {
        findScenes(filter: $filter, scene_filter: $scene_filter) {
            count
            scenes {
                id
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

        scenes = data.get('data', {}).get('findScenes', {}).get('scenes', [])
        log(f"Found {len(scenes)} interactive scenes")

        result = []
        for scene in scenes:
            if not scene.get('files'):
                continue

            file = scene['files'][0]
            file_path = file['path']

            # Extract oshash from fingerprints
            oshash = None
            for fp in file.get('fingerprints', []):
                if fp['type'] == 'oshash':
                    oshash = fp['value']
                    break

            if not oshash:
                continue

            # Check if funscripts exist
            base_path = os.path.splitext(file_path)[0]
            scripts = find_funscript_paths(base_path)

            if scripts:
                result.append({
                    'scene_id': scene['id'],
                    'oshash': oshash,
                    'file_path': file_path
                })

        log(f"Found {len(result)} scenes with funscripts")
        return result

    except (requests.RequestException, ValueError, KeyError) as e:
        log(f"Error querying scenes: {e}")
        return []


def main():
    """
    Main entry point for heatmap generation tasks.

    Expected input format:
    {
        "server_connection": {...},
        "args": {
            "mode": "generate_all",
            "showChapters": <optional, default true>
        }
    }
    """
    try:
        input_data = read_stdin()
        server_connection = input_data.get('server_connection', {})
        plugin_dir = server_connection.get('PluginDir', '')
        scheme = server_connection.get('Scheme', 'http')
        host = server_connection.get('Host', 'localhost')
        port = server_connection.get('Port', 9999)
        session_cookie = server_connection.get('SessionCookie', {})

        # Build cookies dict from session cookie
        cookies = None
        if session_cookie and session_cookie.get('Name') and session_cookie.get('Value'):
            cookies = {session_cookie['Name']: session_cookie['Value']}

        args = input_data.get('args', {})
        mode = args.get('mode', 'generate_all')

        # Get heatmap directory from funUtil plugin
        heatmap_dir = os.path.join(
            os.path.dirname(plugin_dir),
            'funUtil',
            'assets',
            'heatmaps'
        )
        os.makedirs(heatmap_dir, exist_ok=True)

        # Get settings from GraphQL configuration API
        server_url = f"{scheme}://{host}:{port}/graphql"
        settings = {
            'showChapters': True,
            'supportMultipleScriptVersions': False
        }

        try:
            import requests  # type: ignore

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
                plugin_settings = plugins_config.get('alternateHeatmaps', {})

                if plugin_settings:
                    settings['showChapters'] = bool(plugin_settings.get('showChapters', True))
                    settings['supportMultipleScriptVersions'] = bool(plugin_settings.get('supportMultipleScriptVersions', False))
                    log(f"Loaded settings: showChapters={settings['showChapters']}, supportMultipleScriptVersions={settings['supportMultipleScriptVersions']}")
        except Exception as e:
            log(f"Warning: Could not load settings from configuration API: {e}")
            log("Using default settings")

        if mode == 'generate_all':
            log("=" * 60)
            log("Alternate Heatmaps - Batch Processing")
            log("=" * 60)
            log("Querying Stash for interactive scenes...")

            scenes = query_interactive_scenes(server_url, cookies)

            if not scenes:
                log("No interactive scenes with funscripts found")
                write_stdout({
                    "output": "No interactive scenes with funscripts found",
                    "error": None
                })
                return

            log(f"Found {len(scenes)} scene(s) with funscripts")
            log("")

            success_count = 0
            failed_count = 0
            skipped_count = 0

            for idx, scene in enumerate(scenes, 1):
                if TEST_MODE and idx > 10:
                    log("TEST MODE: Stopping after 10 scenes")
                    break

                scene_id = scene['scene_id']
                oshash = scene['oshash']
                file_path = scene['file_path']
                base_path = os.path.splitext(file_path)[0]
                filename = os.path.basename(file_path)

                log(f"[{idx}/{len(scenes)}] {filename}")

                oshash_dir = os.path.join(heatmap_dir, oshash)
                map_path = os.path.join(oshash_dir, f"{oshash}_map.json")
                
                if os.path.exists(map_path):
                    log("  ⊘ Heatmaps already exist, skipping")
                    skipped_count += 1
                    log("")
                    continue

                success = generate_heatmaps_with_variants(
                    base_path,
                    oshash,
                    heatmap_dir,
                    settings['showChapters'],
                    settings.get('supportMultipleScriptVersions', False)
                )

                if success:
                    success_count += 1
                else:
                    failed_count += 1

                log("")

            log("=" * 60)
            log("Summary:")
            log(f"  Generated: {success_count}")
            log(f"  Skipped:   {skipped_count}")
            log(f"  Failed:    {failed_count}")
            log("=" * 60)

            summary = (
                f"Batch processing complete: {success_count} generated, "
                f"{skipped_count} skipped, {failed_count} failed"
            )
            write_stdout({
                "output": summary,
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
            "error": f"{str(e)}\n{traceback.format_exc()}"
        })
        sys.exit(1)


if __name__ == '__main__':
    main()
