#!/usr/bin/env python3
"""
Dependency installer for bulk import performers plugin
Automatically installs required packages if missing
"""

import sys
import os
import subprocess
import platform
import pathlib

def install_module(module_name):
    """Install a Python module using pip"""
    try:
        # Check if already installed
        __import__(module_name)
        print(f"Module '{module_name}' is already installed.")
        return True
    except ImportError:
        pass
    
    try:
        print(f"Installing module '{module_name}'...")
        
        pip_args = ["--disable-pip-version-check"]
        
        # Handle Docker environments
        if is_docker():
            pip_args.append("--break-system-packages")
        
        cmd = [sys.executable, "-m", "pip", "install", module_name] + pip_args
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Successfully installed '{module_name}'")
            return True
        else:
            print(f"Failed to install '{module_name}': {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error installing '{module_name}': {str(e)}")
        return False

def is_docker():
    """Check if running in Docker environment"""
    cgroup = pathlib.Path('/proc/self/cgroup')
    return pathlib.Path('/.dockerenv').is_file() or (cgroup.is_file() and 'docker' in cgroup.read_text())

def install_requirements():
    """Install all required dependencies"""
    required_modules = [
        "stashapp-tools",
        "pydantic",
        "requests"
    ]
    
    print("Checking and installing required dependencies...")
    success = True
    
    for module in required_modules:
        if not install_module(module):
            success = False
    
    if success:
        print("All dependencies installed successfully!")
    else:
        print("Some dependencies failed to install. Please install manually.")
    
    return success

if __name__ == "__main__":
    install_requirements()