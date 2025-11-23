# Group to Tags Converter

## Description

This plugin automatically converts all Groups in your Stash instance into matching Tags. For each group that exists, it will create a corresponding tag with the exact same name.

## Features

- **Automatic Conversion**: Iterates through all groups and creates matching tags
- **Duplicate Prevention**: Checks if tags already exist before creating new ones
- **Comprehensive Logging**: Detailed logs of what was created, skipped, or failed
- **Community Resources**: Uses the proven py_common utilities from the community scrapers
- **Safe Operation**: Only creates tags, never modifies or deletes existing data

## Use Case

Perfect for when you want to:
- Use groups as tags for better organization
- Migrate from groups to tags
- Have both groups AND tags for the same franchises/universes
- Create a tag-based organizational system alongside your groups

## Example

If you have these groups:
- Xenoblade Chronicles
- Stellar Blade  
- Final Fantasy
- Zenless Zone Zero

The plugin will create these matching tags:
- Xenoblade Chronicles
- Stellar Blade
- Final Fantasy  
- Zenless Zone Zero

## Requirements

- Python 3.6+
- `requests` library (auto-installed)
- Access to community py_common utilities

## Configuration

Edit `config.ini` to set your Stash server URL and API key (if required):

```ini
# URL for your local Stash server
url = http://192.168.1.75:9999

# API key (optional if no authentication required)
api_key =
```

## Usage

1. **Reload Plugins** in Stash (Settings → Plugins → Reload Plugins)
2. **Run the Task** called "Convert Groups to Tags"
3. **Check the Logs** to see what was created

## Logging

The plugin provides detailed logging:
- Groups processed
- Tags already existing (skipped)
- New tags created successfully
- Any failures with error details
- Final summary with counts

## Safety

This plugin is completely safe:
- ✅ **Read-only for groups** - never modifies group data
- ✅ **Create-only for tags** - only creates new tags
- ✅ **Duplicate-safe** - won't create duplicate tags
- ✅ **Non-destructive** - never deletes anything

## Troubleshooting

- Ensure `config.ini` has correct Stash URL
- Check that py_common utilities are accessible
- Verify Stash API is responding
- Check logs for specific error messages