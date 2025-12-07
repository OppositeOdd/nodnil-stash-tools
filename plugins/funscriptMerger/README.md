# Funscript Merger

Merges multi-axis funscripts into single v1.1 or v2.0 format.

## Features

- Combines separate axis files (.stroke, .surge, .sway, etc.) into one file
- Output formats: v1.1 (metadata) or v2.0 (channels)
  note: 2.0 is only supported with MFP v1.33.9+ or XTP v0.55b+
- File handling: customizable for how original funscripts are handled post merge.
- Supports all standard axes: stroke, surge, sway, pitch, roll, twist
- Supports multiple variant single axis funscripts, will generate a new 2.0 or 1.1 merge for each variant. #optional
- Supports merge reversal and conversions. i.e v2.0 to v1.1, v2.0 to multiple separated v1.0 scripts, etc.
- Supports adding more axes to an already merged funscript.

## Requirements

- Python 3.x
- **funUtil** plugin (dependency)

**Note:** Funscripts must be saved in the same directory as the video file with matching filename (e.g., `video.mp4` → `video.funscript` / `video.*.funscript`). Support for alternate funscript paths is planned but not yet implemented.

## Installation

**From Repository:**
1. Settings → Plugins → Available Plugins → Add Source
2. URL: `https://oppositeodd.github.io/nodnil-stash-tools/index.yml`
3. Install **Funscript Merger** (funUtil installs automatically)

**Manual:**
1. Install **funUtil** first
2. Copy `funscriptMerger` folder to plugins directory
3. Reload plugins

## Configuration

**Multi-Axis Merging Format:**
- `0` - Disabled
- `1` - Version 1.1 (metadata object, compatible with all MFP versions)
- `2` - Version 2.0 (channels object, requires MFP v1.33.9+ and XTP v0.55b)

**Original Funscript Handling:**
- `0` - Keep originals as is, the newly merged funscript is stored alongside the others, with the name {videoFileName}.max.funscript. This will cause stash to serve {videoFileName}.funscript which is likely just single axis.
- `1` - Move the original funscripts to a newly created `originalFunscripts/` subdirectory, then re-name the merged funscript as {videoFileName}.funscript. This allows stash to serve multi-axis to MFP.
- `2` - Delete originals, same as setting 1 but will delete the original funscripts after successfully merging them (Experimental)

**enableUnmerge:**
- `True` - extra safety step to ensure a user wants to enable unmerging of scripts, set this to true to enable the unmerge task button
- `False` - Script blocks unmerging

**Support Multiple Script Variants:**
- `True` - Script searches for any variants that follow the schema {variantName}.funscript other than the default script, it will skip any {name}.*.funscript
- `False` - Script skips logic that helps to recognize multiple L0 axis variants

## Usage

**Run Task:**
1. Tasks → "Batch generate merged funscripts"
2. Processes all scenes with multi-axis scripts

**Supported Files:**
- `.funscript`, `L0`, `Stroke`
- `.surge.funscript`, `L1`, `Surge`
- `.sway.funscript`, `L2`, `Sway`
- `.twist.funscript`, `R0`, `Twist`
- `.roll.funscript`, `R1`, `Roll`
- `.pitch.funscript`, `R2`, `Pitch`

Note: any other {name}.*.funscript will be left alone and unchanged, it is safe to leave them in the folder, they just won't be merged.

**Output Example (v2.0):**
```json
{
  "version": "2.0",
  "actions": [...],
  "channels": {
    "surge": {"actions": [...]},
    "sway": {"actions": [...]}
  }
}
```

## Workflow with alternateHeatmaps

- Merged funscripts are auto detected and used by alternateHeatmaps, but not required by it. Save some time by creating the funscripts with this plugin first, then batch generating the heatmaps.

- If both alternate versions are merged, and alternate versions are enabled in heatmap generation. Heatmaps will be created and dynamically loaded depending on the script selected. Note that the script selection tool is apart of the plugin [StashInteractiveTools](https://github.com/OppositeOdd/StashInteractiveTools)) by xtc1337. In order to get it to work with my plugin, I had to fork and make some small changes, use this version.

## Safety

- Know the difference between setting 1 and 2 for file handling. Setting it to 2 WILL DELETE THE ORIGINALS. The unmerge function *can* recreate them after deletion, but testing is still needed to verify it works for all edge cases.

## Compatibility

### MFP

- Takes advantage of the way stash serves funscripts to MFP. It technically only supports single file serving, so serving a merged script is just a roundabout way to make multi-axis scripts compatible.
- Remember that MFP v1.33.9+ (Patreon Locked) is required for 2.0 merged scripts, 1.1 scripts are compatible with any version.

### Stash
- Works with Stash's interactive funscript features
- Heatmaps displayed via **alternateHeatmaps** plugin (generate separately)

## Troubleshooting

**Merged file not recognized by MFP:**
- Try v1.1 format for maximum compatibility
- Check MFP logs for specific errors


## Roadmap

- [ ] Support for additional axis i.e valve/suck (on hold until funlib/MFP adds support)
- [ ] Scene based on the fly merging via Stash UI 
- [-] Compatibility with [StashInteractiveTools](https://github.com/xtc1337/StashInteractiveTools) plugin (in progress)

## Related Plugins

- **funUtil**: Base library with shared utilities
- **alternateHeatmaps**: Display and generate heatmaps
- **funscriptSceneTab**: Custom scene tab with heatmap display
