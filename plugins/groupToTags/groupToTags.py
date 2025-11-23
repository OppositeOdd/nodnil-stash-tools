import sys
import os
import json
import subprocess

# Add the community py_common path to sys.path for imports
sys.path.append('/Volumes/mediastack/config/stashdb/stash/scrapers/community')

# Auto-install dependencies if missing
def ensure_dependencies():
    """Ensure required dependencies are installed"""
    required_packages = ['requests']
    
    for package in required_packages:
        try:
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

# Install dependencies before importing
ensure_dependencies()

import py_common.log as log
import py_common.graphql as graphql

def get_all_groups():
    """Get all groups from Stash"""
    query = """
    query FindGroups {
        findGroups(filter: { per_page: -1 }) {
            groups {
                id
                name
            }
        }
    }
    """
    
    result = graphql.callGraphQL(query)
    if result and "findGroups" in result:
        return result["findGroups"]["groups"]
    return []

def find_tag_by_name(name):
    """Find a tag by exact name match"""
    query = """
    query FindTags($name: String!) {
        findTags(
            tag_filter: { name: { value: $name, modifier: EQUALS } }
            filter: { per_page: 1 }
        ) {
            tags {
                id
                name
            }
        }
    }
    """
    
    variables = {"name": name}
    result = graphql.callGraphQL(query, variables)
    if result and "findTags" in result and result["findTags"]["tags"]:
        return result["findTags"]["tags"][0]
    return None

def create_tag(name):
    """Create a new tag"""
    mutation = """
    mutation TagCreate($name: String!) {
        tagCreate(input: { name: $name }) {
            id
            name
        }
    }
    """
    
    variables = {"name": name}
    result = graphql.callGraphQL(mutation, variables)
    if result and "tagCreate" in result:
        return result["tagCreate"]
    return None

def process_group_to_tag(group):
    """Process a single group and create corresponding tag if needed"""
    group_name = group["name"]
    group_id = group["id"]
    
    log.info(f"Processing group: {group_name} (ID: {group_id})")
    
    # Check if tag already exists
    existing_tag = find_tag_by_name(group_name)
    if existing_tag:
        log.info(f"Tag already exists: {group_name} (ID: {existing_tag['id']})")
        return existing_tag
    
    # Create new tag
    new_tag = create_tag(group_name)
    if new_tag:
        log.info(f"Created tag: {new_tag['name']} (ID: {new_tag['id']})")
        return new_tag
    else:
        log.error(f"Failed to create tag for group: {group_name}")
        return None

def main():
    """Main function to process all groups and create matching tags"""
    log.info("Starting Group to Tags conversion...")
    
    # Get all groups
    groups = get_all_groups()
    if not groups:
        log.warning("No groups found in Stash instance")
        return
    
    log.info(f"Found {len(groups)} groups to process")
    
    created_count = 0
    existing_count = 0
    failed_count = 0
    
    # Process each group
    for group in groups:
        try:
            # Check if tag already exists first
            existing_tag = find_tag_by_name(group["name"])
            if existing_tag:
                existing_count += 1
                log.info(f"Tag already exists: {group['name']}")
            else:
                # Create new tag
                result = process_group_to_tag(group)
                if result:
                    created_count += 1
                else:
                    failed_count += 1
        except Exception as e:
            log.error(f"Error processing group {group['name']}: {str(e)}")
            failed_count += 1
    
    # Summary
    log.info("=" * 50)
    log.info("Group to Tags conversion complete!")
    log.info(f"Total groups processed: {len(groups)}")
    log.info(f"Tags already existed: {existing_count}")
    log.info(f"New tags created: {created_count}")
    log.info(f"Failed to create: {failed_count}")
    log.info("=" * 50)

if __name__ == "__main__":
    main()