# Alternate Heatmaps

Replaces default Stash heatmaps with more detailed versions and adds support for multi-axis scripts.

## Features

- Scene index overlay support
- Scrubber overlay with position indicator
- Full heatmap display below player
- Optional chapter support
- generates from merged or multi-file funscripts, by user input only.
- Supports: stroke, surge, sway, pitch, roll, twist axes
- stores heatmaps directly inside funUtil/assets/heatmaps, does not overwrite stash generated files

## Requirements

- **funUtil** plugin (dependency)
- Node.js installed on server
- Funscripts (merged file named `{videoName}.funscript` or separate axis files)

**Note:** Funscripts must be saved in the same directory as the video file with matching filename (e.g., `video.mp4` → `video.funscript` / `video.*.funscript`). Support for alternate funscript paths is planned but not yet implemented.

## Installation

**From Repository:**
1. Settings → Plugins → Available Plugins → Add Source
2. URL: `https://oppositeodd.github.io/nodnil-stash-tools/index.yml`
3. Install **Alternate Heatmaps** (funUtil is a dependency and should auto install)

**Manual:**
1. Install **funUtil** first
2. Copy `alternateHeatmaps` folder to plugins directory
3. Reload plugins

## Usage

**Generate Heatmaps:**
1. Tasks → Generate Heatmaps
2. Click **Run** to batch process all interactive scenes
3. Generates `{oshash}.svg` and `{oshash}_full.svg` for each scene with funscripts

**View:**
- Navigate to scene page
- Heatmap appears in scrubber and below player automatically
- Position indicator tracks playback, this is a bug fix found in default stash.

**Generation Logic:**
1. Queries all interactive scenes in Stash
2. For each scene with at least one `.funscript` file:
   - Uses existing merged `.funscript` if available
   - Otherwise merges all axis files temporarily
   - Generates overlay SVG (690x40) and full SVG (1200x80)
   - Saves to `funUtil/assets/heatmaps/{oshash}.svg` and `{oshash}_full.svg`
3. Skips scenes without any funscript files

## Configuration

- **Show Chapters**: Display chapter bar at top of heatmaps

## Troubleshooting

**No heatmap displays:**
- Check funscripts exist for scene
- Run Generate Heatmaps task
- Check plugin is enabled via stash plugin UI

**Heatmap generation fails:**
- Ensure funscripts are valid JSON
- Review Stash logs for errors
- Run "Generate Heatmaps" task manually
- Check that heatmap SVG exists in `funUtil/assets/heatmaps/`

### "No SVG output from Node.js"

- Ensure Node.js is installed: `node --version`
- Check that `funUtil/funlib-bundle.js` exists
- Look for Python error messages in Stash logs

## Technical Details

### Heatmap Generation Pipeline

```
Python finds funscripts
     ↓
Check for merged file
     ↓ (not found)
Find individual axes
     ↓
Merge temporarily (v2.0 format)
     ↓
Create Node.js script with funlib
     ↓
Execute: node -e "script"
     ↓
Capture SVG output
     ↓
Save to funUtil/assets/heatmaps/{oshash}.svg
```

### Temporary Merge Format

When merging multiple files, uses v2.0 channel format:
note: this is only used for heatmap generation and the funscript will not be served to MFP.
use funscriptMerger plugin to create merged funscripts for stash to serve to MFP

```json
{
  "version": "2.0",
  "actions": [...],  // Main axis (stroke/L0)
  "channels": {
    "surge": {"actions": [...]},
    "sway": {"actions": [...]},
    "pitch": {"actions": [...]}
  }
}
```

### Dependencies

```yaml
ui:
  requires:
    - funUtil  # Provides funlib-bundle.js and API helpers
```


## Related Plugins

- **funUtil**: Base library with funlib bundle
- **funscriptMerger**: Merges multi-axis files permanently
- **funscriptSceneTab**: Displays full heatmap in custom tab

## License

MIT License - See main project for details

## Author

Part of the Stash Funscript Helper plugin suite
