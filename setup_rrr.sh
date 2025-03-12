#!/bin/bash

# Rodent Refreshment Regulator Installation Script
# This script will install all necessary dependencies for running the RRR application

echo "=== Rodent Refreshment Regulator Installation Script ==="
echo "This script will install all dependencies and set up your Raspberry Pi"
echo ""

# Update package lists
echo "=== Updating package lists ==="
sudo apt-get update

# Install Python and pip if not already installed
echo "=== Installing Python and pip ==="
sudo apt-get install -y python3 python3-pip python3-venv

# Install required system packages
echo "=== Installing system dependencies ==="
sudo apt-get install -y git i2c-tools python3-smbus

# Enable I2C interface (needed for relay HATs)
echo "=== Enabling I2C interface ==="
if ! grep -q "dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
    echo "I2C interface enabled. A reboot will be required after installation."
else
    echo "I2C interface already enabled."
fi

# Create directory for the application if it doesn't exist
echo "=== Setting up application directory ==="
mkdir -p ~/rodent-refreshment-regulator
cd ~/rodent-refreshment-regulator

# Clone the repository if not already done
if [ ! -d ".git" ]; then
    echo "=== Cloning the repository ==="
    # Replace with actual repository URL if available
    read -p "Enter the repository URL (or press Enter to skip): " repo_url
    if [ ! -z "$repo_url" ]; then
        git clone "$repo_url" .
        echo "Repository cloned successfully."
    else
        echo "Skipping repository clone. Assuming files will be copied manually."
    fi
else
    echo "Repository already exists."
fi

# Create and activate a virtual environment
echo "=== Creating Python virtual environment ==="
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "=== Installing Python dependencies ==="
pip install --upgrade pip
pip install PyQt5==5.15.4 gitpython==3.1.31 requests==2.31.0 slack_sdk==3.21.3 RPi.GPIO==0.7.0 gpiozero==2.0.1 lgpio==0.2.2.0 smbus2==0.4.1 Flask==2.2.2 Jinja2==3.1.2 jsonschema==4.23.0 attrs==24.2.0 certifi==2024.8.30 idna==3.10 chardet==5.1.0 cryptography==38.0.4 matplotlib-inline==0.1.7

# Create a desktop shortcut
echo "=== Creating desktop shortcut ==="
cat > ~/Desktop/RRR.desktop << EOF
[Desktop Entry]
Type=Application
Name=Rodent Refreshment Regulator
Comment=Start the Rodent Refreshment Regulator application
Exec=bash -c "cd ~/rodent-refreshment-regulator && source venv/bin/activate && cd Project && python3 main.py"
Icon=applications-science
Terminal=false
Categories=Science;Lab;
EOF

chmod +x ~/Desktop/RRR.desktop

# Create a startup script
echo "=== Creating startup script ==="
cat > ~/rodent-refreshment-regulator/start_rrr.sh << EOF
#!/bin/bash
cd ~/rodent-refreshment-regulator
source venv/bin/activate
cd Project
python3 main.py
EOF

chmod +x ~/rodent-refreshment-regulator/start_rrr.sh

echo ""
echo "=== Installation complete! ==="
echo "To run the application, you can:"
echo "1. Double-click the desktop shortcut"
echo "2. Run the startup script: ~/rodent-refreshment-regulator/start_rrr.sh"
echo "3. Manually navigate to the Project directory and run: python3 main.py"
echo ""
echo "Note: A system reboot may be required for I2C changes to take effect."
echo "Would you like to reboot now? (y/n)"
read reboot_choice

if [[ $reboot_choice == "y" || $reboot_choice == "Y" ]]; then
    echo "Rebooting..."
    sudo reboot
else
    echo "Please remember to reboot your system later for I2C changes to take effect."
fi 