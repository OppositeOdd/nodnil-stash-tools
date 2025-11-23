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
            # Return None when there are GraphQL errors to prevent further processing
            return None
        return data.get('data')
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from response: {response.text}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return None

def read_studio_names(file_path):
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

def find_studio(name):
    query = """
    query FindStudios($name: String!) {
        findStudios(
            studio_filter: { name: { value: $name, modifier: EQUALS } }
        ) {
            studios {
                id
                name
            }
        }
    }
    """
    variables = {"name": name}
    result = graphql_request(query, variables)
    if result and result.get("findStudios"):
        studios = result["findStudios"].get("studios", [])
        if studios:
            return studios[0]
    return None

def create_studio(name):
    existing_studio = find_studio(name)
    if existing_studio:
        return existing_studio

    mutation = """
    mutation StudioCreate($name: String!) {
        studioCreate(input: { name: $name }) {
            id
            name
        }
    }
    """
    variables = {"name": name}
    result = graphql_request(mutation, variables)
    if result is None:
        logger.error(f"Failed to get a valid response from GraphQL request for studio: {name}")
        return None
    
    # Check if the result contains the expected studioCreate data
    if "studioCreate" not in result or result["studioCreate"] is None:
        logger.error(f"Failed to create studio '{name}' - GraphQL returned empty result")
        return None
    
    return result

def main():
    # Set the working directory to the script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    studio_file = "studios.txt"
    studio_names = read_studio_names(studio_file)
    
    if not studio_names:
        logger.error("No studio names to process.")
        return

    logger.info(f"Creating {len(studio_names)} studios...")
    for name in studio_names:
        result = create_studio(name)
        if result:
            if "studioCreate" in result and result["studioCreate"]:
                studio = result["studioCreate"]
                logger.info(f"Created studio: {studio['name']} with ID: {studio['id']}")
            elif "id" in result and "name" in result:
                logger.info(f"Studio already exists: {result['name']} with ID: {result['id']}")
            else:
                logger.error(f"Unexpected result format for studio: {name}")
        else:
            logger.error(f"Failed to create studio: {name}")

if __name__ == "__main__":
    main()