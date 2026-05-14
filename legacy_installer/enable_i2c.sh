#!/bin/bash

# Script to enable I2C interface on Raspberry Pi
# To be included in the RRR installation process

echo "=== Enabling I2C Interface for Rodent Refreshment Regulator ==="

# Function to check if script is run with sudo
check_sudo() {
    if [ "$(id -u)" -ne 0 ]; then
        echo "ERROR: This script must be run with sudo privileges."
        echo "Please run: sudo ./enable_i2c.sh"
        exit 1
    fi
}

# Function to enable I2C in config.txt
enable_i2c_config() {
    echo "Enabling I2C in /boot/config.txt..."
    
    # Check if I2C is already enabled
    if grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
        echo "I2C is already enabled in config.txt"
    else
        # Backup config file
        cp /boot/config.txt /boot/config.txt.bak
        echo "Backup created at /boot/config.txt.bak"
        
        # Add I2C configuration
        echo "dtparam=i2c_arm=on" >> /boot/config.txt
        echo "I2C enabled in config.txt"
    fi
}

# Function to load I2C kernel modules
load_i2c_modules() {
    echo "Loading I2C kernel modules..."
    
    # Load modules immediately
    modprobe i2c-dev
    modprobe i2c-bcm2708
    
    # Ensure modules are loaded at boot
    if ! grep -q "i2c-dev" /etc/modules; then
        echo "i2c-dev" >> /etc/modules
    fi
    
    if ! grep -q "i2c-bcm2708" /etc/modules; then
        echo "i2c-bcm2708" >> /etc/modules
    fi
    
    echo "I2C modules configured to load at boot"
}

# Function to install I2C tools
install_i2c_tools() {
    echo "Installing I2C tools..."
    apt-get update
    apt-get install -y i2c-tools python3-smbus
    echo "I2C tools installed"
}

# Function to add user to I2C group
add_user_to_i2c_group() {
    local username
    
    # If script is run with sudo, get the actual username
    if [ -n "$SUDO_USER" ]; then
        username="$SUDO_USER"
    else
        username="$USER"
    fi
    
    echo "Adding user '$username' to i2c group..."
    
    # Create i2c group if it doesn't exist
    getent group i2c > /dev/null || groupadd i2c
    
    # Add user to i2c group
    usermod -a -G i2c "$username"
    
    echo "User added to i2c group"
}

# Function to test I2C functionality
test_i2c() {
    echo "Testing I2C functionality..."
    if command -v i2cdetect > /dev/null; then
        echo "Running i2cdetect to scan for devices:"
        i2cdetect -y 1
        echo "Note: If you just enabled I2C, you may need to reboot to see devices."
    else
        echo "i2cdetect not found. I2C tools may not be installed correctly."
    fi
}

# Main execution
main() {
    check_sudo
    enable_i2c_config
    load_i2c_modules
    install_i2c_tools
    add_user_to_i2c_group
    test_i2c
    
    echo
    echo "=== I2C Interface Enabled Successfully ==="
    echo "For changes to take full effect, please reboot your Raspberry Pi."
    echo "After reboot, you can test I2C with: sudo i2cdetect -y 1"
    
    # Ask for reboot
    read -p "Would you like to reboot now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Rebooting..."
        reboot
    else
        echo "Please remember to reboot for all changes to take effect."
    fi
}

# Run the main function
main 