# Stashapp Plugins & Scripts

A collection of plugins and utility scripts for [Stash](https://github.com/stashapp/stash), an open-source adult media organizer.

These plugins were both inspired by and created to work in tandem with [Serechops Stash Repo](https://github.com/Serechops/Serechops-Stash)

## 📦 Plugins

### Bulk Import Plugins
Bulk import plugins for adding large amounts of data to your Stash instance:

#### [bulkImportPerformers](./plugins/bulkImportPerformers/)
- Bulk import performers from a text file
- Duplicate detection and prevention
- Comprehensive logging and error handling
- Auto-dependency installation

#### [bulkImportGroups](./plugins/bulkImportGroups/)
- Bulk import groups from a text file
- Perfect for franchise/universe organization
- Same proven structure as performers plugin
- Comprehensive logging

#### [bulkImportStudios](./plugins/bulkImportStudios/)
- Bulk import studios from a text file
- Ideal for content producers and animation studios
- GraphQL error handling for duplicate names/aliases
- Robust error recovery

#### [groupToTags](./plugins/groupToTags/)
- Automatically convert all groups to matching tags
- Uses community py_common utilities
- Safe, non-destructive operation
- Detailed progress reporting

#### [tagGroupMapper](./plugins/tagGroupMapper/)
- Automatically map tags to groups by name/alias matching
- Generate configuration for stashDynamicGroups plugin
- Intelligent normalization and duplicate prevention
- Creates detailed reports and ready-to-use config files

## 🛠️ Utility Scripts

### Data Extraction Scripts
Helper scripts for extracting data from organized folder structures:

#### [extract_performers.py](./scripts/extract_performers.py)
Extract performer names from folder structure:
```
Folder/
  Universe1/
    Performer1/
    Performer2/
  Universe2/
    Performer3/
```

#### [extract_universes.py](./scripts/extract_universes.py)
Extract universe/franchise names (top-level folders) from the same structure.

#### [extract_animators.py](./scripts/extract_animators.py)
Extract animator names from file titles with bracket notation:
```
[AnimatorName] filename.mp4
```

#### [addTag.py](./scripts/addTag.py)
Add tags to filenames in two modes:
- **Automatic mode**: Uses subfolder names as tags for files within those folders
- **Manual mode**: Uses a specified tag for all files in a directory
- **Smart cleaning**: Removes existing tags and cleans filenames before adding new tags

## Quick Start

### For Plugins:
1. Copy the plugin folder to your Stash plugins directory
2. Configure `config.py` or `config.ini` with your Stash details
3. Reload plugins in Stash (Settings → Plugins → Reload)
4. Run the plugin task from the Tasks page

### For Scripts:
1. Run the extraction script on your organized folders
2. Copy the generated `.txt` file to the appropriate plugin directory
3. Run the corresponding bulk import plugin

#### Example Workflow:

Initial Folder Structure

```
Folder/
  Animator1/
    Scene1/{File1,File2,File3}
    Scene2/{File1,File2,File3}
    File1
    File2
    File3
  Animator2/
    Scene1/{File1,File2,File3}
    Scene2/{File1,File2,File3}
    File1
    File2
    File3
```
After running addTag.py
```
Folder/
  Animator1/
    Scene1/{[Animator1] File1,[Animator1] File2,[Animator1] File3}
    Scene2/{[Animator1] File1,[Animator1] File2,[Animator1] File3}
    [Animator1] File1
    [Animator1] File2
    [Animator1] File3
  Animator2/
    Scene1/{[Animator2] File1,[Animator2] File2,[Animator2] File3}
    Scene2/{[Animator2] File1,[Animator2] File2,[Animator2] File3}
    [Animator2] File1
    [Animator2] File2
    [Animator2] File3
```
Then reorganize the files into this format

```
Folder/
  Universe1/
    Performer1/{[Animator2] File1,[Animator2] File2,[Animator2] File3}
    Performer2/
  Universe2/
    Performer3/
```
Run with "Folder" as input
- python3 extract_animators.py /path/to/folder
- python3 extract_performers.py /path/to/folder
- python3 extract_universes.py /path/to/folder

Take the output .txt file, rename and place in /path/to/stash/stash/plugins/bulkImport*/{studios.txt,performers.txt,groups.txt}

Run the plugins inside stash, they will import all the corresponding folder names.

Then, run group to Tags plugin. This will create corresponding Tags for every group created in Stash.

Lastly, run tagGroupMapper. This will generate a config to map your groups and tags, which can be used inside serechops plugin dynamicGroupMapper.

## 📋 Requirements

- Python 3.6+
- Stash instance (local or remote)
- Required Python packages (auto-installed by plugins):
  - `requests`
  - `stashapp-tools`
  - `pydantic`

## 🔧 Configuration

Most plugins use a similar configuration pattern:

```python
# config.py
config = {
    "api_key": "",  # Optional API key
    "endpoint": "http://your-stash-server:9999/graphql"
}
```

Or for community-based plugins:

```ini
# config.ini
url = http://your-stash-server:9999
api_key = 
```

## 🛡️ Safety

All plugins are designed to be safe:
- ✅ **Non-destructive** - Only create, never delete
- ✅ **Duplicate-safe** - Check for existing data before creating
- ✅ **Error handling** - Graceful failure recovery
- ✅ **Comprehensive logging** - Detailed operation reports

## Documentation

Each plugin and script includes detailed documentation:
- Setup instructions
- Usage examples
- Configuration options
- Troubleshooting guides

## License

This project is licensed under the same license as Stash.

## Acknowledgments

- [Stash](https://github.com/stashapp/stash) - The amazing media organizer
- [Community Scripts](https://github.com/stashapp/CommunityScripts) - Inspiration and utilities
- py_common utilities from the community scrapers