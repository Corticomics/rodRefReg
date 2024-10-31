#!/usr/bin/env python3
"""
installer_backend.py

This script performs privileged actions required during the installation of the RRR application.
It is intended to be called from the main installer script using pkexec.
"""

import sys
import os
import logging

# Configure logging
logging.basicConfig(
    filename='installer_backend.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def create_config_file(temp_config_file, config_path):
    try:
        with open(temp_config_file, 'r') as f:
            config_content = f.read()
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            f.write(config_content)
        os.chmod(config_path, 0o600)  # Restrict permissions
        logging.info("Configuration file created at %s", config_path)
        # Clean up temporary file
        os.remove(temp_config_file)
    except Exception as e:
        logging.error("Failed to create configuration file: %s", e)
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: installer_backend.py action [parameters]")
        sys.exit(1)

    action = sys.argv[1]
    if action == 'create_config_file':
        temp_config_file = sys.argv[2]
        config_path = sys.argv[3]
        create_config_file(temp_config_file, config_path)
    else:
        print("Unknown action:", action)
        sys.exit(1)

if __name__ == '__main__':
    main()
