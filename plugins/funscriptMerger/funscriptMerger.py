#!/usr/bin/env python3
"""
Funscript Merger - Python Backend

Merges multi-axis funscripts into v1.1 or v2.0 format.
Handles file operations (move/delete originals).
"""

import os
import sys
import shutil
from typing import Dict, List, Tuple

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
    log,
    AXIS_EXTENSIONS,
    find_script_variants_and_axes,
    query_interactive_scenes,
    merge_funscripts,
    load_plugin_settings
)

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'funUtil')
)
from funlib_py import Funscript


KNOWN_AXES = set(AXIS_EXTENSIONS)


def find_all_script_variants(directory: str, base_name: str) -> Dict[str, Dict]:
    variants, shared_axes = find_script_variants_and_axes(directory, base_name)

    if "default" in variants and shared_axes:
        variants["default"]['axes'] = shared_axes

    return variants


def is_special_axis_script(filename: str, base_name: str) -> bool:
    for axis in KNOWN_AXES:
        if filename == f"{base_name}.{axis}.funscript":
            return True
    return False


def handle_original_files(
    scripts: Dict[str, str],
    mode: int,
    base_path: str,
    max_path: str
):
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


def process_single_variant(
    variant_base_path: str,
    variant_data: Dict,
    settings: Dict,
    is_default: bool = False
) -> bool:
    merge_mode = settings.get('mergingMode', 1)
    file_mode = settings.get('fileHandlingMode', 0)
    target_version = '1.1' if merge_mode == 1 else '2.0'

    main_path = variant_data['path']  # Changed from 'main' to 'path' to match shared function
    axes = variant_data.get('axes', {})
    suffix = variant_data['suffix']

    if not main_path and not axes:
        return False

    if not main_path and axes:
        log(f"  ⊘ Variant{suffix}: No main script, only axis files found")
        return False

    if main_path and not axes:
        data = read_funscript_json(main_path)
        if not data:
            log(f"  ✗ Variant{suffix}: Could not read main script")
            return False
        
        directory = os.path.dirname(main_path)
        originals_dir = os.path.join(directory, 'originalFunscripts')
        base_name = os.path.splitext(os.path.basename(main_path))[0]
        
        if suffix:
            video_base = base_name[:-len(suffix)] if base_name.endswith(suffix) else base_name
        else:
            video_base = base_name
        
        available_axes = {}
        if os.path.exists(originals_dir):
            for axis in KNOWN_AXES:
                axis_file = f"{video_base}.{axis}.funscript"
                axis_path = os.path.join(originals_dir, axis_file)
                if os.path.exists(axis_path):
                    available_axes[axis] = axis_path
        
        if available_axes:
            is_merged = is_merged_funscript(data)
            
            if is_merged:
                from funscript_utils import get_funscript_version, convert_funscript_format, get_merged_channels
                
                current_version = get_funscript_version(data)
                existing_channels = set(get_merged_channels(data))
                available_axis_names = set(available_axes.keys())
                missing_axes = available_axis_names - existing_channels
                
                if missing_axes:
                    log(f"  → Variant{suffix}: Merged script missing axes: {', '.join(sorted(missing_axes))}")
                    
                    original_main_in_originals = os.path.join(originals_dir, f"{base_name}.funscript")
                    all_originals_found = os.path.exists(original_main_in_originals) and all(
                        os.path.exists(os.path.join(originals_dir, f"{video_base}.{ch}.funscript")) 
                        for ch in existing_channels
                    )
                    
                    if all_originals_found:
                        log(f"  ✓ Variant{suffix}: Found originals in originalFunscripts/")
                        log(f"  ⟳ Variant{suffix}: Re-merging with all {len(available_axes)} axes...")
                        
                        original_main_data = read_funscript_json(original_main_in_originals)
                        if not original_main_data:
                            log(f"  ✗ Variant{suffix}: Could not read original main script")
                            return False
                        
                        axes_to_merge = {}
                        for axis, axis_path in available_axes.items():
                            axis_data = read_funscript_json(axis_path)
                            if axis_data:
                                axes_to_merge[axis] = axis_data
                        
                        if axes_to_merge:
                            scripts_data = {'main': original_main_data}
                            scripts_data.update(axes_to_merge)
                            
                            merged = merge_funscripts(scripts_data, target_version)
                            if merged and save_funscript(main_path, merged):
                                log(f"  ✓ Variant{suffix}: Re-merged with all axes ({', '.join(sorted(axes_to_merge.keys()))})")
                                return True
                            else:
                                log(f"  ✗ Variant{suffix}: Failed to re-merge")
                                return False
                    else:
                        from funscript_utils import unmerge_funscript
                        
                        log(f"  ⚠ Variant{suffix}: Originals not found, will unmerge to extract them")
                        log(f"  ⟳ Variant{suffix}: Unmerging v{current_version} script...")
                        
                        saved_files = unmerge_funscript(data, variant_base_path)
                        
                        if not saved_files:
                            log(f"  ✗ Variant{suffix}: Unmerge failed")
                            return False
                        
                        log(f"  ✓ Variant{suffix}: Extracted {len(saved_files)} v1.0 scripts")
                        
                        try:
                            os.remove(main_path)
                            log(f"  → Variant{suffix}: Deleted merged script after unmerge")
                        except (OSError, IOError) as e:
                            log(f"  ✗ Variant{suffix}: Error deleting merged script: {e}")
                        
                        unmerged_scripts = {}
                        for channel, path in saved_files.items():
                            script_data = read_funscript_json(path)
                            if script_data:
                                unmerged_scripts[channel] = script_data
                        
                        axes_to_merge = {}
                        for axis, axis_path in available_axes.items():
                            axis_data = read_funscript_json(axis_path)
                            if axis_data:
                                axes_to_merge[axis] = axis_data
                        
                        if unmerged_scripts and axes_to_merge:
                            all_scripts = {}
                            all_scripts.update(unmerged_scripts)
                            all_scripts.update(axes_to_merge)
                            
                            log(f"  ⟳ Variant{suffix}: Re-merging {len(all_scripts)} scripts to v{target_version}...")
                            merged = merge_funscripts(all_scripts, target_version)
                            
                            if merged and save_funscript(main_path, merged):
                                log(f"  ✓ Variant{suffix}: Re-merged with all axes")
                                return True
                            else:
                                log(f"  ✗ Variant{suffix}: Failed to re-merge")
                                return False
                
                if current_version == target_version:
                    log(f"  ⊘ Variant{suffix}: Already in v{target_version} format with all axes")
                    return False

                log(f"  ⟳ Variant{suffix}: Converting from v{current_version} to v{target_version}...")
                converted = convert_funscript_format(data, target_version)

                if converted and save_funscript(main_path, converted):
                    log(f"  ✓ Variant{suffix}: Converted to v{target_version}")
                    return True
                else:
                    log(f"  ✗ Variant{suffix}: Failed to convert")
                    return False
            else:
                log(f"  → Variant{suffix}: Found {len(available_axes)} axes in originalFunscripts/")
                log(f"  ⟳ Variant{suffix}: Merging with axes: {', '.join(sorted(available_axes.keys()))}")
                
                axes_to_merge = {}
                for axis, axis_path in available_axes.items():
                    axis_data = read_funscript_json(axis_path)
                    if axis_data:
                        axes_to_merge[axis] = axis_data
                
                if axes_to_merge:
                    # Merge main script + all axes
                    scripts_data = {'main': data}
                    scripts_data.update(axes_to_merge)
                    
                    merged = merge_funscripts(scripts_data, target_version)
                    if merged and save_funscript(main_path, merged):
                        log(f"  ✓ Variant{suffix}: Merged with {len(axes_to_merge)} axes to v{target_version}")
                        return True
                    else:
                        log(f"  ✗ Variant{suffix}: Failed to merge")
                        return False

        log(f"  ⊘ Variant{suffix}: Single script, no axes to merge")
        return False

    scripts_data = {}
    scripts_paths = {}

    if main_path:
        main_data = read_funscript_json(main_path)
        if main_data:
            scripts_data['main'] = main_data
            scripts_paths['main'] = main_path

    for axis, axis_path in axes.items():
        axis_data = read_funscript_json(axis_path)
        if axis_data:
            scripts_data[axis] = axis_data
            scripts_paths[axis] = axis_path

    if not scripts_data:
        log(f"  ✗ Variant{suffix}: Could not read any scripts")
        return False

    if len(scripts_data) == 1:
        log(f"  ⊘ Variant{suffix}: Only one valid script")
        return False

    log(f"  ⟳ Variant{suffix}: Merging {len(scripts_data)} scripts to v{target_version}...")
    merged = merge_funscripts(scripts_data, target_version)

    max_path = f"{variant_base_path}.max.funscript"
    if not save_funscript(max_path, merged):
        log(f"  ✗ Variant{suffix}: Failed to save merged script")
        return False

    log(f"  ✓ Variant{suffix}: Saved {os.path.basename(max_path)}")

    if file_mode == 1:
        originals_dir = os.path.join(os.path.dirname(variant_base_path), 'originalFunscripts')
        os.makedirs(originals_dir, exist_ok=True)

        for file_path in scripts_paths.values():
            filename = os.path.basename(file_path)
            dest = os.path.join(originals_dir, filename)
            try:
                shutil.move(file_path, dest)
            except (OSError, IOError):
                pass

        try:
            if os.path.exists(variant_base_path + ".funscript"):
                os.remove(variant_base_path + ".funscript")
            shutil.move(max_path, variant_base_path + ".funscript")
            log(f"  ✓ Variant{suffix}: Renamed to .funscript")
        except (OSError, IOError) as e:
            log(f"  ✗ Variant{suffix}: Error renaming: {e}")
            return False

    elif file_mode == 2:
        for file_path in scripts_paths.values():
            try:
                os.remove(file_path)
            except (OSError, IOError):
                pass

        try:
            if os.path.exists(variant_base_path + ".funscript"):
                os.remove(variant_base_path + ".funscript")
            shutil.move(max_path, variant_base_path + ".funscript")
            log(f"  ✓ Variant{suffix}: Renamed to .funscript")
        except (OSError, IOError) as e:
            log(f"  ✗ Variant{suffix}: Error renaming: {e}")
            return False

    return True


def process_scene(
    scene_id: str,
    base_path: str,
    settings: Dict
) -> bool:
    log(
        f"Processing scene {scene_id}: "
        f"{os.path.basename(base_path)}"
    )

    merge_mode = settings.get('mergingMode', 1)

    if merge_mode == 0:
        log("  ⊘ Merging disabled (mode 0), skipping")
        return False

    support_variants = settings.get('supportMultipleScriptVersions', False)

    if support_variants:
        directory = os.path.dirname(base_path)
        base_name = os.path.basename(base_path)

        variants, shared_axes = find_script_variants_and_axes(directory, base_name)

        if not variants:
            log("  ⊘ No script variants found")
            return False
        
        if shared_axes:
            log(f"  → Found {len(variants)} variant(s): {', '.join(variants.keys())}")
            log(f"  → Shared axes: {', '.join(shared_axes.keys())}")
        else:
            log(f"  → Found {len(variants)} variant(s): {', '.join(variants.keys())}")
            log(f"  → No shared axes in main directory (checking originalFunscripts/)")

        any_merged = False
        for variant_key, variant_data in sorted(variants.items()):
            variant_base = base_path + variant_data['suffix']
            is_default = variant_key == "default"
            
            directory = os.path.dirname(base_path)
            originals_dir = os.path.join(directory, 'originalFunscripts')
            
            if os.path.exists(originals_dir):
                available_axes = {}
                for axis, axis_path in shared_axes.items():
                    original_location = os.path.join(originals_dir, os.path.basename(axis_path))
                    if os.path.exists(original_location):
                        available_axes[axis] = original_location
                    elif os.path.exists(axis_path):
                        available_axes[axis] = axis_path
                variant_data['axes'] = available_axes
            else:
                variant_data['axes'] = shared_axes.copy()

            if process_single_variant(variant_base, variant_data, settings, is_default):
                any_merged = True

        return any_merged

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

    cookies = None
    if session_cookie and session_cookie.get('Name') and session_cookie.get('Value'):
        cookies = {session_cookie['Name']: session_cookie['Value']}

    server_url = f"{scheme}://localhost:{port}/graphql"

    log("=" * 60)
    log("Funscript Merger - Batch Processing")
    log("=" * 60)
    log("Querying Stash for interactive scenes...")

    scenes = query_interactive_scenes(server_url, cookies, filter_has_funscripts=False)

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
        file_path = scene.get('file_path')

        if not file_path:
            log(f"[{idx}/{len(scenes)}] Scene {scene_id}: No file path")
            skipped_count += 1
            continue

        base_path = os.path.splitext(file_path)[0]

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

    scenes = query_interactive_scenes(server_url, cookies, filter_has_funscripts=False)

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
        file_path = scene.get('file_path')

        if not file_path:
            log(f"[{idx}/{len(scenes)}] Scene {scene_id}: No file path")
            skipped_count += 1
            continue

        base_path = os.path.splitext(file_path)[0]

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

        default_settings = {
            'mergingMode': 1,
            'fileHandlingMode': 0,
            'enableUnmerge': False,
            'supportMultipleScriptVersions': False
        }
        settings = load_plugin_settings(server_connection, 'funscriptMerger', default_settings)

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
