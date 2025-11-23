# Bulk Import Studios

## Description

This script bulk imports studios into your system using a list of studio names from a text file.

## Features

- Reads studio names from a text file.
- Checks if a studio already exists before creating a new one.
- Logs detailed information about the process, including successes and errors.

## Requirements

`pip install stashapp-tools`

## Usage

1. Run the Task `Bulk Import Studios` after adding their names to the `studios.txt`

`Note:` for any new additions to the list, you will have to `Reload Plugins` for the script to see the updated list.

## Example

Here is an example of what the `studios.txt` file should look like:

Brazzers

Reality Kings

Naughty America

Digital Playground

## Logging

The script uses `stashapi.log` for logging. It logs detailed information about each studio processed, including whether they were created or already exist.

## Troubleshooting

If you encounter any issues:
- Ensure your `config.py` file has the correct API key and endpoint.
- Ensure your `studios.txt` file is correctly formatted and located in the same directory as the script.