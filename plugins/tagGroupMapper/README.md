# Tag-Group Mapper Plugin

This plugin automatically maps Stash tags to groups by matching their names and aliases, then generates the proper configuration format for the **stashDynamicGroups** plugin.

## What It Does

1. **Fetches all tags** with their IDs, names, and aliases
2. **Fetches all groups** with their IDs, names, and aliases  
3. **Matches tags to groups** by comparing normalized names and aliases
4. **Generates configuration** in the format needed by stashDynamicGroups plugin

## How to Use

### 1. Run the Plugin
- Go to **Settings** → **Plugins** in Stash
- Find **Tag-Group Mapper** plugin
- Click **Generate Tag-Group Mappings**

### 2. Check Output Files
The plugin creates two files in its directory:

#### `tag_group_mappings.txt`
Contains the configuration string to copy into stashDynamicGroups:
```
# Configuration for stashDynamicGroups plugin
# Copy the line below to SetGroupTagRelationship setting

123:456,789:101,202:303

# Individual mappings:
# Xenoblade Chronicles (ID: 123) -> Xenoblade Chronicles (ID: 456)
# Final Fantasy (ID: 789) -> Final Fantasy (ID: 101)
# Pokemon (ID: 202) -> Pokemon (ID: 303)
```

#### `tag_group_mappings_report.txt`
Detailed report showing all matches found with match types and reasoning.

### 3. Configure stashDynamicGroups
1. Go to **Settings** → **Plugins** → **stashDynamicGroups**
2. Find the **SetGroupTagRelationship** setting
3. Copy the configuration string from `tag_group_mappings.txt`
4. Paste it into the setting and save

## Matching Logic

The plugin uses intelligent matching:

- **Exact name matches**: "Xenoblade Chronicles" tag ↔ "Xenoblade Chronicles" group
- **Alias matches**: Tag alias "XC" ↔ Group name "Xenoblade Chronicles"
- **Normalized matching**: Ignores case, punctuation, and extra spaces
- **Duplicate prevention**: Won't create duplicate mappings

## Example Output

If you have:
- Tag: "Xenoblade Chronicles" (ID: 123)
- Group: "Xenoblade Chronicles" (ID: 456)

The plugin generates: `123:456`

When used with stashDynamicGroups:
- Adding "Xenoblade Chronicles" tag to a scene → Scene joins "Xenoblade Chronicles" group
- Removing the tag → Scene leaves the group

## Configuration

Edit `config.py` to customize Stash connection:
```python
STASH_URL = "http://localhost:9999"
STASH_API_KEY = ""  # Add if needed
```

## Requirements

- Python 3.6+
- `requests` library (auto-installed)
- Running Stash instance

## Workflow

1. **Tag-Group Mapper** → Generate mappings
2. **stashDynamicGroups** → Use mappings for automation
3. **Automatic sync** → Tags ↔ Groups stay synchronized

Perfect for organizing large libraries where tags and groups should stay in sync! 🎯