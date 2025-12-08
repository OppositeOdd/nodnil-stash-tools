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
    AXIS_EXTENSIONS,
    find_script_variants_and_axes,
    query_interactive_scenes,
    merge_funscripts
)

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'funUtil')
)
from funlib_py import Funscript  # noqa: E402


KNOWN_AXES = set(AXIS_EXTENSIONS)


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
            funscript_data = merge_funscripts(scripts_data, '2.0')
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
    # Remove video extension to get the base name for funscripts
    base_name_no_ext = os.path.splitext(base_name)[0]
    
    oshash_dir = os.path.join(heatmap_dir, oshash)
    os.makedirs(oshash_dir, exist_ok=True)
    
    if not support_variants:
        return generate_heatmap(base_path, oshash, heatmap_dir, show_chapters)
    
    variants, axis_scripts = find_script_variants_and_axes(directory, base_name_no_ext)
    
    if not variants:
        log("  ⊘ No funscript variants found")
        return False
    
    log(f"  → Found {len(variants)} variant(s): {', '.join(variants.keys())}")
    log(f"  [DEBUG] Variant paths: {list(variants.values())}")
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
        
        # Remove .funscript extension for find_funscript_paths using os.path.splitext
        base_variant_path, ext = os.path.splitext(variant_path)
        scripts_paths = find_funscript_paths(base_variant_path)
        log(f"  [DEBUG] Found scripts: {scripts_paths}")
        
        if not scripts_paths:
            log(f"  ✗ No funscript data found for{suffix_display}")
            continue
        
        funscript_data = None
        
        # scripts_paths is a dict like {'main': 'path.funscript', 'pitch': 'path.pitch.funscript'}
        if len(scripts_paths) == 1:
            # Single script - just read it
            script_path = list(scripts_paths.values())[0]
            funscript_data = read_funscript_json(script_path)
        else:
            # Multiple scripts (main + axes) - merge them
            scripts_objs = []
            main_script = None

            for axis_name, script_path in scripts_paths.items():
                data = read_funscript_json(script_path)
                if data:
                    if axis_name == 'main':
                        # Main script - don't set channel
                        main_script = Funscript(data)
                    else:
                        # Axis script - set channel name
                        data['channel'] = axis_name
                        scripts_objs.append(Funscript(data))

            # Add main script first if it exists
            if main_script:
                scripts_objs.insert(0, main_script)

            if scripts_objs:
                try:
                    merged_list = Funscript.mergeMultiAxis(scripts_objs, {'allowMissingActions': True})
                    if merged_list:
                        funscript_data = merged_list[0].toJSON()
                except Exception as e:
                    log(f"  ✗ Error merging multi-axis scripts: {e}")
                    funscript_data = None

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

        cookies = None
        if session_cookie and session_cookie.get('Name') and session_cookie.get('Value'):
            cookies = {session_cookie['Name']: session_cookie['Value']}

        args = input_data.get('args', {})
        mode = args.get('mode', 'generate_all')

        heatmap_dir = os.path.join(
            os.path.dirname(plugin_dir),
            'funUtil',
            'assets',
            'heatmaps'
        )
        os.makedirs(heatmap_dir, exist_ok=True)

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

                scene_id = scene['id']
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
