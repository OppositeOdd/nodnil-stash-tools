#!/bin/bash
# Script to install Python dependencies in Stash Docker container
# Run this on your Ubuntu Linux machine where Docker is running

echo "Installing Python dependencies in Stash Docker container..."

# Find the Stash container ID/name (adjust as needed)
CONTAINER=$(docker ps | grep stash | awk '{print $1}' | head -1)

if [ -z "$CONTAINER" ]; then
    echo "Error: Could not find running Stash container"
    echo "Please check your container name/ID manually:"
    docker ps
    exit 1
fi

echo "Found Stash container: $CONTAINER"

# Install dependencies in the container
echo "Installing pydantic..."
docker exec -it $CONTAINER pip install pydantic --break-system-packages

echo "Installing stashapp-tools..."
docker exec -it $CONTAINER pip install stashapp-tools --break-system-packages

echo "Verifying installations..."
docker exec -it $CONTAINER python3 -c "import pydantic; print('pydantic version:', pydantic.__version__)"
docker exec -it $CONTAINER python3 -c "import stashapi; print('stashapp-tools imported successfully')"

echo "Dependencies installed successfully!"
echo "You may need to restart the Stash container or reload plugins."