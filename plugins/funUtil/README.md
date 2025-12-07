# FunUtil

Shared utilities library for funscript plugins. Provides funlib_py (Python port of funlib), Stash API helpers, file operations, and heatmap utilities.

## Installation

**From Repository:**
1. Settings → Plugins → Available Plugins → Add Source
2. URL: `https://oppositeodd.github.io/nodnil-stash-tools/index.yml`
3. Install **FunUtil**

**Manual:**
1. Copy `funUtil` folder to Stash `plugins` directory
2. Reload plugins

## For Developers

Declare as dependency:
```yaml
ui:
  requires:
    - funUtil
```

### JavaScript API

```javascript
// Scene data
const sceneData = await FunUtil.fetchSceneData(sceneId);
const sceneId = FunUtil.getCurrentSceneId();

// Heatmaps
const url = FunUtil.getHeatmapUrl(oshash, 'overlay', 'pluginName');
const exists = await FunUtil.heatmapExists(url);

// File paths
const basePath = FunUtil.getBasePath('/path/to/video.mp4');
const dir = FunUtil.getDirectory('/path/to/video.mp4');

// API calls
const result = await FunUtil.callStashGQL(query, variables);
const config = await FunUtil.getPluginConfig('pluginId', defaults);
const result = await FunUtil.callPythonPlugin('pluginId', 'task', args);

// Initialization
FunUtil.waitForStashLibrary(initFunction);
```

### Python Backend

Call via `FunUtil.callPythonPlugin('funUtil', 'file_operation', {action, ...})`

**Actions:**
- `read_funscripts` - Read all funscripts for base path
- `save_funscript` - Save funscript to disk  
- `save_heatmap` - Save SVG to assets/heatmaps
- `create_directory` - Create directory recursively
- `move_file` - Move file with path creation
- `delete_file` - Delete file
- `rename_file` - Rename/move file
- `file_exists` - Check file existence

## Dependent Plugins

- **alternateHeatmaps** - Multi-axis heatmap generation
- **funscriptMerger** - Merge multi-axis funscripts
- **funscriptSceneTab** - Funscript tab in scene pages
