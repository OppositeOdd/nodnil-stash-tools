# Funscript Scene Tab

Adds a "Funscripts" tab to scene pages displaying full heatmap and statistics.

## Features

- Custom tab in scene navigation
- Full heatmap image display
- Statistics table: actions, duration, speeds per axis
- Auto-updates when navigating scenes
- Graceful failure if heatmap missing

## Requirements

- **funUtil** plugin (dependency)
- **alternateHeatmaps** plugin (generates heatmaps)
- Stash

## Installation

**From Repository:**
1. Settings → Plugins → Available Plugins → Add Source
2. URL: `https://oppositeodd.github.io/nodnil-stash-tools/index.yml`
3. Install **Funscript Scene Tab** (dependencies install automatically)

**Manual:**
1. Install **funUtil** and **alternateHeatmaps** first
2. Copy `funscriptSceneTab` folder to plugins directory
3. Reload plugins

## Usage

1. Open scene page
2. Click **Funscripts** tab
3. View heatmap and stats

**If "No heatmap available":**
- Run alternateHeatmaps → Generate Heatmaps task (optionally generate merged funscripts first to save time)
- Process the scene
- Refresh page

## Tab Contents

**Heatmap Image:**
- Multi-axis visualization
- All detected axes displayed
- Chapters shown if enabled during generation

**Statistics Table:**
- Axis name
- Total actions
- Duration
- Max speed
- Average speed

## Troubleshooting

**Tab doesn't appear:**
- Verify on scene page (`/scenes/###`)
- Check funUtil loaded (Settings → Plugins)
- Check browser console

**No heatmap:**
- Run alternateHeatmaps task
- Verify funscripts exist
- Check `funUtil/assets/heatmaps/` directory

**Empty statistics:**
- Regenerate heatmaps with latest alternateHeatmaps
- Stats parsed from SVG text elements, ensure heatmaps were created successfully in funUtil/assets/heatmaps/{sceneOHash}.svg and {sceneOHash}_full.svg

## Technical Details

### Tab Integration

The plugin injects a new tab into Stash's scene navigation:

```html
<div class="nav-item">
  <a href="#" class="nav-link"
     data-rb-event-key="scene-funscripts-panel"
     role="tab">
    Funscripts
  </a>
</div>
```

### Panel Structure

Tab content is created dynamically:

```html
<div id="scene-funscripts-panel"
     class="tab-pane active show"
     role="tabpanel">
  <div class="funscripts-panel-content">
    <img src="..." class="full-heatmap-image"/>
    <table class="funscript-stats-table">...</table>
  </div>
</div>
```

### Stats Parsing

Stats are extracted from SVG structure:

1. Find axis groups: `g[transform^="translate"]`
2. Extract axis name: `text[font-size="250%"]`
3. Parse stat pairs: `text[text-anchor="end"]` elements
4. Build data structure: `{axis, Actions, Duration, MaxSpeed, AvgSpeed}`

## Future Enhancements

- [ ] Export stats to CSV/JSON
- [ ] Side-by-side comparison of multiple versions / Integrate with the [StashInteractiveTools](https://github.com/xtc1337/StashInteractiveTools) plugin by xtc1337
- [ ] Direct funscript file viewer/editor. (partially complete, added a lighthouse function)
- [ ] MFP controller via stash

## License

MIT License - See main project for details

## Author

Part of the Stash Funscript Helper plugin suite
