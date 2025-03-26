#!/bin/bash

# Rodent Refreshment Regulator Installation Script
# This script will install all necessary dependencies for running the RRR application

echo "=== Rodent Refreshment Regulator Installation Script ==="
echo "This script will install all dependencies and set up your Raspberry Pi"
echo ""

# Check if running with sudo (required for some operations)
if [ "$(id -u)" -ne 0 ]; then
    echo "Some installation steps require sudo privileges."
    echo "You will be prompted for your password when necessary."
fi

# Update package lists
echo "=== Updating package lists ==="
sudo apt-get update

# Install Python and pip if not already installed
echo "=== Installing Python and pip ==="
sudo apt-get install -y python3 python3-pip python3-venv

# Install required system packages - using system packages for PyQt5, RPi.GPIO, and data science libraries
echo "=== Installing system dependencies ==="
sudo apt-get install -y git i2c-tools python3-smbus python3-dev python3-pyqt5 python3-rpi.gpio python3-gpiozero python3-pandas python3-numpy

# Enable I2C interface (needed for relay HATs)
echo "=== Enabling I2C interface ==="
# Create a temporary script
cat > /tmp/enable_i2c_temp.sh << 'EOF'
#!/bin/bash

# Check if I2C is already enabled
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
    # Backup config file
    sudo cp /boot/config.txt /boot/config.txt.bak
    echo "Backup created at /boot/config.txt.bak"
    
    # Add I2C configuration
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt > /dev/null
    echo "I2C enabled in config.txt"
else
    echo "I2C is already enabled in config.txt"
fi

# Load modules immediately
sudo modprobe i2c-dev
sudo modprobe i2c-bcm2708 || echo "Module i2c-bcm2708 not available on this system"

# Ensure modules are loaded at boot
if ! grep -q "i2c-dev" /etc/modules; then
    echo "i2c-dev" | sudo tee -a /etc/modules > /dev/null
fi

# Create i2c group if it doesn't exist
getent group i2c > /dev/null || sudo groupadd i2c

# Add user to i2c group
sudo usermod -a -G i2c $USER
echo "User added to i2c group"

# Test I2C functionality
echo "Testing I2C functionality..."
if command -v i2cdetect > /dev/null; then
    echo "Running i2cdetect to scan for devices:"
    sudo i2cdetect -y 1
    echo "Note: If you just enabled I2C, you may need to reboot to see devices."
else
    echo "i2cdetect not found. Installing I2C tools..."
    sudo apt-get install -y i2c-tools
fi
EOF

# Make the temporary script executable and run it
chmod +x /tmp/enable_i2c_temp.sh
/tmp/enable_i2c_temp.sh
rm /tmp/enable_i2c_temp.sh

# Create directory for the application if it doesn't exist
echo "=== Setting up application directory ==="
mkdir -p ~/rodent-refreshment-regulator
cd ~/rodent-refreshment-regulator

# Set repository URL
REPO_URL="https://github.com/Corticomics/rodRefReg.git"

# Clone the repository if not already done
if [ ! -d ".git" ]; then
    echo "=== Cloning the repository ==="
    echo "Using repository: $REPO_URL"
    git clone "$REPO_URL" .
    echo "Repository cloned successfully."
else
    echo "Repository already exists. Updating..."
    git pull
fi

# Create virtual environment with access to system packages 
# (this is critical for PyQt5 and RPi.GPIO)
echo "=== Creating Python virtual environment with system packages ==="
python3 -m venv venv --system-site-packages
source venv/bin/activate

# Create a modified requirements file without the problematic packages
echo "=== Creating modified requirements file ==="
if [ -f "installer/requirements.txt" ]; then
    grep -v -E 'PyQt5|RPi\.GPIO|gpiozero|pandas|numpy' installer/requirements.txt > /tmp/requirements_modified.txt
    REQUIREMENTS_PATH="/tmp/requirements_modified.txt"
elif [ -f "requirements.txt" ]; then
    grep -v -E 'PyQt5|RPi\.GPIO|gpiozero|pandas|numpy' requirements.txt > /tmp/requirements_modified.txt
    REQUIREMENTS_PATH="/tmp/requirements_modified.txt"
else
    echo "No requirements.txt found, will install packages individually."
    REQUIREMENTS_PATH=""
fi

# Install Python dependencies
echo "=== Installing Python dependencies ==="
pip install --upgrade pip

# If we have a modified requirements file, use it
if [ -n "$REQUIREMENTS_PATH" ]; then
    echo "Installing dependencies from modified requirements file..."
    # Use --break-system-packages only if needed
    if pip install -r "$REQUIREMENTS_PATH"; then
        echo "Dependencies installed successfully."
    else
        echo "Initial installation failed, trying with --break-system-packages..."
        pip install --break-system-packages -r "$REQUIREMENTS_PATH"
    fi
else
    echo "Installing essential packages individually..."
    # Install everything except problem packages
    pip install gitpython==3.1.31 requests==2.31.0 slack_sdk==3.21.3 lgpio==0.2.2.0 smbus2==0.4.1 Flask==2.2.2 Jinja2==3.1.2 jsonschema==4.23.0 attrs==24.2.0 certifi==2024.8.30 idna==3.10 chardet==5.1.0 cryptography==38.0.4 matplotlib-inline==0.1.7
fi

# Verify slack_sdk installation
echo "=== Verifying slack_sdk installation ==="
if pip show slack_sdk > /dev/null; then
    echo "slack_sdk is installed correctly."
else
    echo "Installing slack_sdk separately..."
    pip install slack_sdk==3.21.3 --break-system-packages
fi

# Verify PyQt5 is accessible from the virtual environment
echo "=== Verifying PyQt5 is accessible ==="
python3 -c "import PyQt5.QtCore; print('PyQt5 version:', PyQt5.QtCore.PYQT_VERSION_STR)" || {
    echo "Warning: PyQt5 still not accessible through the usual import."
    echo "Trying alternate import method..."
    python3 -c "import PyQt5; from PyQt5 import QtCore; print('PyQt5 works with alternate import')" || {
        echo "Error: PyQt5 is still not accessible. Installing with pip as a last resort..."
        sudo apt-get install -y python3-dev qt5-qmake qtbase5-dev
        pip install PyQt5==5.15.4 --break-system-packages
    }
}

# Verify RPi.GPIO is accessible
echo "=== Verifying RPi.GPIO is accessible ==="
python3 -c "import RPi.GPIO; print('RPi.GPIO version:', RPi.GPIO.VERSION)" || {
    echo "Warning: RPi.GPIO not accessible. Trying with --break-system-packages..."
    sudo apt-get install -y python3-rpi.gpio
    pip install RPi.GPIO --break-system-packages
}

# Verify pandas is accessible
echo "=== Verifying pandas is accessible ==="
python3 -c "import pandas; print('pandas version:', pandas.__version__)" || {
    echo "Warning: pandas not accessible. Installing..."
    sudo apt-get install -y python3-pandas
    # If system package doesn't work, try pip
    python3 -c "import pandas" || pip install pandas --break-system-packages
}

# Create a desktop shortcut
echo "=== Creating desktop shortcut ==="
mkdir -p ~/Desktop
cat > ~/Desktop/RRR.desktop << EOF
[Desktop Entry]
Type=Application
Name=Rodent Refreshment Regulator
Comment=Start the Rodent Refreshment Regulator application
Exec=bash -c "cd ~/rodent-refreshment-regulator && source venv/bin/activate && cd Project && python3 main.py"
Icon=applications-science
Terminal=true
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

# Create a test script
echo "=== Creating hardware test script ==="
cat > ~/rodent-refreshment-regulator/test_hardware.sh << EOF
#!/bin/bash
cd ~/rodent-refreshment-regulator
source venv/bin/activate
cd Project

echo "Testing I2C devices..."
sudo i2cdetect -y 1

if [ -f "test_relay_connection.py" ]; then
    echo "Testing relay connection..."
    python3 test_relay_connection.py
else
    echo "Relay test script not found."
fi
EOF

chmod +x ~/rodent-refreshment-regulator/test_hardware.sh

# Create a diagnostic script to help debug launch issues
echo "=== Creating diagnostic script ==="
cat > ~/rodent-refreshment-regulator/diagnose.sh << 'EOF'
#!/bin/bash
echo "=== RRR Diagnostic Script ==="
echo "Checking environment..."
cd ~/rodent-refreshment-regulator
echo "Current directory: $(pwd)"

echo "Activating virtual environment..."
source venv/bin/activate
echo "Python path: $(which python3)"
echo "Python version: $(python3 --version)"

echo "Checking for required libraries..."
python3 -c "import PyQt5; print('PyQt5 found')" || echo "PyQt5 not found"
python3 -c "import pandas; print('pandas found')" || echo "pandas not found"
python3 -c "import RPi.GPIO; print('RPi.GPIO found')" || echo "RPi.GPIO not found"
python3 -c "import slack_sdk; print('slack_sdk found')" || echo "slack_sdk not found"

echo "Checking for Project directory..."
if [ -d "Project" ]; then
    echo "Project directory exists"
    cd Project
    echo "Checking for main.py..."
    if [ -f "main.py" ]; then
        echo "main.py exists"
        echo "Would you like to try running main.py? (y/n)"
        read choice
        if [[ $choice == "y" ]]; then
            echo "Attempting to run main.py..."
            python3 main.py
        else
            echo "Skipped running main.py"
        fi
    else
        echo "ERROR: main.py not found!"
        echo "Files in Project directory:"
        ls -la
    fi
else
    echo "ERROR: Project directory not found!"
    echo "Contents of rodent-refreshment-regulator:"
    ls -la
fi
EOF

chmod +x ~/rodent-refreshment-regulator/diagnose.sh

# Add quick fix script for missing pandas
echo "=== Creating quick fix script for missing packages ==="
cat > ~/rodent-refreshment-regulator/fix_dependencies.sh << 'EOF'
#!/bin/bash
echo "=== RRR Dependency Fix Script ==="
cd ~/rodent-refreshment-regulator
source venv/bin/activate

echo "Installing pandas..."
sudo apt-get install -y python3-pandas
python3 -c "import pandas" || pip install pandas --break-system-packages

echo "Checking if pandas is now available..."
python3 -c "import pandas; print('pandas version:', pandas.__version__)" && echo "pandas installed successfully!"

echo "Installing any other potential missing packages..."
pip install -y numpy matplotlib seaborn scipy scikit-learn statsmodels --break-system-packages

echo "All dependencies should now be installed. Try running the application again."
EOF

chmod +x ~/rodent-refreshment-regulator/fix_dependencies.sh

echo ""
echo "=== Installation complete! ==="
echo "To run the application, you can:"
echo "1. Double-click the desktop shortcut"
echo "2. Run the startup script: ~/rodent-refreshment-regulator/start_rrr.sh"
echo "3. Manually navigate to the Project directory and run: python3 main.py"
echo ""
echo "If you encounter missing package errors:"
echo "Run: ~/rodent-refreshment-regulator/fix_dependencies.sh"
echo ""
echo "To diagnose problems:"
echo "Run: ~/rodent-refreshment-regulator/diagnose.sh"
echo ""
echo "To test hardware connectivity:"
echo "Run: ~/rodent-refreshment-regulator/test_hardware.sh"
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