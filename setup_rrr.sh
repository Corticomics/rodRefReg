#!/bin/bash

# Rodent Refreshment Regulator Installation Script
# This script will install all necessary dependencies for running the RRR application

# Set error handling
set -e  # Exit on error
trap 'echo "Error occurred at line $LINENO. Command: $BASH_COMMAND"' ERR

# Create log file
INSTALL_LOG="$HOME/rrr_install_$(date +%Y%m%d_%H%M%S).log"
echo "=== Rodent Refreshment Regulator Installation Log ===" > "$INSTALL_LOG"
echo "Started: $(date)" >> "$INSTALL_LOG"

# Log function
log() {
    echo "$1"
    echo "$(date +%H:%M:%S): $1" >> "$INSTALL_LOG"
}

# Error function
error_exit() {
    log "ERROR: $1"
    log "Installation failed. Check the log file at $INSTALL_LOG for details."
    exit 1
}

# Success function
success() {
    log "SUCCESS: $1"
}

# Check for internet connection
log "Checking internet connection..."
if ! ping -c 1 github.com &> /dev/null && ! ping -c 1 8.8.8.8 &> /dev/null; then
    error_exit "No internet connection detected. Please check your network and try again."
fi
log "✓ Internet connection verified"

# Check disk space (need at least 1GB free)
log "Checking available disk space..."
AVAILABLE_SPACE=$(df -BM --output=avail $HOME | tail -n 1 | tr -d 'M')
if [ "$AVAILABLE_SPACE" -lt 1000 ]; then
    error_exit "Not enough disk space. Need at least 1GB free, but only have ${AVAILABLE_SPACE}MB"
fi
log "Available disk space: ${AVAILABLE_SPACE}MB - OK"

# Check for Raspberry Pi
log "Checking for Raspberry Pi hardware..."
if [ -f /proc/cpuinfo ]; then
    if ! grep -q "Raspberry Pi" /proc/cpuinfo && ! grep -q "BCM" /proc/cpuinfo; then
        log "Warning: This doesn't appear to be a Raspberry Pi. Some hardware features may not work."
    else
        log "Raspberry Pi detected - OK"
    fi
else
    log "Warning: Unable to determine hardware type. Assuming compatible hardware."
fi

log "=== Rodent Refreshment Regulator Installation Script ==="
log "This script will install all dependencies and set up your Raspberry Pi"
log ""

# SECURITY: Detect real user and target directory correctly (must be early in script)
if [ -n "$SUDO_USER" ]; then
    REAL_USER="$SUDO_USER"
    REAL_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    log "Security: Running with sudo, installing for user: $REAL_USER at $REAL_HOME"
else
    REAL_USER="$USER"
    REAL_HOME="$HOME"
fi

# Prevent root user installation
if [ "$REAL_USER" = "root" ]; then
    error_exit "This installer should not be run as root user directly. Use your regular user account."
fi

TARGET_DIR="$REAL_HOME/rodent-refreshment-regulator"

# PRIVILEGE SEPARATION: Functions to run operations with correct privileges
run_as_user() {
    if [ "$(id -u)" -eq 0 ]; then
        # Running as root, drop privileges to real user
        sudo -u "$REAL_USER" -H "$@"
    else
        # Already running as user
        "$@"
    fi
}

# Check if running with sudo (required for some operations)
if [ "$(id -u)" -ne 0 ]; then
    log "Some installation steps require sudo privileges."
    log "You will be prompted for your password when necessary."
fi

# Update package lists
log "=== Updating package lists ==="
sudo apt-get update || error_exit "Failed to update package lists"

# Install Python and pip if not already installed
log "=== Installing Python and pip ==="
sudo apt-get install -y python3 python3-pip python3-venv || error_exit "Failed to install Python and pip"

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
log "Python version: $PYTHON_VERSION"
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
if [ $PYTHON_MAJOR -lt 3 ] || [ $PYTHON_MAJOR -eq 3 -a $PYTHON_MINOR -lt 6 ]; then
    error_exit "Python version must be at least 3.6. Found: $PYTHON_VERSION"
fi

# Install required system packages - using system packages for PyQt5, RPi.GPIO, and data science libraries
log "=== Installing system dependencies ==="
sudo apt-get install -y git i2c-tools python3-smbus python3-dev python3-pyqt5 python3-rpi.gpio python3-gpiozero python3-pandas python3-numpy build-essential || error_exit "Failed to install system dependencies"

# Install Sequent Microsystems 16-relay HAT driver
log "=== Installing Sequent Microsystems 16-relay HAT driver ==="
if [ ! -d "/tmp/16relind-rpi" ]; then
    log "Cloning 16relind-rpi repository..."
    git clone https://github.com/SequentMicrosystems/16relind-rpi.git /tmp/16relind-rpi || error_exit "Failed to clone 16relind-rpi repository"
    cd /tmp/16relind-rpi
    log "Installing relay HAT driver..."
    sudo make install || log "Warning: make install for 16relind-rpi failed, but continuing"
    cd - > /dev/null
else
    log "16relind-rpi repository already exists, updating..."
    cd /tmp/16relind-rpi
    git pull || log "Warning: git pull for 16relind-rpi failed, but continuing with existing code"
    log "Reinstalling relay HAT driver..."
    sudo make install || log "Warning: make install for 16relind-rpi failed, but continuing"
    cd - > /dev/null
fi

# Verify 16relind command is available
if command -v 16relind > /dev/null; then
    log "16relind command installed successfully."
else
    log "Warning: 16relind command not found after installation."
fi

# Install Python library for SM16relind if available
if [ -d "/tmp/16relind-rpi/python" ]; then
    log "Installing Python library for SM16relind..."
    cd /tmp/16relind-rpi/python
    sudo python3 setup.py install || log "Warning: SM16relind Python installation failed, but continuing"
    cd - > /dev/null
fi

# Enable I2C interface (needed for relay HATs)
log "=== Enabling I2C interface ==="
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
    # Raspberry Pi 5 uses different I2C bus numbers (13, 14) instead of the traditional (0, 1)
    # Scan all available buses
    for bus_num in $(ls /dev/i2c-* 2>/dev/null | sed 's/.*i2c-//'); do
        echo "Scanning I2C bus $bus_num:"
        sudo i2cdetect -y $bus_num
    done
    echo "Note: If you just enabled I2C, you may need to reboot to see devices."
else
    echo "i2cdetect not found. Installing I2C tools..."
    sudo apt-get install -y i2c-tools
fi
EOF

# Make the temporary script executable and run it
chmod +x /tmp/enable_i2c_temp.sh
/tmp/enable_i2c_temp.sh || log "Warning: I2C setup encountered issues, but continuing"
rm /tmp/enable_i2c_temp.sh

# Enhanced I2C bus detection and configuration
log "=== Enhanced I2C Bus Detection ==="
log "Checking for available I2C buses..."

# Function to detect available I2C buses
detect_i2c_buses() {
    local available_buses=()
    for i in $(seq 0 20); do
        if [ -e "/dev/i2c-$i" ]; then
            available_buses+=("$i")
        fi
    done
    echo "${available_buses[@]}"
}

# Get available I2C buses
AVAILABLE_BUSES=($(detect_i2c_buses))

if [ ${#AVAILABLE_BUSES[@]} -eq 0 ]; then
    log "No I2C buses detected. You may need to reboot for I2C changes to take effect."
    log "After reboot, the system will auto-detect available I2C buses."
else
    log "Detected I2C buses: ${AVAILABLE_BUSES[*]}"
    
    # Create a script to auto-detect and configure I2C buses at runtime
    cat > /tmp/configure_i2c.sh << 'EOI'
#!/bin/bash

# Configure I2C - Automatically detect and use available I2C buses
# Optimized for Raspberry Pi 5 with new I2C bus addressing (buses 13, 14)
echo "Configuring I2C bus detection for Rodent Refreshment Regulator..."

# Detect available I2C buses
AVAILABLE_BUSES=()
for i in $(seq 0 50); do  # Extended range for Pi 5
    if [ -e "/dev/i2c-$i" ]; then
        AVAILABLE_BUSES+=("$i")
        echo "Found I2C bus: /dev/i2c-$i"
    fi
done

if [ ${#AVAILABLE_BUSES[@]} -eq 0 ]; then
    echo "Error: No I2C buses detected!"
    echo "Please check that I2C is enabled in raspi-config"
    echo "For Raspberry Pi 5, ensure dtparam=i2c_arm=on is in /boot/firmware/config.txt"
    exit 1
fi

# For Raspberry Pi 5, prefer higher numbered buses (13, 14)
PRIMARY_BUS=${AVAILABLE_BUSES[-1]}  # Last (highest) bus
echo "Will use primary I2C bus: /dev/i2c-$PRIMARY_BUS"

# Run fix_i2c.py if available with virtual environment
cd ~/rodent-refreshment-regulator
if [ -f "Project/fix_i2c.py" ]; then
    echo "Running I2C fix script with proper Python environment..."
    source venv/bin/activate 2>/dev/null || echo "Warning: Could not activate virtual environment"
    cd Project
    chmod +x fix_i2c.py
    python3 fix_i2c.py
    cd ..
    echo "I2C configuration complete."
fi

# Test with i2cdetect on all available buses
for bus in "${AVAILABLE_BUSES[@]}"; do
    echo "Testing I2C bus $bus:"
    if timeout 10 sudo i2cdetect -y $bus; then
        echo "✓ Bus $bus is responsive"
    else
        echo "⚠ Bus $bus timeout or error"
    fi
done

# Display bus recommendations
echo ""
echo "I2C Bus Configuration Summary:"
echo "Available buses: ${AVAILABLE_BUSES[*]}"
if [[ " ${AVAILABLE_BUSES[*]} " =~ " 13 " ]] || [[ " ${AVAILABLE_BUSES[*]} " =~ " 14 " ]]; then
    echo "✓ Raspberry Pi 5 detected (buses 13/14 present)"
    echo "✓ Using modern I2C configuration"
else
    echo "ℹ Traditional Raspberry Pi I2C configuration detected"
fi
EOI

    chmod +x /tmp/configure_i2c.sh
    
    # Create tools directory and properly use it
    run_as_user mkdir -p "$TARGET_DIR/tools"
    run_as_user cp /tmp/configure_i2c.sh "$TARGET_DIR/tools/configure_i2c.sh"
    run_as_user chmod +x "$TARGET_DIR/tools/configure_i2c.sh"
    
    # Also put a copy in the root directory for compatibility with existing scripts  
    run_as_user cp "$TARGET_DIR/tools/configure_i2c.sh" "$TARGET_DIR/configure_i2c.sh"
    run_as_user chmod +x "$TARGET_DIR/configure_i2c.sh"
fi

# Smart installation directory setup - handles all execution contexts
log "=== Setting up application directory ==="

# Set repository URL
REPO_URL="https://github.com/Corticomics/rodRefReg.git"

# Function to detect current execution context
detect_execution_context() {
    local current_dir=$(pwd)
    local current_basename=$(basename "$current_dir")
    
    # Check if we're already in a git repository
    if [ -d ".git" ]; then
        local repo_url=$(git remote get-url origin 2>/dev/null || echo "")
        if [[ "$repo_url" == *"rodRefReg"* ]] || [[ "$repo_url" == *"rodent-refreshment-regulator"* ]]; then
            echo "EXISTING_REPO"
            return
        fi
    fi
    
    # Check if we're in the target directory
    if [ "$current_dir" = "$TARGET_DIR" ]; then
        echo "TARGET_DIR"
        return
    fi
    
    # Check if target directory exists and is a valid git repo
    if [ -d "$TARGET_DIR/.git" ]; then
        echo "TARGET_EXISTS_VALID_REPO"
        return
    fi
    
    # Check if target directory exists (but isn't a git repo)
    if [ -d "$TARGET_DIR" ]; then
        echo "TARGET_EXISTS_INVALID_REPO"
        return
    fi
    
    # Default case - fresh installation
    echo "FRESH_INSTALL"
}

# Execute context-aware installation
CONTEXT=$(detect_execution_context)
log "Detected execution context: $CONTEXT"

case $CONTEXT in
    "EXISTING_REPO")
        log "Running from existing repository - setting up in place"
        
        # Ask user about repository handling
        echo ""
        echo "🔄 Repository Update Options:"
        echo "1. Keep existing repository and try to update (preserves any local changes)"
        echo "2. Fresh clone from GitHub (overwrites any local changes with latest version)"
        echo ""
        read -p "Choose option (1 or 2, default is 1): " -r repo_choice
        echo ""
        
        if [[ "$repo_choice" == "2" ]]; then
            log "User chose fresh clone - removing existing repository"
            current_dir=$(pwd)
            cd /tmp
            rm -rf "$current_dir"
            
            # Fresh clone
            log "Fresh cloning repository to target directory"
            run_as_user git clone "$REPO_URL" "$TARGET_DIR" || error_exit "Failed to clone repository"
            cd "$TARGET_DIR" || error_exit "Failed to change to target directory"
            log "Fresh repository cloned successfully"
        else
            log "User chose to keep existing repository"
            
            # If we're not in the target directory, copy/move to target
            if [ "$(pwd)" != "$TARGET_DIR" ]; then
                log "Moving repository to standard location: $TARGET_DIR"
                
                # Create backup if target exists
                if [ -d "$TARGET_DIR" ]; then
                    backup_dir="${TARGET_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
                    log "Creating backup: $backup_dir"
                    mv "$TARGET_DIR" "$backup_dir"
                fi
                
                # Copy current repo to target location
                run_as_user cp -r "$(pwd)" "$TARGET_DIR"
                cd "$TARGET_DIR" || error_exit "Failed to change to target directory"
            fi
            
            # Configure git to handle divergent branches
            git config pull.rebase false || log "Warning: could not set git config"
            
            # Update the repository with conflict resolution
            log "Updating repository..."
            if ! git fetch origin; then
                log "Warning: fetch failed, continuing with existing code"
            else
                # Try to pull with automatic conflict resolution
                if ! git pull origin main; then
                    if ! git pull origin master; then
                        log "Warning: pull failed due to conflicts, resetting to remote state"
                        # Stash any local changes and reset to remote
                        git stash push -m "Auto-stash during installation $(date)" || true
                        git reset --hard origin/main || git reset --hard origin/master || log "Warning: could not reset to remote"
                    fi
                fi
            fi
        fi
        ;;
        
    "TARGET_DIR")
        log "Already in target directory - updating repository"
        if [ -d ".git" ]; then
            git fetch origin || log "Warning: fetch failed, continuing"
            git pull origin main || git pull origin master || log "Warning: pull failed, continuing"
        else
            log "Warning: In target directory but no git repository found"
            # Try to initialize from remote
            run_as_user git clone "$REPO_URL" temp_clone || error_exit "Failed to clone repository"
            run_as_user cp -r temp_clone/* .
            run_as_user cp -r temp_clone/.git .
            run_as_user rm -rf temp_clone
        fi
        ;;
        
    "TARGET_EXISTS_VALID_REPO")
        log "Target directory exists with valid git repository - updating installation"
        cd "$TARGET_DIR" || error_exit "Failed to change to target directory"
        log "Valid git repository found, updating..."
        run_as_user git fetch origin || log "Warning: fetch failed, continuing"
        run_as_user git pull origin main || run_as_user git pull origin master || log "Warning: pull failed, continuing"
        ;;
        
    "TARGET_EXISTS_INVALID_REPO")
        log "Target directory exists but is not a valid git repository - performing fresh clone"
        # Create backup of existing directory
        backup_dir="${TARGET_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
        log "Creating backup: $backup_dir"
        mv "$TARGET_DIR" "$backup_dir" || log "Warning: backup failed"
        
                    # Fresh clone
            log "Cloning fresh repository..."
            run_as_user git clone "$REPO_URL" "$TARGET_DIR" || error_exit "Failed to clone repository"
        cd "$TARGET_DIR" || error_exit "Failed to change to target directory"
        log "Fresh repository cloned successfully"
        ;;
        
    "FRESH_INSTALL")
        log "Fresh installation - cloning repository to target directory"
        
        # Create parent directory if needed
        run_as_user mkdir -p "$(dirname "$TARGET_DIR")"
        
        # Clone repository
        run_as_user git clone "$REPO_URL" "$TARGET_DIR" || error_exit "Failed to clone repository"
        cd "$TARGET_DIR" || error_exit "Failed to change to target directory"
        log "Repository cloned successfully to $TARGET_DIR"
        ;;
        
    *)
        error_exit "Unknown execution context: $CONTEXT"
        ;;
esac

# Verify we're in the correct location with the correct structure
if [ ! -f "Project/main.py" ]; then
    error_exit "Installation verification failed - Project/main.py not found in $(pwd)"
fi

log "✓ Repository setup complete - using directory: $(pwd)"

# SECURITY: Fix ownership of all files to ensure they belong to the real user
log "=== Setting correct file ownership ==="
if [ "$(id -u)" -eq 0 ] && [ -n "$REAL_USER" ]; then
    chown -R "$REAL_USER:$REAL_USER" "$TARGET_DIR"
    log "✓ File ownership set to $REAL_USER"
fi

# Create virtual environment with access to system packages 
# (this is critical for PyQt5 and RPi.GPIO)
log "=== Creating Python virtual environment with system packages ==="
run_as_user python3 -m venv venv --system-site-packages || error_exit "Failed to create virtual environment"

# Activate virtual environment and set up dependencies (all as real user)
log "=== Setting up Python dependencies ==="
run_as_user bash -c "
    source venv/bin/activate
    
    # Install pip packages as the real user
    pip install --upgrade pip || echo 'Warning: pip upgrade failed'
    
    # Install essential packages
    pip install gitpython==3.1.31 requests==2.31.0 slack_sdk==3.21.3 lgpio==0.2.2.0 smbus2==0.4.1 Flask==2.2.2 Jinja2==3.1.2 jsonschema==4.23.0 attrs==24.2.0 certifi==2024.8.30 idna==3.10 chardet==5.1.0 cryptography==38.0.4 matplotlib-inline==0.1.7 || pip install --break-system-packages gitpython==3.1.31 requests==2.31.0 slack_sdk==3.21.3 lgpio==0.2.2.0 smbus2==0.4.1 Flask==2.2.2 Jinja2==3.1.2 jsonschema==4.23.0 attrs==24.2.0 certifi==2024.8.30 idna==3.10 chardet==5.1.0 cryptography==38.0.4 matplotlib-inline==0.1.7
"

# Create a modified requirements file without the problematic packages (if needed)
log "=== Creating modified requirements file ==="
if [ -f "installer/requirements.txt" ]; then
    grep -v -E 'PyQt5|RPi\.GPIO|gpiozero|pandas|numpy' installer/requirements.txt > /tmp/requirements_modified.txt
    REQUIREMENTS_PATH="/tmp/requirements_modified.txt"
elif [ -f "requirements.txt" ]; then
    grep -v -E 'PyQt5|RPi\.GPIO|gpiozero|pandas|numpy' requirements.txt > /tmp/requirements_modified.txt
    REQUIREMENTS_PATH="/tmp/requirements_modified.txt"
else
    log "No requirements.txt found, will install packages individually."
    REQUIREMENTS_PATH=""
fi

# Dependencies already installed in user context above
log "=== Python dependencies installed successfully ==="

# Verify slack_sdk installation
log "=== Verifying slack_sdk installation ==="
if pip show slack_sdk > /dev/null; then
    log "slack_sdk is installed correctly."
else
    log "Installing slack_sdk separately..."
    pip install slack_sdk==3.21.3 --break-system-packages || error_exit "Failed to install slack_sdk"
fi

# Verify PyQt5 is accessible from the virtual environment
log "=== Verifying PyQt5 is accessible ==="
python3 -c "import PyQt5.QtCore; print('PyQt5 version:', PyQt5.QtCore.PYQT_VERSION_STR)" || {
    log "Warning: PyQt5 still not accessible through the usual import."
    log "Trying alternate import method..."
    python3 -c "import PyQt5; from PyQt5 import QtCore; print('PyQt5 works with alternate import')" || {
        log "Error: PyQt5 is still not accessible. Installing with pip as a last resort..."
        sudo apt-get install -y python3-dev qt5-qmake qtbase5-dev
        pip install PyQt5==5.15.4 --break-system-packages || error_exit "Failed to install PyQt5"
    }
}

# Verify RPi.GPIO is accessible
log "=== Verifying RPi.GPIO is accessible ==="
python3 -c "import RPi.GPIO; print('RPi.GPIO version:', RPi.GPIO.VERSION)" || {
    log "Warning: RPi.GPIO not accessible. Trying with --break-system-packages..."
    sudo apt-get install -y python3-rpi.gpio
    pip install RPi.GPIO --break-system-packages || error_exit "Failed to install RPi.GPIO"
}

# Verify pandas is accessible
log "=== Verifying pandas is accessible ==="
python3 -c "import pandas; print('pandas version:', pandas.__version__)" || {
    log "Warning: pandas not accessible. Installing..."
    sudo apt-get install -y python3-pandas || error_exit "Failed to install pandas"
    # If system package doesn't work, try pip
    python3 -c "import pandas" || pip install pandas --break-system-packages || error_exit "Failed to install pandas"
}

# Verify SM16relind Python module can be imported (if it exists)
log "=== Verifying SM16relind module is accessible ==="
python3 -c "
try: 
    import SM16relind
    print('SM16relind module found')
except ImportError: 
    print('SM16relind module not found, but command line tool should work')
" || {
    log "Note: SM16relind Python module not found. This is normal if the module uses command line tools instead."
    # Try symlink if the lib directory exists but install didn't work
    if [ -d "/usr/local/lib/python3*/dist-packages/SM16relind" ]; then
        log "Found SM16relind module in system packages, creating symlink to virtual environment..."
        SM_PATH=$(find /usr/local/lib/python3*/dist-packages -name "SM16relind" -type d | head -n 1)
        if [ -n "$SM_PATH" ]; then
            PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
            run_as_user mkdir -p "$TARGET_DIR/venv/lib/python$PY_VERSION/site-packages/"
            run_as_user ln -sf $SM_PATH "$TARGET_DIR/venv/lib/python$PY_VERSION/site-packages/"
            log "Symlink created."
        fi
    fi
}

# Test and validate 16relind relay HAT functionality with Raspberry Pi 5 configuration
log "=== Testing 16relind Relay HAT Functionality ==="
if command -v 16relind > /dev/null; then
    log "Testing relay HAT communication on detected I2C buses..."
    
    # Test relay command on available buses
    HAT_FOUND=false
    for bus in "${AVAILABLE_BUSES[@]}"; do
        log "Testing relay HAT on I2C bus $bus..."
        
        # Try to get relay status (non-destructive test)
        if timeout 5 16relind 0 read all 2>/dev/null | grep -q "0\|1"; then
            log "✓ Relay HAT responding on bus $bus"
            HAT_FOUND=true
            break
        else
            log "No response from relay HAT on bus $bus"
        fi
    done
    
    if [ "$HAT_FOUND" = true ]; then
        log "✓ Relay HAT communication verified"
        
        # Test custom Python module with proper bus detection
        log "Testing custom SM16relind Python module..."
        python3 -c "
import sys
import os
sys.path.insert(0, 'Project/gpio')
try:
    from custom_SM16relind import find_available_i2c_buses, test_connection
    buses = find_available_i2c_buses()
    print(f'Python module detected I2C buses: {buses}')
    
    if buses:
        print('✓ Custom SM16relind module is working correctly')
        print(f'✓ Raspberry Pi 5 I2C configuration detected: {any(b >= 13 for b in buses)}')
    else:
        print('⚠ No I2C buses detected by Python module')
except Exception as e:
    print(f'Error testing custom module: {e}')
" || log "Warning: Custom SM16relind module test failed"
    else
        log "⚠ No relay HAT detected on any I2C bus"
        log "   This may be normal if hardware is not connected yet"
    fi
else
    log "Warning: 16relind command not found - relay HAT control may not work"
fi

# Create a desktop shortcut with improved execution
log "=== Creating desktop shortcut ==="

# Determine the actual user (not root) for desktop shortcut
ACTUAL_USER="${SUDO_USER:-$USER}"
ACTUAL_HOME=$(getent passwd "$ACTUAL_USER" | cut -d: -f6)

# Create desktop directory for both root and actual user
mkdir -p ~/Desktop
if [ "$ACTUAL_USER" != "root" ] && [ -n "$ACTUAL_HOME" ]; then
    run_as_user mkdir -p "$ACTUAL_HOME/Desktop"
fi

# First create a launcher script for better error handling
run_as_user bash -c "cat > '$TARGET_DIR/launch_rrr.sh' << 'EOF'
#!/bin/bash
# RRR Application Launcher with error handling
cd \"\$(dirname \"\$0\")\""

# Log file
LAUNCH_LOG="$HOME/rrr_launch_$(date +%Y%m%d).log"
echo "=== RRR Launch $(date) ===" >> "$LAUNCH_LOG"

# Run the update script first
if [ -f "update_ui.sh" ]; then
    echo "Checking for UI updates..." | tee -a "$LAUNCH_LOG"
    ./update_ui.sh 2>&1 | tee -a "$LAUNCH_LOG"
    if [ $? -ne 0 ]; then
        echo "Warning: UI update check failed, but continuing..." | tee -a "$LAUNCH_LOG"
    fi
fi

# Configure I2C
if [ -f "configure_i2c.sh" ]; then
    echo "Configuring I2C buses..." | tee -a "$LAUNCH_LOG"
    ./configure_i2c.sh 2>&1 | tee -a "$LAUNCH_LOG"
    if [ $? -ne 0 ]; then
        echo "Warning: I2C configuration failed, but continuing..." | tee -a "$LAUNCH_LOG"
    fi
fi

# Activate virtual environment
echo "Activating virtual environment..." | tee -a "$LAUNCH_LOG"
source venv/bin/activate

# Launch the application
echo "Starting RRR application..." | tee -a "$LAUNCH_LOG"
cd Project
python3 main.py 2>&1 | tee -a "$LAUNCH_LOG"
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "ERROR: Application exited with code $EXIT_CODE" | tee -a "$LAUNCH_LOG"
    echo "Check the log file at $LAUNCH_LOG for details"
    # Keep terminal open for error inspection
    read -p "Press Enter to close this window..."
fi

exit \$EXIT_CODE
EOF
"

run_as_user chmod +x "$TARGET_DIR/launch_rrr.sh"

# Create the desktop shortcut using the launcher script
SHORTCUT_CONTENT="[Desktop Entry]
Type=Application
Name=Rodent Refreshment Regulator
Comment=Start the Rodent Refreshment Regulator application
Exec=bash -c \"cd $TARGET_DIR && ./launch_rrr.sh\"
Icon=applications-science
Terminal=true
Categories=Science;Lab;"

# Create shortcut for root user
echo "$SHORTCUT_CONTENT" > ~/Desktop/RRR.desktop
chmod +x ~/Desktop/RRR.desktop

# Create shortcut for actual user if different from root
if [ "$ACTUAL_USER" != "root" ] && [ -n "$ACTUAL_HOME" ]; then
    echo "$SHORTCUT_CONTENT" > "$ACTUAL_HOME/Desktop/RRR.desktop"
    chown "$ACTUAL_USER:$ACTUAL_USER" "$ACTUAL_HOME/Desktop/RRR.desktop"
    chmod +x "$ACTUAL_HOME/Desktop/RRR.desktop"
    log "Desktop shortcut created for user $ACTUAL_USER"
fi

# Create a startup script
log "=== Creating startup script ==="
run_as_user cat > "$TARGET_DIR/start_rrr.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"

# Auto-detect and configure I2C buses
if [ -f "configure_i2c.sh" ]; then
    echo "Configuring I2C buses..."
    ./configure_i2c.sh
fi

# Check for UI updates before starting
if [ -f "update_ui.sh" ]; then
    echo "Checking for UI updates..."
    ./update_ui.sh
fi

source venv/bin/activate
cd Project
python3 main.py
EOF

run_as_user chmod +x "$TARGET_DIR/start_rrr.sh"

# Copy the UI update script
log "=== Creating UI update script ==="
run_as_user cat > "$TARGET_DIR/update_ui.sh" << 'EOF'
#!/bin/bash

# Rodent Refreshment Regulator Update Script
# This script checks for updates and applies them automatically, then restarts the application
#
# Enhanced features:
# - Configurable installation path
# - Full application update (not just UI)
# - Robust error handling
# - Safe database and settings preservation
# - Automatic application restart
# - Detailed logging

# Enable basic error handling
set -e

# Log file for troubleshooting
UPDATE_LOG="$HOME/rrr_update_$(date +%Y%m%d).log"
echo "=== RRR Update $(date) ===" >> "$UPDATE_LOG"

# Configuration
RRR_DIR="${RRR_INSTALL_DIR:-$HOME/rodent-refreshment-regulator}"
LOG_FILE="$RRR_DIR/update_log.txt"
DEFAULT_BRANCH="main"

# Function for logging
log() {
    echo "$1" | tee -a "$UPDATE_LOG"
}

log "=== Starting RRR Update Process ==="

# Navigate to app directory - use environment variable if set, otherwise use default
if [ ! -d "$RRR_DIR" ]; then
    log "ERROR: Installation directory not found: $RRR_DIR"
    log "Please set RRR_INSTALL_DIR environment variable to your installation path"
    exit 1
fi
cd "$RRR_DIR" || { log "ERROR: Failed to change to installation directory"; exit 1; }

# Get current branch or use default
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "$DEFAULT_BRANCH")
log "Current branch: $BRANCH"

# Store current git hash
CURRENT_HASH=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
log "Current commit: $CURRENT_HASH"

# Attempt to update from repository
log "Fetching latest updates..."
git fetch origin "$BRANCH" || { log "ERROR: Failed to fetch updates"; exit 1; }

# Get remote hash
REMOTE_HASH=$(git rev-parse origin/$BRANCH 2>/dev/null || echo "unknown")
log "Latest remote commit: $REMOTE_HASH"

# Compare hashes to see if an update is available
if [ "$CURRENT_HASH" == "$REMOTE_HASH" ]; then
    log "Application is already up to date."
else
    log "Updates available. Backing up important files..."
    
    # Create timestamped backup directory for better tracking
    BACKUP_DIR="$RRR_DIR/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup database file if it exists
    if [ -f "Project/rrr_database.db" ]; then
        log "Backing up database..."
        cp -f "Project/rrr_database.db" "$BACKUP_DIR/rrr_database.db" || log "WARNING: Failed to backup database"
    fi

    # Backup settings if they exist
    if [ -f "Project/settings.json" ]; then
        log "Backing up settings..."
        cp -f "Project/settings.json" "$BACKUP_DIR/settings.json" || log "WARNING: Failed to backup settings"
    fi
    
    # Stash any local changes
    git stash || log "WARNING: Failed to stash changes, continuing anyway..."

    # Pull the latest updates for the entire application
    log "Applying application updates..."
    
    if ! git pull origin "$BRANCH"; then
        log "ERROR: Failed to pull updates. Attempting to resolve..."
        # Try harder to resolve conflicts by resetting to remote state
        if git reset --hard "origin/$BRANCH"; then
            log "Reset to remote state successful"
        else
            log "ERROR: Failed to reset to remote state. Update aborted."
            exit 1
        fi
    fi
    
    # Restore backed up files to preserve user data
    log "Restoring user data files..."
    
    if [ -f "$BACKUP_DIR/rrr_database.db" ]; then
        cp -f "$BACKUP_DIR/rrr_database.db" "Project/rrr_database.db" || log "WARNING: Failed to restore database"
    fi
    
    if [ -f "$BACKUP_DIR/settings.json" ]; then
        cp -f "$BACKUP_DIR/settings.json" "Project/settings.json" || log "WARNING: Failed to restore settings"
    fi
    
    log "Application updated successfully to commit $REMOTE_HASH!"

    # Disable sparse checkout
    git config core.sparseCheckout false
    
    # Get update details for notification
    UPDATE_DATE=$(date "+%Y-%m-%d %H:%M:%S")
    COMMIT_MSG=$(git log -1 --pretty=%B)
    
    # Create update notification for the app
    log "Creating update notification..."
    cat > Project/update_info.json << EOJ
{
    "updated": true,
    "date": "$UPDATE_DATE",
    "commit_message": "$(echo "$COMMIT_MSG" | head -n 1)",
    "previous_commit": "$CURRENT_HASH",
    "new_commit": "$REMOTE_HASH",
    "changes_summary": "The application has been updated to the latest version."
}
EOJ

    # Check if we need to restart the application
    if pgrep -f "python.*main.py" > /dev/null; then
        log "Restarting application..."
        
        # Different restart methods depending on platform
        if [ -f "/etc/systemd/system/rodent-regulator.service" ]; then
            # Systemd service method
            sudo systemctl restart rodent-regulator.service || log "WARNING: Failed to restart service"
        else
            # Direct process kill and restart
            pkill -f "python.*main.py" || log "WARNING: No running instance found to kill"
            
            # Wait for process to terminate
            sleep 2
            
            # Start application in background - ensure we use the virtual environment
            cd "$RRR_DIR"
            source venv/bin/activate
            nohup python3 "$RRR_DIR/Project/main.py" > "$RRR_DIR/app.log" 2>&1 &
            
            if [ $? -eq 0 ]; then
                log "Application restarted successfully"
            else
                log "WARNING: Failed to restart application"
            fi
        fi
    else
        log "No running instance detected. Application will use updates on next launch."
    fi
fi

log "Update process completed successfully."
exit 0
EOF

run_as_user chmod +x "$TARGET_DIR/update_ui.sh"

# Create a test script with proper quoting for heredoc
log "=== Creating hardware test script ==="
run_as_user cat > "$TARGET_DIR/test_hardware.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
cd Project

echo "Testing I2C devices..."
# Detect available I2C buses
AVAILABLE_BUSES=()
for i in $(seq 0 20); do
    if [ -e "/dev/i2c-$i" ]; then
        AVAILABLE_BUSES+=("$i")
        echo "Found I2C bus: /dev/i2c-$i"
    fi
done

if [ ${#AVAILABLE_BUSES[@]} -eq 0 ]; then
    echo "No I2C buses detected! Please check your I2C configuration."
else
    for bus in "${AVAILABLE_BUSES[@]}"; do
        echo "Testing I2C bus $bus:"
        sudo i2cdetect -y $bus
    done
fi

if [ -f "test_relay_connection.py" ]; then
    echo "Testing relay connection..."
    python3 test_relay_connection.py
else
    echo "Relay test script not found."
fi
EOF

run_as_user chmod +x "$TARGET_DIR/test_hardware.sh"

# Create a diagnostic script to help debug launch issues
log "=== Creating diagnostic script ==="
run_as_user cat > "$TARGET_DIR/diagnose.sh" << 'EOF'
#!/bin/bash
echo "=== RRR Diagnostic Script ==="
echo "Checking environment..."
cd "$(dirname "$0")"
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

run_as_user chmod +x "$TARGET_DIR/diagnose.sh"

# Add quick fix script for missing pandas
log "=== Creating quick fix script for missing packages ==="
run_as_user cat > "$TARGET_DIR/fix_dependencies.sh" << 'EOF'
#!/bin/bash
echo "=== RRR Dependency Fix Script ==="
cd "$(dirname "$0")"
source venv/bin/activate

echo "Installing pandas..."
sudo apt-get install -y python3-pandas
python3 -c "import pandas" || pip install pandas --break-system-packages

echo "Checking if pandas is now available..."
python3 -c "import pandas; print('pandas version:', pandas.__version__)" && echo "pandas installed successfully!"

echo "Installing Sequent Microsystems 16-relay HAT driver..."
if [ ! -d "/tmp/16relind-rpi" ]; then
    git clone https://github.com/SequentMicrosystems/16relind-rpi.git /tmp/16relind-rpi
fi
cd /tmp/16relind-rpi
git pull
sudo make install
cd - > /dev/null

# Install Python library if available
if [ -d "/tmp/16relind-rpi/python" ]; then
    echo "Installing Python library for SM16relind..."
    cd /tmp/16relind-rpi/python
    sudo python3 setup.py install
    # Create symlink to virtual environment
    PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    SM_PATH=$(find /usr/local/lib/python3*/dist-packages -name "SM16relind" -type d | head -n 1)
    if [ -n "$SM_PATH" ]; then
        mkdir -p venv/lib/python$PY_VERSION/site-packages/
        ln -sf $SM_PATH venv/lib/python$PY_VERSION/site-packages/
    fi
    cd - > /dev/null
fi

echo "Installing any other potential missing packages..."
pip install numpy matplotlib seaborn scipy scikit-learn statsmodels --break-system-packages

echo "All dependencies should now be installed. Try running the application again."
EOF

run_as_user chmod +x "$TARGET_DIR/fix_dependencies.sh"

# Create an I2C troubleshooting script
log "=== Creating I2C troubleshooting script ==="
run_as_user cat > "$TARGET_DIR/fix_i2c.sh" << 'EOF'
#!/bin/bash
echo "=== RRR I2C Troubleshooting Script ==="
echo "This script helps diagnose and fix I2C connection issues."

# Check if running with sudo
if [ "$(id -u)" -ne 0 ]; then
    echo "Some operations require sudo privileges."
    echo "Consider running this script with sudo if you encounter permission issues."
fi

# Function to detect I2C buses
detect_i2c_buses() {
    echo "Detecting I2C buses..."
    local found=false
    
    for i in $(seq 0 20); do
        if [ -e "/dev/i2c-$i" ]; then
            echo "Found I2C bus: /dev/i2c-$i"
            found=true
        fi
    done
    
    if [ "$found" = false ]; then
        echo "No I2C buses detected."
    fi
    
    return $([ "$found" = true ] && echo 0 || echo 1)
}

# Check if I2C interface is enabled in config.txt
check_config() {
    echo "Checking /boot/config.txt for I2C configuration..."
    
    if grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
        echo "✓ I2C is enabled in config.txt"
    else
        echo "✗ I2C is not enabled in config.txt"
        echo "  Adding I2C configuration..."
        echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt > /dev/null
        echo "  I2C has been enabled in config.txt. You need to reboot for this to take effect."
        need_reboot=true
    fi
}

# Check if I2C modules are loaded
check_modules() {
    echo "Checking if I2C kernel modules are loaded..."
    
    if lsmod | grep -q "i2c_"; then
        echo "✓ I2C modules are loaded"
    else
        echo "✗ I2C modules are not loaded"
        echo "  Loading I2C modules..."
        sudo modprobe i2c-dev
        sudo modprobe i2c-bcm2708 || echo "Module i2c-bcm2708 not available on this system"
        
        echo "  Ensuring modules load at boot..."
        if ! grep -q "i2c-dev" /etc/modules; then
            echo "i2c-dev" | sudo tee -a /etc/modules > /dev/null
        fi
    fi
}

# Run i2cdetect
run_i2cdetect() {
    echo "Running i2cdetect to scan for devices..."
    
    local found=false
    for i in $(seq 0 20); do
        if [ -e "/dev/i2c-$i" ]; then
            echo "Scanning bus $i:"
            sudo i2cdetect -y $i
            found=true
        fi
    done
    
    if [ "$found" = false ]; then
        echo "No buses to scan. Make sure I2C is enabled."
    fi
}

# Check user permissions
check_permissions() {
    echo "Checking user permissions for I2C access..."
    
    if groups | grep -q "i2c"; then
        echo "✓ User is in the i2c group"
    else
        echo "✗ User is not in the i2c group"
        echo "  Adding user to i2c group..."
        sudo usermod -a -G i2c $USER
        echo "  User added to i2c group. You may need to log out and back in for this to take effect."
    fi
}

# Run the fix_i2c.py script if available
run_fix_i2c_py() {
    echo "Checking for fix_i2c.py script..."
    
    if [ -f ~/rodent-refreshment-regulator/Project/fix_i2c.py ]; then
        echo "✓ Found fix_i2c.py script"
        echo "  Running the script..."
        
        cd ~/rodent-refreshment-regulator/Project
        chmod +x fix_i2c.py
        python3 fix_i2c.py
        
        cd - > /dev/null
    else
        echo "✗ fix_i2c.py script not found"
    fi
}

# Main execution
echo "Starting I2C diagnostics..."
need_reboot=false

# Run all checks
check_config
check_modules
check_permissions
detect_i2c_buses
run_i2cdetect
run_fix_i2c_py

# Provide a summary
echo ""
echo "===== I2C Troubleshooting Summary ====="
if detect_i2c_buses; then
    echo "✅ I2C buses detected. The system should be ready to use."
    echo "   If you're still having issues, try running the fix_i2c.py script:"
    echo "   cd \"\$(dirname \"\$0\")/Project\" && python3 fix_i2c.py"
else
    echo "❌ No I2C buses detected."
    
    if [ "$need_reboot" = true ]; then
        echo "   You need to reboot for the changes to take effect."
        echo "   Run 'sudo reboot' to restart the system."
    else
        echo "   Try the following steps:"
        echo "   1. Run 'sudo raspi-config' and enable I2C interface"
        echo "   2. Reboot the system"
        echo "   3. Run this script again"
    fi
fi
EOF

run_as_user chmod +x "$TARGET_DIR/fix_i2c.sh"

# Disable power management and screen blanking
log "=== Disabling Power Management ==="
log "Configuring system to prevent sleep during experiments..."

# Backup config.txt before modifications
if [ -f "/boot/config.txt" ]; then
    sudo cp /boot/config.txt /boot/config.txt.power_bak
    log "Backed up /boot/config.txt to /boot/config.txt.power_bak"
    
    # Add HDMI configurations to prevent display sleep
    if ! grep -v "^hdmi_blanking=0" /boot/config.txt; then
        echo "hdmi_blanking=0" | sudo tee -a /boot/config.txt > /dev/null
        log "Added hdmi_blanking=0 to /boot/config.txt"
    else
        log "hdmi_blanking=0 already set in config.txt"
    fi
fi

# Disable console blanking in cmdline.txt
if [ -f "/boot/cmdline.txt" ]; then
    sudo cp /boot/cmdline.txt /boot/cmdline.txt.power_bak
    log "Backed up /boot/cmdline.txt to /boot/cmdline.txt.power_bak"
    
    if ! grep -q "consoleblank=0" /boot/cmdline.txt; then
        # Append consoleblank=0 to the end of cmdline.txt, preserving its single-line structure
        sudo sed -i 's/$/ consoleblank=0/' /boot/cmdline.txt
        log "Added consoleblank=0 to kernel command line"
    else
        log "consoleblank=0 already set in cmdline.txt"
    fi
fi

# Create a service file to run RRR as a system service
log "=== Creating System Service ==="
log "Setting up RRR to run as a background service..."

# Use the actual username instead of hardcoding "pi"
CURRENT_USER="$USER"
HOME_DIR="$HOME"

sudo tee /etc/systemd/system/rodent-regulator.service > /dev/null << EOF
[Unit]
Description=Rodent Refreshment Regulator
After=network.target

[Service]
ExecStart=/bin/bash -c "cd ${HOME_DIR}/rodent-refreshment-regulator && ./start_rrr.sh"
WorkingDirectory=${HOME_DIR}/rodent-refreshment-regulator
Restart=always
User=${CURRENT_USER}
Environment=DISPLAY=:0

[Install]
WantedBy=multi-user.target
EOF

# Create a script to enable/disable service
run_as_user cat > "$TARGET_DIR/toggle_service.sh" << 'EOF'
#!/bin/bash
# Script to toggle between desktop mode and service mode for RRR

SERVICE_STATUS=$(systemctl is-active rodent-regulator.service)

if [ "$SERVICE_STATUS" = "active" ]; then
    echo "RRR is currently running as a service. Stopping service..."
    sudo systemctl stop rodent-regulator.service
    sudo systemctl disable rodent-regulator.service
    echo "Service stopped. You can now run RRR manually using the desktop icon or start_rrr.sh"
else
    echo "Setting up RRR to run as a system service..."
    sudo systemctl enable rodent-regulator.service
    sudo systemctl start rodent-regulator.service
    echo "Service started. RRR will now run automatically in the background."
    echo "It will continue to run even when display is disconnected or session is closed."
    echo "To switch back to manual mode, run this script again."
fi
EOF

run_as_user chmod +x "$TARGET_DIR/toggle_service.sh"

# Create installation verification script
log "=== Creating installation verification script ==="
run_as_user cat > "$TARGET_DIR/verify_installation.sh" << 'EOF'
#!/bin/bash
# RRR Installation Verification Script
# Quickly checks if the installation is working correctly

echo "🔍 RRR Installation Verification"
echo "================================"
echo ""

# Check if we're in the right directory
if [ ! -f "Project/main.py" ]; then
    echo "❌ Error: Not in RRR installation directory"
    echo "   Please run this from the RRR installation directory"
    exit 1
fi

echo "✅ Installation directory: $(pwd)"

# Check Python environment
echo "🐍 Checking Python environment..."
if [ -d "venv" ]; then
    echo "   ✅ Virtual environment found"
    
    if source venv/bin/activate 2>/dev/null; then
        echo "   ✅ Virtual environment activated"
        
        # Test critical imports
        python3 -c "
import sys
try:
    import PyQt5
    print('   ✅ PyQt5 available')
except ImportError:
    print('   ❌ PyQt5 not available')

try:
    import RPi.GPIO
    print('   ✅ RPi.GPIO available')
except ImportError:
    print('   ❌ RPi.GPIO not available')

try:
    import pandas
    print('   ✅ pandas available')
except ImportError:
    print('   ❌ pandas not available')
" 2>/dev/null
        
        deactivate
    else
        echo "   ❌ Cannot activate virtual environment"
    fi
else
    echo "   ❌ Virtual environment not found"
fi

# Check hardware components
echo ""
echo "🔧 Checking hardware components..."

# Check I2C
if command -v i2cdetect >/dev/null 2>&1; then
    echo "   ✅ I2C tools installed"
    
    # List available I2C buses
    buses=($(ls /dev/i2c-* 2>/dev/null | sed 's/.*i2c-//'))
    if [ ${#buses[@]} -gt 0 ]; then
        echo "   ✅ I2C buses available: ${buses[*]}"
    else
        echo "   ⚠️  No I2C buses detected (may need reboot)"
    fi
else
    echo "   ❌ I2C tools not installed"
fi

# Check relay HAT communication
echo "   🔌 Testing relay HAT communication..."
if command -v 16relind >/dev/null 2>&1; then
    echo "   ✅ 16relind command available"
    
    # Try to communicate with relay HAT
    if timeout 5 16relind -h >/dev/null 2>&1; then
        echo "   ✅ Relay HAT driver responding"
    else
        echo "   ⚠️  Relay HAT driver installed but may need hardware connection"
    fi
else
    echo "   ❌ 16relind command not found"
fi

echo ""
echo "📊 Summary:"
echo "==========="

# Overall assessment
critical_files=("Project/main.py" "Project/ui/gui.py" "Project/gpio/gpio_handler.py")
missing_files=0

for file in "${critical_files[@]}"; do
    if [ ! -f "$file" ]; then
        ((missing_files++))
    fi
done

if [ $missing_files -eq 0 ] && [ -d "venv" ]; then
    echo "🎉 Installation appears to be working correctly!"
    echo ""
    echo "Next steps:"
    echo "1. Reboot your system if you haven't already"
    echo "2. Run the application: ./start_rrr.sh"
    echo "3. Check the Help tab in the application for usage guides"
else
    echo "⚠️  Installation has some issues that may need attention"
    echo ""
    echo "Troubleshooting:"
    echo "1. Try running: ./fix_dependencies.sh"
    echo "2. For I2C issues: ./fix_i2c.sh"
    echo "3. For general diagnosis: ./diagnose.sh"
fi

echo ""
echo "For support, check the documentation or contact your system administrator."
EOF

run_as_user chmod +x "$TARGET_DIR/verify_installation.sh"

# Final installation verification
log "=== Final Installation Verification ==="
cd "$TARGET_DIR" || error_exit "Target directory not accessible"

# Check critical files
CRITICAL_FILES=("Project/main.py" "Project/ui/gui.py" "Project/gpio/gpio_handler.py")
for file in "${CRITICAL_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        log "WARNING: Critical file missing: $file"
    else
        log "✓ Verified: $file"
    fi
done

# Test Python environment
log "Testing Python environment..."
if source venv/bin/activate 2>/dev/null; then
    if python3 -c "import PyQt5; print('✓ PyQt5 available')" 2>/dev/null; then
        log "✓ Python environment verified"
    else
        log "WARNING: PyQt5 may not be properly installed"
    fi
    deactivate
else
    log "WARNING: Virtual environment activation failed"
fi

echo ""
echo "🎉 ===== INSTALLATION COMPLETE! ===== 🎉"
echo ""
echo "The Rodent Refreshment Regulator has been successfully installed!"
echo "Installation directory: $TARGET_DIR"
echo "Installed for user: $REAL_USER"
echo ""
echo "🚀 TO START THE APPLICATION:"
echo "   Option 1: Double-click the desktop shortcut 'RRR'"
echo "   Option 2: Run: $TARGET_DIR/start_rrr.sh"
echo "   Option 3: Manual start:"
echo "            cd $TARGET_DIR"
echo "            source venv/bin/activate"
echo "            cd Project && python3 main.py"
echo ""
echo "🛠️  TROUBLESHOOTING TOOLS (if needed):"
echo "   • Installation check: $TARGET_DIR/verify_installation.sh"
echo "   • Fix dependencies: $TARGET_DIR/fix_dependencies.sh"
echo "   • System diagnosis: $TARGET_DIR/diagnose.sh"
echo "   • Hardware test: $TARGET_DIR/test_hardware.sh"
echo "   • I2C issues: $TARGET_DIR/fix_i2c.sh"
echo ""
echo "⚙️  SYSTEM CONFIGURATION:"
echo "   • Service mode toggle: $TARGET_DIR/toggle_service.sh"
echo "   • Power management: DISABLED (prevents sleep during experiments)"
echo "   • I2C buses detected: ${AVAILABLE_BUSES[*]:-"Will be detected on reboot"}"
echo ""
echo "⚠️  IMPORTANT: A system reboot is recommended for I2C and power settings."
echo ""
read -p "Would you like to reboot now? (y/N): " -r reboot_choice
echo ""

if [[ $reboot_choice =~ ^[Yy]$ ]]; then
    echo "🔄 Rebooting system..."
    log "User chose to reboot - system restarting"
    sudo reboot
else
    echo "✅ Installation complete! Remember to reboot later."
    echo ""
    echo "📖 For detailed usage instructions, see:"
echo "   $TARGET_DIR/README.md"
    echo ""
    echo "🎯 Quick start: Run the application and check the Help tab for guides."
    log "Installation completed successfully - user chose not to reboot"
fi 
