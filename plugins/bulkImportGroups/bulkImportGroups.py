import requests
import json
import os
import sys
import subprocess

# Auto-install dependencies if missing
def ensure_dependencies():
    """Ensure required dependencies are installed"""
    required_packages = ['pydantic', 'stashapp-tools']
    
    for package in required_packages:
        try:
            if package == 'stashapp-tools':
                import stashapi.log
            else:
                __import__(package)
        except ImportError:
            print(f"Installing missing package: {package}")
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", package, 
                    "--break-system-packages", "--quiet"
                ])
                print(f"Successfully installed: {package}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to install {package}: {e}")
                # Continue anyway, let the import error happen naturally

# Install dependencies before importing
ensure_dependencies()

import stashapi.log as logger
from config import config  # Importing config from config.py

def graphql_request(query, variables=None):
    headers = {
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Only add API key header if it's provided
    if config["api_key"]:
        headers["ApiKey"] = config["api_key"]
    
    response = requests.post(config['endpoint'], json={'query': query, 'variables': variables}, headers=headers)
    try:
        data = response.json()
        if "errors" in data:
            logger.error(f"GraphQL errors: {data['errors']}")
        return data.get('data')
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from response: {response.text}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return None

def read_group_names(file_path):
    try:
        with open(file_path, 'r') as file:
            names = [line.strip() for line in file.readlines()]
        return names
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return []
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return []

def find_group(name):
    query = """
    query FindGroups($name: String!) {
        findGroups(
            group_filter: { name: { value: $name, modifier: EQUALS } }
        ) {
            groups {
                id
                name
            }
        }
    }
    """
    variables = {"name": name}
    result = graphql_request(query, variables)
    if result and result.get("findGroups"):
        groups = result["findGroups"].get("groups", [])
        if groups:
            return groups[0]
    return None

def create_group(name):
    existing_group = find_group(name)
    if existing_group:
        return existing_group

    mutation = """
    mutation GroupCreate($name: String!) {
        groupCreate(input: { name: $name }) {
            id
            name
        }
    }
    """
    variables = {"name": name}
    result = graphql_request(mutation, variables)
    if result is None:
        logger.error(f"Failed to get a valid response from GraphQL request for group: {name}")
    return result

def main():
    # Set the working directory to the script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    group_file = "groups.txt"
    group_names = read_group_names(group_file)
    
    if not group_names:
        logger.error("No group names to process.")
        return

    logger.info(f"Creating {len(group_names)} groups...")
    for name in group_names:
        result = create_group(name)
        if result:
            if "groupCreate" in result:
                group = result["groupCreate"]
                logger.info(f"Created group: {group['name']} with ID: {group['id']}")
            elif "id" in result and "name" in result:
                logger.info(f"Group already exists: {result['name']} with ID: {result['id']}")
        else:
            logger.error(f"Failed to create group: {name}")

if __name__ == "__main__":
    main()