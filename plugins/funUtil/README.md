# FunUtil

Shared utilities library for funscript plugins. Provides funlib_py (Python port of funlib), funscript_utils (shared Python functions), Stash API helpers, and heatmap utilities.

## Credits

**funlib_py** is a Python port of the original [funlib](https://github.com/Eroscripts/funlib) library written in TypeScript by the Eroscripts forum developers. The original library provides funscript parsing, manipulation, and SVG generation capabilities.

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

### Python Libraries

**funscript_utils.py** - Shared utility functions for Python plugins:
- `find_funscript_paths()` - Locate all funscript files for a scene
- `find_script_variants_and_axes()` - Detect script variants and axis files
- `query_interactive_scenes()` - Query Stash for interactive scenes
- `merge_funscripts()` - Merge multi-axis funscripts
- `load_plugin_settings()` - Load plugin settings from Stash API
- File I/O helpers, logging, and more

**funlib_py/** - Python port of [funlib](https://github.com/Eroscripts/funlib) (TypeScript):
- Funscript class for parsing and manipulation
- SVG heatmap generation
- Multi-axis merging and format conversion
- Statistics and analysis functions

Import in your plugin:
```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'funUtil'))
from funscript_utils import find_funscript_paths, merge_funscripts
from funlib_py import Funscript
```

### Python Backend (Deprecated)

The `funUtil.py` RPC backend has been removed. Use `funscript_utils.py` for Python plugins.

## Dependent Plugins

- **alternateHeatmaps** - Multi-axis heatmap generation
- **funscriptMerger** - Merge multi-axis funscripts
- **funscriptSceneTab** - Funscript tab in scene pages
