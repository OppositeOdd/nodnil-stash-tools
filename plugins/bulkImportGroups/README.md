# Bulk Import Groups

## Description

This script bulk imports groups into your system using a list of group names from a text file.

## Features

- Reads group names from a text file.
- Checks if a group already exists before creating a new one.
- Logs detailed information about the process, including successes and errors.

## Requirements

`pip install stashapp-tools`

## Usage

1. Run the Task `Bulk Import Groups` after adding their names to the `groups.txt`

`Note:` for any new additions to the list, you will have to `Reload Plugins` for the script to see the updated list.

## Example

Here is an example of what the `groups.txt` file should look like:

Marvel Comics

DC Comics

Image Comics

Dark Horse Comics

## Logging

The script uses `stashapi.log` for logging. It logs detailed information about each group processed, including whether they were created or already exist.

## Troubleshooting

If you encounter any issues:
- Ensure your `config.py` file has the correct API key and endpoint.
- Ensure your `groups.txt` file is correctly formatted and located in the same directory as the script.