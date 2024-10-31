#!/usr/bin/env python3
"""
installer_backend.py

This script performs privileged actions required during the installation of the RRR application.
It is intended to be called from the main installer script using pkexec.
"""

import sys
import os
import subprocess
import logging

# Configure logging
logging.basicConfig(
    filename='installer_backend.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def install_system_dependencies(packages):
    try:
        subprocess.check_call(['apt-get', 'update'])
        subprocess.check_call(['apt-get', 'install', '-y'] + packages)
        logging.info("System dependencies installed successfully.")
    except subprocess.CalledProcessError as e:
        logging.error("Failed to install system dependencies: %s", e)
        sys.exit(1)

def install_python_packages(packages):
    try:
        subprocess.check_call(['pip3', 'install'] + packages)
        logging.info("Python packages installed successfully.")
    except subprocess.CalledProcessError as e:
        logging.error("Failed to install Python packages: %s", e)
        sys.exit(1)

def clone_repository(repo_url, dest_path):
    try:
        if not os.path.exists(dest_path):
            subprocess.check_call(['git', 'clone', repo_url, dest_path])
            logging.info("Repository cloned successfully.")
        else:
            subprocess.check_call(['git', '-C', dest_path, 'pull'])
            logging.info("Repository updated successfully.")
    except subprocess.CalledProcessError as e:
        logging.error("Failed to clone or update repository: %s", e)
        sys.exit(1)

def create_config_file(config_content, config_path):
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            f.write(config_content)
        os.chmod(config_path, 0o600)  # Restrict permissions
        logging.info("Configuration file created at %s", config_path)
    except Exception as e:
        logging.error("Failed to create configuration file: %s", e)
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: installer_backend.py action [parameters]")
        sys.exit(1)

    action = sys.argv[1]
    if action == 'install_system_dependencies':
        packages = sys.argv[2:]
        install_system_dependencies(packages)
    elif action == 'install_python_packages':
        packages = sys.argv[2:]
        install_python_packages(packages)
    elif action == 'clone_repository':
        repo_url = sys.argv[2]
        dest_path = sys.argv[3]
        clone_repository(repo_url, dest_path)
    elif action == 'create_config_file':
        # Read config content from a temporary file to avoid command-line issues
        temp_config_file = sys.argv[2]
        config_path = sys.argv[3]
        with open(temp_config_file, 'r') as f:
            config_content = f.read()
        create_config_file(config_content, config_path)
        # Clean up temporary file
        os.remove(temp_config_file)
    else:
        print("Unknown action:", action)
        sys.exit(1)

if __name__ == '__main__':
    main()
