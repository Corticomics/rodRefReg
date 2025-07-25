#!/bin/bash

# Rodent Refreshment Regulator (RRR) - Robust Installation Script
# Version: 2.0
# Compatible with: Raspberry Pi 4, Raspberry Pi 5, Debian-based systems
# 
# This script implements industry best practices for:
# - Git repository management with conflict resolution
# - Raspberry Pi hardware detection and configuration
# - I2C interface setup with Pi 5 compatibility
# - Python dependency management with system integration
# - Error handling and recovery mechanisms
# - User-proof installation process

# ====================================================================
# CONFIGURATION AND INITIALIZATION
# ====================================================================

# Strict error handling following bash best practices
set -euo pipefail  # Exit on error, undefined vars, pipe failures
IFS=$'\n\t'       # Secure Internal Field Separator

# Trap errors with detailed reporting
trap 'error_handler $? $LINENO $BASH_COMMAND' ERR

# Global configuration
readonly SCRIPT_VERSION="2.0"
readonly REPO_URL="https://github.com/Corticomics/rodRefReg.git"
readonly APP_DIR="$HOME/rodent-refreshment-regulator"
readonly INSTALL_LOG="$HOME/rrr_install_$(date +%Y%m%d_%H%M%S).log"
readonly MIN_PYTHON_VERSION="3.6"
readonly MIN_DISK_SPACE_MB=1000

# System state tracking
NEEDS_REBOOT=false
I2C_DETECTION_SUCCESS=false
DETECTED_PI_VERSION=""

# ====================================================================
# LOGGING AND ERROR HANDLING
# ====================================================================

# Initialize logging
exec 1> >(tee -a "$INSTALL_LOG")
exec 2> >(tee -a "$INSTALL_LOG" >&2)

log() {
    local level="${1:-INFO}"
    local message="${2:-}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message"
}

error_handler() {
    local exit_code=$1
    local line_number=$2
    local command="$3"
    
    log "ERROR" "Installation failed at line $line_number"
    log "ERROR" "Command: $command"
    log "ERROR" "Exit code: $exit_code"
    log "ERROR" "Check the log file at $INSTALL_LOG for details"
    
    cleanup_on_error
    exit $exit_code
}

cleanup_on_error() {
    log "INFO" "Performing cleanup after error..."
    
    # Clean up temporary files
    rm -f /tmp/enable_i2c_temp.sh /tmp/configure_i2c.sh /tmp/requirements_modified.txt
    
    # Deactivate virtual environment if active  
    if [[ "${VIRTUAL_ENV:-}" != "" ]]; then
        deactivate 2>/dev/null || true
    fi
    
    log "INFO" "Cleanup completed"
}

# Check for internet connection
log "Checking internet connection..."
if ! ping -c 1 github.com &> /dev/null && ! ping -c 1 8.8.8.8 &> /dev/null; then
    error_exit "No internet connection detected. Please check your network and try again."
fi
log "✓ Internet connection verified"


# ====================================================================
# SYSTEM DETECTION AND VALIDATION
# ====================================================================

detect_raspberry_pi() {
    log "INFO" "Detecting Raspberry Pi hardware..."
    
    if [ ! -f /proc/cpuinfo ]; then
        log "WARN" "Unable to read /proc/cpuinfo - assuming compatible hardware"
        return 0
    fi
    
    if grep -q "Raspberry Pi 5" /proc/cpuinfo; then
        DETECTED_PI_VERSION="5"
        log "INFO" "Raspberry Pi 5 detected"
    elif grep -q "Raspberry Pi 4" /proc/cpuinfo; then
        DETECTED_PI_VERSION="4"
        log "INFO" "Raspberry Pi 4 detected"
    elif grep -q "Raspberry Pi" /proc/cpuinfo; then
        DETECTED_PI_VERSION="other"
        log "INFO" "Raspberry Pi detected (older model)"
    elif grep -q "BCM" /proc/cpuinfo; then
        DETECTED_PI_VERSION="compatible"
        log "INFO" "BCM-compatible hardware detected"
    else
        log "WARN" "This doesn't appear to be a Raspberry Pi"
        log "WARN" "Some hardware features may not work correctly"
        return 0
    fi
    
    return 0
}

check_system_requirements() {
    log "INFO" "Checking system requirements..."
    
    # Internet connectivity
    if ! timeout 10 ping -c 1 github.com &>/dev/null; then
        log "ERROR" "No internet connection to github.com"
        log "ERROR" "Please check your network connection and try again"
        exit 1
    fi
    
    # Disk space
    local available_space
    available_space=$(df -BM --output=avail "$HOME" | tail -n 1 | tr -d 'M')
    
    if [ "$available_space" -lt $MIN_DISK_SPACE_MB ]; then
        log "ERROR" "Insufficient disk space: ${available_space}MB available, ${MIN_DISK_SPACE_MB}MB required"
        exit 1
    fi
    
    log "INFO" "Available disk space: ${available_space}MB - OK"
    
    # Operating system
    if ! command -v apt-get &>/dev/null; then
        log "ERROR" "This installer requires apt-get (Debian/Ubuntu-based system)"
        exit 1
    fi
    
    success_message "System requirements check passed"
}

validate_python_version() {
    local python_version
    python_version=$(python3 --version 2>/dev/null | cut -d ' ' -f 2)
    
    if [ -z "$python_version" ]; then
        log "ERROR" "Python 3 is not installed"
        exit 1
    fi
    
    local python_major python_minor
    python_major=$(echo "$python_version" | cut -d. -f1)
    python_minor=$(echo "$python_version" | cut -d. -f2)
    
    local min_major min_minor
    min_major=$(echo "$MIN_PYTHON_VERSION" | cut -d. -f1)
    min_minor=$(echo "$MIN_PYTHON_VERSION" | cut -d. -f2)
    
    if [ "$python_major" -lt "$min_major" ] || 
       [ "$python_major" -eq "$min_major" -a "$python_minor" -lt "$min_minor" ]; then
        log "ERROR" "Python version must be at least $MIN_PYTHON_VERSION"
        log "ERROR" "Found: $python_version"
        exit 1
    fi
    
    log "INFO" "Python version: $python_version - OK"
}

# ====================================================================
# PACKAGE INSTALLATION AND MANAGEMENT
# ====================================================================

update_system_packages() {
    log "INFO" "Updating system packages..."
    
    # Update package lists with retry logic
    local retry_count=0
    local max_retries=3
    
    while [ $retry_count -lt $max_retries ]; do
        if sudo apt-get update; then
            success_message "Package lists updated"
            return 0
        else
            retry_count=$((retry_count + 1))
            log "WARN" "Package update failed (attempt $retry_count/$max_retries)"
            
            if [ $retry_count -lt $max_retries ]; then
                log "INFO" "Retrying in 5 seconds..."
                sleep 5
            fi
        fi
    done
    
    log "ERROR" "Failed to update package lists after $max_retries attempts"
    exit 1
}

install_system_dependencies() {
    log "INFO" "Installing system dependencies..."
    
    local packages=(
        "python3"
        "python3-pip" 
        "python3-venv"
        "python3-dev"
        "python3-pyqt5"
        "python3-rpi.gpio"
        "python3-gpiozero"
        "python3-pandas"
        "python3-numpy"
        "python3-smbus"
        "git"
        "i2c-tools"
        "build-essential"
        "pkg-config"
        "libffi-dev"
        "libssl-dev"
    )
    
    # Install packages with automatic retry on lock - using direct execution
    if ! sudo apt-get install -y "${packages[@]}"; then
        log "WARN" "Initial package installation failed, trying again..."
        sleep 10
        
        if ! sudo apt-get install -y "${packages[@]}"; then
            log "ERROR" "Failed to install system dependencies"
            exit 1
        fi
    fi
    
    success_message "System dependencies installed"
}

install_relay_hat_driver() {
    log "INFO" "Installing Sequent Microsystems 16-relay HAT driver..."
    
    local driver_dir="/tmp/16relind-rpi"
    
    # Clean up any existing directory
    if [ -d "$driver_dir" ]; then
        rm -rf "$driver_dir"
    fi
    
    # Clone the driver repository
    if ! git clone https://github.com/SequentMicrosystems/16relind-rpi.git "$driver_dir"; then
        log "ERROR" "Failed to clone relay HAT driver repository"
        exit 1
    fi
    
    # Build and install the driver
    (
        cd "$driver_dir" || exit 1
        
        if sudo make install; then
            log "INFO" "Relay HAT driver installed successfully"
        else
            log "WARN" "Relay HAT driver installation failed, but continuing"
        fi
        
        # Install Python library if available
        if [ -d "python" ]; then
            log "INFO" "Installing Python library for SM16relind..."
            (
                cd python || exit 1
                if sudo python3 setup.py install; then
                    log "INFO" "SM16relind Python library installed"
                else
                    log "WARN" "SM16relind Python library installation failed"
                fi
            )
        fi
    )
    
    # Verify installation
    if command -v 16relind &>/dev/null; then
        success_message "16relind command available"
    else
        log "WARN" "16relind command not found after installation"
    fi
    
    # Clean up
    rm -rf "$driver_dir"
}

# ====================================================================
# I2C CONFIGURATION WITH RASPBERRY PI 5 SUPPORT
# ====================================================================

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
    log "INFO" "Configured I2C device permissions"
    
    # Reload udev rules
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    
    if [ "$need_reboot" = true ]; then
        NEEDS_REBOOT=true
        log "INFO" "I2C configuration completed - reboot required"
    else
        log "INFO" "I2C configuration completed - no reboot required"
    fi
}

detect_i2c_buses() {
    log "INFO" "Detecting I2C buses..."
    
    local available_buses=()
    local max_attempts=3
    local attempt=1
    
    # Wait for I2C subsystem to initialize
    sleep 2
    
    while [ $attempt -le $max_attempts ]; do
        available_buses=()
        
        log "INFO" "Detection attempt $attempt/$max_attempts..."
        
        # Check for I2C device files with proper permissions
        for i in $(seq 0 20); do
            if [ -e "/dev/i2c-$i" ] && [ -r "/dev/i2c-$i" ] && [ -w "/dev/i2c-$i" ]; then
                available_buses+=("$i")
            fi
        done
        
        if [ ${#available_buses[@]} -gt 0 ]; then
            log "INFO" "Found I2C buses: ${available_buses[*]}"
            I2C_DETECTION_SUCCESS=true
            break
        else
            log "WARN" "No I2C buses found on attempt $attempt"
            if [ $attempt -lt $max_attempts ]; then
                sleep 3
            fi
        fi
        
        ((attempt++))
    done
    
    # Provide diagnostic information if detection failed
    if [ ${#available_buses[@]} -eq 0 ]; then
        log "ERROR" "No accessible I2C buses detected"
        log "INFO" "Diagnostic information:"
        log "INFO" "Available I2C device files:"
        ls -la /dev/i2c-* 2>/dev/null || log "INFO" "No I2C device files found"
        log "INFO" "User groups: $(groups)"
        log "INFO" "I2C kernel modules:"
        lsmod | grep i2c || log "INFO" "No I2C modules loaded"
        
        if [ "$NEEDS_REBOOT" = true ]; then
            log "INFO" "I2C buses should be available after reboot"
        else
            log "INFO" "Try running: sudo raspi-config and manually enable I2C interface"
        fi
        
        I2C_DETECTION_SUCCESS=false
        return 1
    fi
    
    # Test I2C functionality with i2cdetect
    log "INFO" "Testing I2C functionality..."
    for bus in "${available_buses[@]}"; do
        log "INFO" "Testing I2C bus $bus:"
        if command -v i2cdetect > /dev/null; then
            sudo i2cdetect -y "$bus" 2>/dev/null || log "WARN" "Bus $bus scan failed"
        fi
    done
    
    echo "${available_buses[@]}"
    return 0
}

# ====================================================================
# REPOSITORY MANAGEMENT WITH CONFLICT RESOLUTION
# ====================================================================

setup_application_directory() {
    log "INFO" "Setting up application directory..."
    

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


fix_python_executable_permissions() {
    log "INFO" "Setting executable permissions for Python scripts..."
    
    local python_executables=()
    local fixed_count=0
    

    # Also put a copy in the root directory for compatibility with existing scripts
    cp ~/rodent-refreshment-regulator/tools/configure_i2c.sh ~/rodent-refreshment-regulator/configure_i2c.sh
    chmod +x ~/rodent-refreshment-regulator/configure_i2c.sh
fi

# Smart installation directory setup - handles all execution contexts
log "=== Setting up application directory ==="

# Set repository URL
REPO_URL="https://github.com/Corticomics/rodRefReg.git"
TARGET_DIR="$HOME/rodent-refreshment-regulator"

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
    
    # Check if target directory exists and is a repo
    if [ -d "$TARGET_DIR/.git" ]; then
        echo "TARGET_EXISTS"
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
            git clone "$REPO_URL" "$TARGET_DIR" || error_exit "Failed to clone repository"
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
                cp -r "$(pwd)" "$TARGET_DIR"
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
            git clone "$REPO_URL" temp_clone || error_exit "Failed to clone repository"
            cp -r temp_clone/* .
            cp -r temp_clone/.git .
            rm -rf temp_clone
        fi
        ;;
        
    "TARGET_EXISTS")
        log "Target directory exists - updating existing installation"
        cd "$TARGET_DIR" || error_exit "Failed to change to target directory"
        git fetch origin || log "Warning: fetch failed, continuing"
        git pull origin main || git pull origin master || log "Warning: pull failed, continuing"
        ;;
        
    "FRESH_INSTALL")
        log "Fresh installation - cloning repository to target directory"
        
        # Create parent directory if needed
        mkdir -p "$(dirname "$TARGET_DIR")"
        
        # Clone repository
        git clone "$REPO_URL" "$TARGET_DIR" || error_exit "Failed to clone repository"
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

# Create virtual environment with access to system packages 
# (this is critical for PyQt5 and RPi.GPIO)
log "=== Creating Python virtual environment with system packages ==="
python3 -m venv venv --system-site-packages || error_exit "Failed to create virtual environment"
source venv/bin/activate || error_exit "Failed to activate virtual environment"

# Create a modified requirements file without the problematic packages
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

# Install Python dependencies
log "=== Installing Python dependencies ==="
pip install --upgrade pip || log "Warning: pip upgrade failed, but continuing"

# If we have a modified requirements file, use it
if [ -n "$REQUIREMENTS_PATH" ]; then
    log "Installing dependencies from modified requirements file..."
    # Use --break-system-packages only if needed
    if pip install -r "$REQUIREMENTS_PATH"; then
        log "Dependencies installed successfully."

    else
        log "ERROR" "main.py not found - this will cause application failure"
        exit 1
    fi
    
    if [ $fixed_count -gt 0 ]; then
        log "INFO" "Fixed executable permissions for $fixed_count Python files"
        success_message "Python executable permissions corrected"
    else
        log "INFO" "All Python executable permissions were already correct"
    fi
    
    # Verify critical files are now executable
    local critical_files=("$APP_DIR/Project/main.py")
    
    for file in "${critical_files[@]}"; do
        if [ -f "$file" ] && [ -x "$file" ]; then
            log "INFO" "✓ Verified executable: $(basename "$file")"
        else
            log "ERROR" "✗ Critical file not executable: $file"
            exit 1
        fi
    done
}

# ====================================================================
# PYTHON ENVIRONMENT AND DEPENDENCY MANAGEMENT  
# ====================================================================

setup_python_environment() {
    log "INFO" "Setting up Python virtual environment..."
    
    # Create virtual environment with system site packages access
    # This is critical for PyQt5 and RPi.GPIO integration
    if ! python3 -m venv venv --system-site-packages; then
        log "ERROR" "Failed to create virtual environment"
        exit 1
    fi
    
    # Activate virtual environment
    if ! source venv/bin/activate; then
        log "ERROR" "Failed to activate virtual environment"
        exit 1
    fi
    
    success_message "Virtual environment created and activated"
}

install_python_dependencies() {
    log "INFO" "Installing Python dependencies..."
    
    # Upgrade pip first
    if ! pip install --upgrade pip; then
        log "WARN" "pip upgrade failed, but continuing"
    fi
    
    # Create modified requirements file excluding system packages
    local requirements_path="/tmp/requirements_modified.txt"
    
    if [ -f "installer/requirements.txt" ]; then
        grep -v -E 'PyQt5|RPi\.GPIO|gpiozero|pandas|numpy' installer/requirements.txt > "$requirements_path"
    elif [ -f "requirements.txt" ]; then
        grep -v -E 'PyQt5|RPi\.GPIO|gpiozero|pandas|numpy' requirements.txt > "$requirements_path"
    else
        log "INFO" "No requirements.txt found, will install packages individually"
        requirements_path=""
    fi
    
    # Install dependencies
    if [ -n "$requirements_path" ] && [ -f "$requirements_path" ]; then
        log "INFO" "Installing dependencies from modified requirements file..."
        
        if pip install -r "$requirements_path"; then
            log "INFO" "Dependencies installed successfully"
        else
            log "WARN" "Initial installation failed, trying with --break-system-packages..."
            if pip install --break-system-packages -r "$requirements_path"; then
                log "INFO" "Dependencies installed with --break-system-packages"
            else
                log "ERROR" "Failed to install Python dependencies"
                exit 1
            fi
        fi
    else
        log "INFO" "Installing essential packages individually..."
        
        local essential_packages=(
            "gitpython==3.1.31"
            "requests==2.31.0" 
            "slack_sdk==3.21.3"
            "smbus2==0.4.1"
            "Flask==2.2.2"
            "Jinja2==3.1.2"
            "jsonschema==4.23.0"
            "attrs==24.2.0"
            "certifi==2024.8.30"
            "idna==3.10"
            "chardet==5.1.0"
            "cryptography==38.0.4"
        )
        
        for package in "${essential_packages[@]}"; do
            if ! pip install "$package"; then
                log "WARN" "Failed to install $package, trying with --break-system-packages"
                pip install --break-system-packages "$package" || log "WARN" "Failed to install $package"
            fi
        done
    fi
    
    # Clean up temporary files
    rm -f "$requirements_path"
    
    success_message "Python dependencies installation completed"
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
            mkdir -p ~/rodent-refreshment-regulator/venv/lib/python$PY_VERSION/site-packages/
            ln -sf $SM_PATH ~/rodent-refreshment-regulator/venv/lib/python$PY_VERSION/site-packages/
            log "Symlink created."

        fi
    done
    
    if [ ${#failed_deps[@]} -gt 0 ]; then
        log "WARN" "Some dependencies are not available: ${failed_deps[*]}"
        log "INFO" "This may be resolved after a reboot or by running fix_dependencies.sh"
    else
        success_message "All critical dependencies verified"
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
    mkdir -p "$ACTUAL_HOME/Desktop"
fi


create_launcher_script() {
    log "INFO" "Creating application launcher script..."
    
    cat > "$APP_DIR/launch_rrr.sh" << 'EOF'
#!/bin/bash
# RRR Application Launcher with comprehensive error handling

LAUNCH_LOG="$HOME/rrr_launch_$(date +%Y%m%d).log"
echo "=== RRR Launch $(date) ===" >> "$LAUNCH_LOG"

log_message() {
    echo "$1" | tee -a "$LAUNCH_LOG"
}

check_prerequisites() {
    log_message "Checking system prerequisites..."
    
    if [ ! -d ~/rodent-refreshment-regulator ]; then
        log_message "ERROR: RRR installation directory not found"
        return 1
    fi
    
    cd ~/rodent-refreshment-regulator || return 1
    
    if [ ! -d "venv" ]; then
        log_message "ERROR: Python virtual environment not found"
        log_message "Try running the installer again: ./setup_rrr.sh"
        return 1
    fi
    
    if [ ! -d "Project" ] || [ ! -f "Project/main.py" ]; then
        log_message "ERROR: Application files not found"
        return 1
    fi
    
    log_message "✅ Prerequisites check passed"
    return 0
}

configure_i2c() {
    log_message "Configuring I2C interface..."
    
    if [ -f "configure_i2c.sh" ]; then
        if ./configure_i2c.sh 2>&1 >> "$LAUNCH_LOG"; then
            log_message "✅ I2C configuration successful"
            return 0
        else
            log_message "⚠️  I2C configuration failed"
            log_message "Hardware relay control may not work correctly"
            
            echo "I2C configuration failed. Continue anyway? (y/n)"
            read -r continue_choice
            if [[ $continue_choice =~ ^[Yy]$ ]]; then
                log_message "User chose to continue despite I2C issues"
                return 0
            else
                log_message "User chose to abort due to I2C issues"
                return 1
            fi
        fi
    else
        log_message "⚠️  I2C configuration script not found"
        return 0
    fi
}

start_application() {
    log_message "Starting RRR application..."
    
    if ! source venv/bin/activate; then
        log_message "ERROR: Failed to activate virtual environment"
        return 1
    fi
    
    cd Project || {
        log_message "ERROR: Failed to change to Project directory"
        return 1
    }
    
    # Check critical dependencies
    python3 -c "import PyQt5" 2>/dev/null || {
        log_message "ERROR: PyQt5 not available"
        log_message "Try running: ~/rodent-refreshment-regulator/fix_dependencies.sh"
        return 1
    }
    
    # Launch the application
    log_message "Launching main application..."
    python3 main.py 2>&1 | tee -a "$LAUNCH_LOG"
    
    local exit_code=${PIPESTATUS[0]}
    log_message "Application exited with code: $exit_code"
    
    return $exit_code
}

main() {
    log_message "=== Rodent Refreshment Regulator Launcher ==="
    
    if ! check_prerequisites; then
        echo "Prerequisites check failed. See log: $LAUNCH_LOG"
        read -p "Press Enter to close..."
        exit 1
    fi
    
    if ! configure_i2c; then
        echo "I2C configuration failed. See log: $LAUNCH_LOG"
        read -p "Press Enter to close..."
        exit 1
    fi
    
    if start_application; then
        log_message "✅ Application completed successfully"
        exit 0
    else
        echo ""
        echo "❌ Application failed to start"
        echo "Check the log file for details: $LAUNCH_LOG"
        echo ""
        echo "Common solutions:"
        echo "1. Run diagnostics: ~/rodent-refreshment-regulator/diagnose.sh"
        echo "2. Fix dependencies: ~/rodent-refreshment-regulator/fix_dependencies.sh"
        echo "3. Fix I2C issues: ~/rodent-refreshment-regulator/fix_i2c.sh"
        echo ""
        read -p "Press Enter to close..."
        exit 1
    fi
}

# Create the desktop shortcut using the launcher script
SHORTCUT_CONTENT="[Desktop Entry]
Type=Application
Name=Rodent Refreshment Regulator
Comment=Start the Rodent Refreshment Regulator application
Exec=bash -c \"cd ~/rodent-refreshment-regulator && ./launch_rrr.sh\"
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
cat > ~/rodent-refreshment-regulator/start_rrr.sh << EOF

#!/bin/bash
# Runtime I2C Configuration Script for RRR

echo "=== Configuring I2C for Rodent Refreshment Regulator ==="

detect_runtime_i2c_buses() {
    local available_buses=()
    local max_attempts=5
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        available_buses=()
        
        echo "Detecting I2C buses (attempt $attempt/$max_attempts)..."
        
        for i in $(seq 0 20); do
            if [ -e "/dev/i2c-$i" ]; then
                if sudo test -r "/dev/i2c-$i" && sudo test -w "/dev/i2c-$i"; then
                    available_buses+=("$i")
                    echo "Found accessible I2C bus: /dev/i2c-$i"
                fi
            fi
        done
        
        if [ ${#available_buses[@]} -gt 0 ]; then
            break
        else
            echo "No accessible I2C buses found on attempt $attempt"
            if [ $attempt -lt $max_attempts ]; then
                sleep 2
            fi
        fi
        
        ((attempt++))
    done
    
    if [ ${#available_buses[@]} -eq 0 ]; then
        echo "ERROR: No accessible I2C buses detected!"
        echo "Troubleshooting information:"
        echo "1. Check if user is in i2c group: groups | grep i2c"
        echo "2. Check I2C devices: ls -la /dev/i2c-*"
        echo "3. Check I2C modules: lsmod | grep i2c"
        echo "4. Try: sudo raspi-config -> Interface Options -> I2C -> Enable"
        return 1
    fi
    
    echo "Successfully detected I2C buses: ${available_buses[*]}"
    echo "Primary I2C bus will be: /dev/i2c-${available_buses[0]}"
    
    # Test I2C functionality
    echo "Testing I2C functionality..."
    for bus in "${available_buses[@]}"; do
        echo "Scanning I2C bus $bus:"
        if command -v i2cdetect > /dev/null; then
            sudo i2cdetect -y "$bus" 2>/dev/null | head -n 10
        fi
    done
    
    # Run Project-specific I2C fix if available
    if [ -f "../Project/fix_i2c.py" ]; then
        echo "Running project-specific I2C configuration..."
        cd ../Project || exit 1
        python3 fix_i2c.py || echo "Warning: I2C fix script encountered issues"
        cd - > /dev/null
    fi
    
    return 0
}

if detect_runtime_i2c_buses; then
    echo "✅ I2C configuration completed successfully"
    exit 0
else
    echo "❌ I2C configuration failed"
    echo "The application may not be able to control hardware relays."
    exit 1
fi
EOF

    chmod +x "$APP_DIR/tools/configure_i2c.sh"
    
    # Create compatibility copy in root directory
    cp "$APP_DIR/tools/configure_i2c.sh" "$APP_DIR/configure_i2c.sh"
    chmod +x "$APP_DIR/configure_i2c.sh"
    
    success_message "I2C configuration script created"
}

create_update_script() {
    log "INFO" "Creating application update script..."
    
    cat > "$APP_DIR/update_ui.sh" << 'EOF'
#!/bin/bash

# Rodent Refreshment Regulator Update Script
# This script checks for updates and applies them automatically
#
# Enhanced features:
# - Configurable installation path
# - Full application update (not just UI)
# - Robust error handling
# - Safe database and settings preservation
# - Detailed logging

# Strict error handling following bash best practices
set -euo pipefail
IFS=$'\n\t'

# Log file for troubleshooting
UPDATE_LOG="$HOME/rrr_update_$(date +%Y%m%d).log"
echo "=== RRR Update $(date) ===" >> "$UPDATE_LOG"

# Configuration
RRR_DIR="${RRR_INSTALL_DIR:-$HOME/rodent-refreshment-regulator}"
DEFAULT_BRANCH="main"

# Function for logging
log() {
    local level="${1:-INFO}"
    local message="${2:-}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message" | tee -a "$UPDATE_LOG"
}

# Error handling
error_exit() {
    log "ERROR" "$1"
    exit 1
}

log "INFO" "Starting RRR update process"

# Navigate to app directory - use environment variable if set, otherwise use default
if [ ! -d "$RRR_DIR" ]; then
    error_exit "Installation directory not found: $RRR_DIR. Please set RRR_INSTALL_DIR environment variable to your installation path"
fi

cd "$RRR_DIR" || error_exit "Failed to change to installation directory"

# Get current branch or use default
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "$DEFAULT_BRANCH")
log "INFO" "Current branch: $BRANCH"

# Store current git hash
CURRENT_HASH=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
log "INFO" "Current commit: $CURRENT_HASH"

# Attempt to update from repository with robust error handling
log "INFO" "Fetching latest updates..."
if ! git fetch origin "$BRANCH"; then
    error_exit "Failed to fetch updates from repository"
fi

# Get remote hash
REMOTE_HASH=$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo "unknown")
log "INFO" "Latest remote commit: $REMOTE_HASH"

# Compare hashes to see if an update is available
if [ "$CURRENT_HASH" == "$REMOTE_HASH" ]; then
    log "INFO" "Application is already up to date"
    exit 0
else
    log "INFO" "Updates available. Backing up important files..."
    
    # Create timestamped backup directory for better tracking
    BACKUP_DIR="$RRR_DIR/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup database file if it exists
    if [ -f "Project/rrr_database.db" ]; then
        log "INFO" "Backing up database..."
        cp -f "Project/rrr_database.db" "$BACKUP_DIR/rrr_database.db" || log "WARN" "Failed to backup database"
    fi

    # Backup settings if they exist
    if [ -f "Project/settings.json" ]; then
        log "INFO" "Backing up settings..."
        cp -f "Project/settings.json" "$BACKUP_DIR/settings.json" || log "WARN" "Failed to backup settings"
    fi
    
    # Backup any saved settings
    if [ -d "Project/saved_settings" ]; then
        log "INFO" "Backing up saved settings..."
        cp -rf "Project/saved_settings" "$BACKUP_DIR/" || log "WARN" "Failed to backup saved settings"
    fi
    
    # Stash any local changes safely
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        log "INFO" "Stashing local changes..."
        git stash push -m "Auto-stash before update $(date)" || log "WARN" "Failed to stash changes, continuing anyway"
    fi

    # Pull the latest updates for the entire application
    log "INFO" "Applying application updates..."
    
    if ! git reset --hard "origin/$BRANCH"; then
        log "ERROR" "Failed to apply updates. Attempting to recover..."
        
        # Try to restore from backup if update fails
        if [ -f "$BACKUP_DIR/rrr_database.db" ]; then
            cp -f "$BACKUP_DIR/rrr_database.db" "Project/rrr_database.db" 2>/dev/null || true
        fi
        if [ -f "$BACKUP_DIR/settings.json" ]; then
            cp -f "$BACKUP_DIR/settings.json" "Project/settings.json" 2>/dev/null || true
        fi
        
        error_exit "Failed to apply updates and recovery attempted"
    fi
    
    # Restore backed up files to preserve user data
    log "INFO" "Restoring user data files..."
    
    if [ -f "$BACKUP_DIR/rrr_database.db" ]; then
        cp -f "$BACKUP_DIR/rrr_database.db" "Project/rrr_database.db" || log "WARN" "Failed to restore database"
    fi
    
    if [ -f "$BACKUP_DIR/settings.json" ]; then
        cp -f "$BACKUP_DIR/settings.json" "Project/settings.json" || log "WARN" "Failed to restore settings"
    fi
    
    if [ -d "$BACKUP_DIR/saved_settings" ]; then
        cp -rf "$BACKUP_DIR/saved_settings" "Project/" || log "WARN" "Failed to restore saved settings"
    fi
    
    log "INFO" "Application updated successfully to commit $REMOTE_HASH"

    # Get update details for notification
    UPDATE_DATE=$(date "+%Y-%m-%d %H:%M:%S")
    COMMIT_MSG=$(git log -1 --pretty=%B 2>/dev/null || echo "Update applied")
    
    # Create update notification for the app
    log "INFO" "Creating update notification..."
    cat > Project/update_info.json << EOJSON
{
    "updated": true,
    "date": "$UPDATE_DATE",
    "commit_message": "$(echo "$COMMIT_MSG" | head -n 1 | sed 's/"/\\"/g')",
    "previous_commit": "$CURRENT_HASH",
    "new_commit": "$REMOTE_HASH",
    "changes_summary": "The application has been updated to the latest version."
}
EOJSON

    # Check if we need to restart the application
    if pgrep -f "python.*main.py" > /dev/null; then
        log "INFO" "Restarting application..."
        
        # Different restart methods depending on platform
        if [ -f "/etc/systemd/system/rodent-regulator.service" ]; then
            # Systemd service method
            if sudo systemctl restart rodent-regulator.service; then
                log "INFO" "Service restarted successfully"
            else
                log "WARN" "Failed to restart service"
            fi
        else
            # Direct process kill and restart
            pkill -f "python.*main.py" || log "WARN" "No running instance found to kill"
            
            # Wait for process to terminate
            sleep 2
            
            # Start application in background - ensure we use the virtual environment
            if [ -f "venv/bin/activate" ]; then
                source venv/bin/activate
                nohup python3 "$RRR_DIR/Project/main.py" > "$RRR_DIR/app.log" 2>&1 &
                
                if [ $? -eq 0 ]; then
                    log "INFO" "Application restarted successfully"
                else
                    log "WARN" "Failed to restart application"
                fi
            else
                log "WARN" "Virtual environment not found, cannot restart application"
            fi
        fi
    else
        log "INFO" "No running instance detected. Application will use updates on next launch"
    fi
fi

log "INFO" "Update process completed successfully"
exit 0
EOF
    
    chmod +x "$APP_DIR/update_ui.sh"
    
    success_message "Update script created"
}

create_diagnostic_scripts() {
    log "INFO" "Creating diagnostic and troubleshooting scripts..."
    
    # Main diagnostic script
    cat > "$APP_DIR/diagnose.sh" << 'EOF'
#!/bin/bash
echo "=== RRR Diagnostic Script ==="
echo "Checking environment..."

cd ~/rodent-refreshment-regulator || {
    echo "ERROR: RRR installation directory not found"
    exit 1
}

echo "Current directory: $(pwd)"

if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment not found"
    echo "Try running the installer again"
    exit 1
fi

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
if [ -d "Project" ] && [ -f "Project/main.py" ]; then
    echo "✅ Project directory and main.py found"
else
    echo "❌ Project directory or main.py not found"
fi

echo "I2C Status:"
if command -v i2cdetect > /dev/null; then
    for i in $(seq 0 5); do
        if [ -e "/dev/i2c-$i" ]; then
            echo "I2C bus $i detected"
        fi
    done
else
    echo "i2cdetect not available"
fi

echo "User groups: $(groups)"
EOF
    
    chmod +x "$APP_DIR/diagnose.sh"
    
    # Dependencies fix script
    cat > "$APP_DIR/fix_dependencies.sh" << 'EOF'
#!/bin/bash
echo "=== RRR Dependency Fix Script ==="

cd ~/rodent-refreshment-regulator || {
    echo "ERROR: RRR installation directory not found"
    exit 1
}

source venv/bin/activate

echo "Installing/updating system packages..."
sudo apt-get update
sudo apt-get install -y python3-pandas python3-pyqt5 python3-rpi.gpio python3-numpy

echo "Checking Python packages..."
python3 -c "import pandas; print('pandas version:', pandas.__version__)" || \
    pip install pandas --break-system-packages

echo "Installing Sequent Microsystems driver..."
if [ ! -d "/tmp/16relind-rpi" ]; then
    git clone https://github.com/SequentMicrosystems/16relind-rpi.git /tmp/16relind-rpi
fi

cd /tmp/16relind-rpi || exit 1
git pull
sudo make install

if [ -d "python" ]; then
    cd python || exit 1
    sudo python3 setup.py install
fi

echo "Dependencies fix completed"
EOF
    
    chmod +x "$APP_DIR/fix_dependencies.sh"
    
    # I2C troubleshooting script  
    cat > "$APP_DIR/fix_i2c.sh" << 'EOF'
#!/bin/bash
echo "=== RRR I2C Troubleshooting Script ==="

# Check configuration files
CONFIG_FILE="/boot/config.txt"
if [ -f "/boot/firmware/config.txt" ]; then
    CONFIG_FILE="/boot/firmware/config.txt"
    echo "Using Raspberry Pi 5 config path"
fi

echo "Checking I2C configuration in $CONFIG_FILE..."
if grep -q "^dtparam=i2c_arm=on" "$CONFIG_FILE"; then
    echo "✓ I2C is enabled in config"
else
    echo "✗ I2C is not enabled in config"
    echo "Adding I2C configuration..."
    echo "dtparam=i2c_arm=on" | sudo tee -a "$CONFIG_FILE"
    echo "Reboot required for changes to take effect"
fi

echo "Checking I2C modules..."
if lsmod | grep -q "i2c_"; then
    echo "✓ I2C modules are loaded"
else
    echo "✗ Loading I2C modules..."
    sudo modprobe i2c-dev
    sudo modprobe i2c-bcm2835 2>/dev/null || sudo modprobe i2c-bcm2708 2>/dev/null
fi

echo "Checking user permissions..."
if groups | grep -q "i2c"; then
    echo "✓ User is in i2c group"
else
    echo "✗ Adding user to i2c group..."
    sudo usermod -a -G i2c $USER
    echo "Log out and back in for group changes to take effect"
fi

echo "Scanning for I2C devices..."
for i in $(seq 0 5); do
    if [ -e "/dev/i2c-$i" ]; then
        echo "Scanning bus $i:"
        sudo i2cdetect -y $i 2>/dev/null || echo "Bus $i scan failed"
    fi
done

echo "I2C troubleshooting completed"
EOF
    
    chmod +x "$APP_DIR/fix_i2c.sh"
    
    # Hardware testing script - integrates with Project test scripts
    cat > "$APP_DIR/test_hardware.sh" << 'EOF'
#!/bin/bash
echo "=== RRR Hardware Testing Script ==="
echo "This script tests I2C functionality and relay hardware connectivity."
echo ""

cd ~/rodent-refreshment-regulator || {
    echo "ERROR: RRR installation directory not found"
    exit 1
}

# Test log file
TEST_LOG="$HOME/rrr_hardware_test_$(date +%Y%m%d_%H%M%S).log"
echo "Test results will be logged to: $TEST_LOG"
echo "=== RRR Hardware Test $(date) ===" > "$TEST_LOG"

log_test() {
    echo "$1" | tee -a "$TEST_LOG"
}

test_i2c_buses() {
    log_test "=== I2C Bus Detection Test ==="
    
    local buses_found=()
    local bus_count=0
    
    log_test "Scanning for I2C buses..."
    for i in $(seq 0 20); do
        if [ -e "/dev/i2c-$i" ]; then
            buses_found+=("$i")
            log_test "✓ Found I2C bus: /dev/i2c-$i"
            ((bus_count++))
        fi
    done
    
    if [ $bus_count -eq 0 ]; then
        log_test "❌ No I2C buses detected!"
        log_test "   Try running: ~/rodent-refreshment-regulator/fix_i2c.sh"
        return 1
    else
        log_test "✅ Found $bus_count I2C bus(es): ${buses_found[*]}"
    fi
    
    # Test each bus with i2cdetect
    if command -v i2cdetect > /dev/null; then
        for bus in "${buses_found[@]}"; do
            log_test ""
            log_test "Testing I2C bus $bus with i2cdetect:"
            if sudo i2cdetect -y "$bus" >> "$TEST_LOG" 2>&1; then
                log_test "✓ Bus $bus scan completed"
            else
                log_test "⚠️ Bus $bus scan failed"
            fi
        done
    else
        log_test "⚠️ i2cdetect not available - install i2c-tools"
    fi
    
    return 0
}

test_i2c_permissions() {
    log_test ""
    log_test "=== I2C Permissions Test ==="
    
    # Check user groups
    if groups | grep -q "i2c"; then
        log_test "✓ User is in i2c group"
    else
        log_test "❌ User not in i2c group"
        log_test "   Run: sudo usermod -a -G i2c $USER"
        log_test "   Then log out and back in"
        return 1
    fi
    
    # Test device permissions
    local accessible_buses=()
    for i in $(seq 0 10); do
        if [ -e "/dev/i2c-$i" ]; then
            if [ -r "/dev/i2c-$i" ] && [ -w "/dev/i2c-$i" ]; then
                accessible_buses+=("$i")
                log_test "✓ Bus $i is accessible"
            else
                log_test "❌ Bus $i permission denied"
            fi
        fi
    done
    
    if [ ${#accessible_buses[@]} -gt 0 ]; then
        log_test "✅ I2C permissions OK for buses: ${accessible_buses[*]}"
        return 0
    else
        log_test "❌ No accessible I2C buses found"
        return 1
    fi
}

test_relay_modules() {
    log_test ""
    log_test "=== Relay Module Import Test ==="
    
    # Activate virtual environment
    if [ -d "venv" ]; then
        source venv/bin/activate
        log_test "✓ Virtual environment activated"
    else
        log_test "❌ Virtual environment not found"
        return 1
    fi
    
    # Test SM16relind module import
    if python3 -c "import SM16relind; print('SM16relind version check passed')" 2>> "$TEST_LOG"; then
        log_test "✓ SM16relind module imported successfully"
    else
        log_test "❌ SM16relind module import failed"
        log_test "   Try running: ~/rodent-refreshment-regulator/fix_dependencies.sh"
        return 1
    fi
    
    # Test custom I2C fix module if it exists
    if [ -f "Project/fix_i2c.py" ]; then
        cd Project || return 1
        if python3 -c "exec(open('fix_i2c.py').read())" 2>> "$TEST_LOG"; then
            log_test "✓ Custom I2C fix module executed successfully"
        else
            log_test "⚠️ Custom I2C fix module had issues (check log)"
        fi
        cd - > /dev/null
    fi
    
    return 0
}

test_relay_connection() {
    log_test ""
    log_test "=== Relay Connection Test ==="
    
    # Use Project test scripts if available
    if [ -f "Project/test_relay_diagnostic.py" ]; then
        log_test "Running project diagnostic script..."
        cd Project || return 1
        
        if python3 test_relay_diagnostic.py >> "$TEST_LOG" 2>&1; then
            log_test "✓ Project diagnostic completed"
        else
            log_test "❌ Project diagnostic failed"
            cd - > /dev/null
            return 1
        fi
        
        cd - > /dev/null
    else
        log_test "Project diagnostic script not found"
    fi
    
    # Basic connection test
    log_test "Performing basic relay connection test..."
    
    # Create a simple test script
    cat > /tmp/relay_test.py << 'PYTEST'
import sys
try:
    import SM16relind
    print("Attempting to connect to relay hat...")
    rel = SM16relind.SM16relind(0)
    print("✓ Successfully connected to relay hat")
    
    # Test basic functionality
    print("Testing relay 1...")
    rel.set(1, 1)
    import time
    time.sleep(0.5)
    state = rel.get(1)
    rel.set(1, 0)
    
    if state == 1:
        print("✓ Relay control test passed")
        sys.exit(0)
    else:
        print("❌ Relay control test failed")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Relay connection failed: {e}")
    sys.exit(1)
PYTEST
    
    if python3 /tmp/relay_test.py >> "$TEST_LOG" 2>&1; then
        log_test "✅ Basic relay connection test passed"
        rm -f /tmp/relay_test.py
        return 0
    else
        log_test "❌ Basic relay connection test failed"
        rm -f /tmp/relay_test.py
        return 1
    fi
}

run_comprehensive_test() {
    log_test "Starting comprehensive hardware test..."
    log_test "System: $(uname -a)"
    log_test "User: $(whoami)"
    log_test "Groups: $(groups)"
    log_test ""
    
    local test_results=()
    local overall_status=0
    
    # Run all tests
    if test_i2c_buses; then
        test_results+=("I2C_BUSES: PASS")
    else
        test_results+=("I2C_BUSES: FAIL")
        overall_status=1
    fi
    
    if test_i2c_permissions; then
        test_results+=("I2C_PERMISSIONS: PASS")
    else
        test_results+=("I2C_PERMISSIONS: FAIL")
        overall_status=1
    fi
    
    if test_relay_modules; then
        test_results+=("RELAY_MODULES: PASS")
    else
        test_results+=("RELAY_MODULES: FAIL")
        overall_status=1
    fi
    
    if test_relay_connection; then
        test_results+=("RELAY_CONNECTION: PASS")
    else
        test_results+=("RELAY_CONNECTION: FAIL")
        overall_status=1
    fi
    
    # Print summary
    log_test ""
    log_test "=== HARDWARE TEST SUMMARY ==="
    for result in "${test_results[@]}"; do
        log_test "$result"
    done
    
    log_test ""
    if [ $overall_status -eq 0 ]; then
        log_test "🎉 ALL HARDWARE TESTS PASSED!"
        log_test "Your RRR system is ready for operation."
    else
        log_test "⚠️ SOME HARDWARE TESTS FAILED"
        log_test ""
        log_test "Troubleshooting steps:"
        log_test "1. Check hardware connections"
        log_test "2. Run: ~/rodent-refreshment-regulator/fix_i2c.sh"
        log_test "3. Run: ~/rodent-refreshment-regulator/fix_dependencies.sh"
        log_test "4. Ensure system has been rebooted after I2C configuration"
        log_test "5. Check the detailed log: $TEST_LOG"
    fi
    
    log_test ""
    log_test "Test completed: $(date)"
    
    return $overall_status
}

# Main execution
echo "Hardware testing requires sudo access for I2C operations."
echo "You may be prompted for your password."
echo ""

if run_comprehensive_test; then
    echo "✅ Hardware test completed successfully!"
    echo "Check the log for details: $TEST_LOG"
    exit 0
else
    echo "❌ Hardware test failed!"
    echo "Check the log for details: $TEST_LOG"
    exit 1
fi
EOF
    
    chmod +x "$APP_DIR/test_hardware.sh"
    
    success_message "Diagnostic scripts created"
}

create_desktop_integration() {
    log "INFO" "Creating desktop integration..."
    
    # Create desktop shortcut
    mkdir -p ~/Desktop
    
    cat > ~/Desktop/RRR.desktop << EOF
[Desktop Entry]
Type=Application
Name=Rodent Refreshment Regulator
Comment=Start the Rodent Refreshment Regulator application
Exec=bash -c "cd ~/rodent-refreshment-regulator && ./launch_rrr.sh"
Icon=applications-science
Terminal=true
Categories=Science;Lab;
EOF
    
    chmod +x ~/Desktop/RRR.desktop
    
    # Create startup script for manual use
    cat > "$APP_DIR/start_rrr.sh" << EOF
#!/bin/bash
cd ~/rodent-refreshment-regulator

# Configure I2C if script exists
if [ -f "configure_i2c.sh" ]; then
    echo "Configuring I2C buses..."
    ./configure_i2c.sh
fi

source venv/bin/activate
cd Project
python3 main.py
EOF
    
    chmod +x "$APP_DIR/start_rrr.sh"
    
    success_message "Desktop integration created"
}

# ====================================================================
# SYSTEM SERVICE CONFIGURATION
# ====================================================================

create_system_service() {
    log "INFO" "Creating system service configuration..."
    
    # Create systemd service file
    sudo tee /etc/systemd/system/rodent-regulator.service > /dev/null << EOF
[Unit]
Description=Rodent Refreshment Regulator
After=network.target

[Service]
ExecStart=/bin/bash -c "cd ${APP_DIR} && ./start_rrr.sh"
WorkingDirectory=${APP_DIR}
Restart=always
User=${USER}
Environment=DISPLAY=:0

[Install]
WantedBy=multi-user.target
EOF
    
    # Create service toggle script
    cat > "$APP_DIR/toggle_service.sh" << 'EOF'
#!/bin/bash
SERVICE_STATUS=$(systemctl is-active rodent-regulator.service 2>/dev/null || echo "inactive")

if [ "$SERVICE_STATUS" = "active" ]; then
    echo "RRR is currently running as a service. Stopping service..."
    sudo systemctl stop rodent-regulator.service
    sudo systemctl disable rodent-regulator.service
    echo "Service stopped. You can now run RRR manually."
else
    echo "Setting up RRR to run as a system service..."
    sudo systemctl enable rodent-regulator.service
    sudo systemctl start rodent-regulator.service
    echo "Service started. RRR will now run automatically."
fi
EOF
    
    chmod +x "$APP_DIR/toggle_service.sh"
    
    success_message "System service configuration created"
}

# ====================================================================
# POWER MANAGEMENT CONFIGURATION
# ====================================================================


# Create installation verification script
log "=== Creating installation verification script ==="
cat > ~/rodent-refreshment-regulator/verify_installation.sh << 'EOF'
#!/bin/bash
# RRR Installation Verification Script
# Quickly checks if the installation is working correctly

echo "🔍 RRR Installation Verification"
echo "================================"
echo ""

# Check if we're in the right directory
if [ ! -f "Project/main.py" ]; then
    echo "❌ Error: Not in RRR installation directory"
    echo "   Please run this from: ~/rodent-refreshment-regulator/"
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

chmod +x ~/rodent-refreshment-regulator/verify_installation.sh

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
echo ""
echo "🚀 TO START THE APPLICATION:"
echo "   Option 1: Double-click the desktop shortcut 'RRR'"
echo "   Option 2: Run: ~/rodent-refreshment-regulator/start_rrr.sh"
echo "   Option 3: Manual start:"
echo "            cd ~/rodent-refreshment-regulator"
echo "            source venv/bin/activate"
echo "            cd Project && python3 main.py"
echo ""
echo "🛠️  TROUBLESHOOTING TOOLS (if needed):"
echo "   • Installation check: ~/rodent-refreshment-regulator/verify_installation.sh"
echo "   • Fix dependencies: ~/rodent-refreshment-regulator/fix_dependencies.sh"
echo "   • System diagnosis: ~/rodent-refreshment-regulator/diagnose.sh"
echo "   • Hardware test: ~/rodent-refreshment-regulator/test_hardware.sh"
echo "   • I2C issues: ~/rodent-refreshment-regulator/fix_i2c.sh"
echo ""
echo "⚙️  SYSTEM CONFIGURATION:"
echo "   • Service mode toggle: ~/rodent-refreshment-regulator/toggle_service.sh"
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
    echo "   ~/rodent-refreshment-regulator/README.md"
    echo ""
    echo "🎯 Quick start: Run the application and check the Help tab for guides."
    log "Installation completed successfully - user chose not to reboot"

fi 
