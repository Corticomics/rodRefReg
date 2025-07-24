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

success_message() {
    log "SUCCESS" "$1"
}

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

configure_i2c_interface() {
    log "INFO" "Configuring I2C interface..."
    
    local config_file="/boot/config.txt"
    local firmware_config="/boot/firmware/config.txt"
    local need_reboot=false
    
    # Raspberry Pi 5 uses different config path
    if [ -f "$firmware_config" ]; then
        config_file="$firmware_config"
        log "INFO" "Using Raspberry Pi 5 firmware config path"
    fi
    
    if [ ! -f "$config_file" ]; then
        log "ERROR" "Configuration file not found: $config_file"
        exit 1
    fi
    
    # Backup configuration file
    sudo cp "$config_file" "${config_file}.bak.$(date +%Y%m%d_%H%M%S)"
    log "INFO" "Configuration file backed up"
    
    # Enable I2C in boot configuration
    if ! grep -q "^dtparam=i2c_arm=on" "$config_file"; then
        log "INFO" "Enabling I2C in boot configuration..."
        echo "dtparam=i2c_arm=on" | sudo tee -a "$config_file" > /dev/null
        need_reboot=true
    fi
    
    # Set I2C baudrate for reliability (especially important for Pi 5)
    if ! grep -q "dtparam=i2c_arm_baudrate" "$config_file"; then
        log "INFO" "Setting I2C baudrate for optimal performance..."
        echo "dtparam=i2c_arm_baudrate=100000" | sudo tee -a "$config_file" > /dev/null
    fi
    
    # Load I2C kernel modules immediately
    log "INFO" "Loading I2C kernel modules..."
    sudo modprobe i2c-dev 2>/dev/null || log "WARN" "i2c-dev module already loaded or not available"
    
    # Load appropriate module based on Pi version
    case "$DETECTED_PI_VERSION" in
        "5")
            sudo modprobe i2c-bcm2835 2>/dev/null || log "WARN" "i2c-bcm2835 module not available"
            ;;
        *)
            sudo modprobe i2c-bcm2708 2>/dev/null || log "WARN" "i2c-bcm2708 module not available"
            ;;
    esac
    
    # Ensure modules load at boot
    local modules_file="/etc/modules"
    if ! grep -q "^i2c-dev" "$modules_file"; then
        echo "i2c-dev" | sudo tee -a "$modules_file" > /dev/null
        log "INFO" "Added i2c-dev to boot modules"
    fi
    
    # Create and configure I2C group
    if ! getent group i2c > /dev/null; then
        sudo groupadd i2c
        log "INFO" "Created i2c group"
    fi
    
    # Add current user to i2c group
    sudo usermod -a -G i2c "$USER"
    log "INFO" "Added user to i2c group"
    
    # Set proper permissions for I2C devices
    sudo tee /etc/udev/rules.d/99-i2c.rules > /dev/null << 'EOF'
SUBSYSTEM=="i2c-dev", GROUP="i2c", MODE="0664"
KERNEL=="i2c-[0-9]*", GROUP="i2c", MODE="0664"
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
    
    mkdir -p "$APP_DIR"
    cd "$APP_DIR" || {
        log "ERROR" "Failed to change to application directory"
        exit 1
    }
    
    log "INFO" "Application directory: $APP_DIR"
}

setup_repository() {
    log "INFO" "Setting up git repository..."
    
    local repo_url="$1"
    local target_dir="$(pwd)"
    
    if [ -d ".git" ]; then
        log "INFO" "Existing repository detected - updating..."
        
        # Verify and update remote URL
        local current_remote
        current_remote=$(git remote get-url origin 2>/dev/null || echo "")
        
        if [ "$current_remote" != "$repo_url" ]; then
            log "WARN" "Remote URL mismatch - updating"
            log "INFO" "Expected: $repo_url"
            log "INFO" "Found: $current_remote"
            git remote set-url origin "$repo_url"
        fi
        
        # Fetch latest changes
        if ! git fetch origin main; then
            log "ERROR" "Failed to fetch from repository"
            exit 1
        fi
        
        # Handle local changes safely
        if ! git diff-index --quiet HEAD -- 2>/dev/null; then
            log "INFO" "Detected local changes - stashing..."
            git stash push -m "Auto-stash before update $(date)"
        fi
        
        # Update to latest version
        if ! git reset --hard origin/main; then
            log "ERROR" "Failed to update repository"
            exit 1
        fi
        
        success_message "Repository updated successfully"
        
        fix_python_executable_permissions
    else
        # Handle directory that may contain files but isn't a git repo
        if [ "$(ls -A "$target_dir" 2>/dev/null | wc -l)" -gt 0 ]; then
            log "INFO" "Directory contains files but is not a git repository"
            
            # Create timestamped backup
            local backup_dir="${target_dir}/backup_$(date +%Y%m%d_%H%M%S)"
            log "INFO" "Creating backup at: $backup_dir"
            mkdir -p "$backup_dir"
            
            # Move all files to backup (excluding . and .. and the backup dir itself)
            find "$target_dir" -maxdepth 1 -not -path "$target_dir" -not -path "$backup_dir" \
                -exec mv {} "$backup_dir/" \; 2>/dev/null || true
            
            log "INFO" "Existing files backed up successfully"
        fi
        
        # Clone repository with proper error handling
        log "INFO" "Cloning repository..."
        log "INFO" "Repository URL: $repo_url"
        
        if ! git clone "$repo_url" "$target_dir"; then
            log "ERROR" "Failed to clone repository from $repo_url"
            
            # Provide helpful debugging information
            log "INFO" "Troubleshooting information:"
            log "INFO" "- Check internet connectivity: ping -c 1 github.com"
            log "INFO" "- Verify repository URL: $repo_url"
            log "INFO" "- Check available disk space: df -h $target_dir"
            
            exit 1
        fi
        
        success_message "Repository cloned successfully"
    fi
    
    # Fix Python executable permissions for both new and updated repositories
    fix_python_executable_permissions
}

fix_python_executable_permissions() {
    log "INFO" "Setting executable permissions for Python scripts..."
    
    local python_executables=()
    local fixed_count=0
    
    # Find all Python files with shebang lines that should be executable
    while IFS= read -r -d '' file; do
        if [ -f "$file" ] && head -n 1 "$file" 2>/dev/null | grep -q "^#!.*python"; then
            python_executables+=("$file")
            
            # Check if file is already executable
            if [ ! -x "$file" ]; then
                log "INFO" "Setting executable permission: $file"
                chmod +x "$file" || log "WARN" "Failed to set executable permission: $file"
                ((fixed_count++))
            else
                log "INFO" "Already executable: $file"
            fi
        fi
    done < <(find "$APP_DIR/Project" -name "*.py" -type f -print0 2>/dev/null)
    
    # Specifically ensure main.py is executable (critical for application startup)
    if [ -f "$APP_DIR/Project/main.py" ]; then
        if [ ! -x "$APP_DIR/Project/main.py" ]; then
            log "INFO" "Ensuring main.py is executable (critical for application startup)"
            chmod +x "$APP_DIR/Project/main.py" || {
                log "ERROR" "Failed to make main.py executable - installation will fail"
                exit 1
            }
            ((fixed_count++))
        fi
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

verify_python_dependencies() {
    log "INFO" "Verifying Python dependencies..."
    
    # Critical dependencies verification
    local dependencies=(
        "PyQt5:PyQt5.QtCore"
        "RPi.GPIO:RPi.GPIO"
        "pandas:pandas"
        "slack_sdk:slack_sdk"
        "numpy:numpy"
    )
    
    local failed_deps=()
    
    for dep in "${dependencies[@]}"; do
        local package_name="${dep%%:*}"
        local import_name="${dep##*:}"
        
        if python3 -c "import $import_name" 2>/dev/null; then
            log "INFO" "✓ $package_name available"
        else
            log "WARN" "✗ $package_name not available"
            failed_deps+=("$package_name")
        fi
    done
    
    if [ ${#failed_deps[@]} -gt 0 ]; then
        log "WARN" "Some dependencies are not available: ${failed_deps[*]}"
        log "INFO" "This may be resolved after a reboot or by running fix_dependencies.sh"
    else
        success_message "All critical dependencies verified"
    fi
}

# ====================================================================
# APPLICATION SCRIPTS AND INTEGRATION
# ====================================================================

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

main "$@"
EOF

    chmod +x "$APP_DIR/launch_rrr.sh"
    success_message "Application launcher created"
}

create_i2c_configuration_script() {
    log "INFO" "Creating runtime I2C configuration script..."
    
    mkdir -p "$APP_DIR/tools"
    
    cat > "$APP_DIR/tools/configure_i2c.sh" << 'EOF'
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

configure_power_management() {
    log "INFO" "Configuring power management..."
    
    local config_file="/boot/config.txt"
    
    # Use Pi 5 config path if available
    if [ -f "/boot/firmware/config.txt" ]; then
        config_file="/boot/firmware/config.txt"
    fi
    
    # Backup config file
    if [ -f "$config_file" ]; then
        sudo cp "$config_file" "${config_file}.power_bak"
        log "INFO" "Config file backed up"
        
        # Prevent HDMI blanking
        if ! grep -q "^hdmi_blanking=0" "$config_file"; then
            echo "hdmi_blanking=0" | sudo tee -a "$config_file" > /dev/null
            log "INFO" "HDMI blanking disabled"
        fi
    fi
    
    # Disable console blanking
    if [ -f "/boot/cmdline.txt" ]; then
        sudo cp /boot/cmdline.txt /boot/cmdline.txt.power_bak
        
        if ! grep -q "consoleblank=0" /boot/cmdline.txt; then
            sudo sed -i 's/$/ consoleblank=0/' /boot/cmdline.txt
            log "INFO" "Console blanking disabled"
        fi
    fi
    
    success_message "Power management configured"
}

# ====================================================================
# INSTALLATION VALIDATION AND VERIFICATION
# ====================================================================

validate_installation() {
    log "INFO" "Validating installation integrity..."
    
    local validation_errors=()
    local validation_warnings=()
    
    # Check directory structure
    log "INFO" "Checking directory structure..."
    
    local required_dirs=(
        "$APP_DIR"
        "$APP_DIR/Project"
        "$APP_DIR/venv"
        "$APP_DIR/tools"
    )
    
    for dir in "${required_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            validation_errors+=("Missing directory: $dir")
        else
            log "INFO" "✓ Directory exists: $dir"
        fi
    done
    
    # Check essential files
    log "INFO" "Checking essential files..."
    
    local required_files=(
        "$APP_DIR/Project/main.py"
        "$APP_DIR/venv/bin/activate"
        "$APP_DIR/launch_rrr.sh"
        "$APP_DIR/start_rrr.sh"
        "$APP_DIR/diagnose.sh"
        "$APP_DIR/fix_dependencies.sh"
        "$APP_DIR/fix_i2c.sh"
        "$APP_DIR/test_hardware.sh"
        "$APP_DIR/update_ui.sh"
        "$APP_DIR/toggle_service.sh"
        "$APP_DIR/tools/configure_i2c.sh"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            validation_errors+=("Missing file: $file")
        elif [ ! -x "$file" ]; then
            validation_errors+=("File not executable: $file")
        else
            log "INFO" "✓ File exists and executable: $(basename "$file")"
        fi
    done
    
    # Additional check for critical Python files with shebang lines
    local critical_python_files=(
        "$APP_DIR/Project/main.py"
        "$APP_DIR/Project/fix_i2c.py"
    )
    
    for file in "${critical_python_files[@]}"; do
        if [ -f "$file" ]; then
            # Check if file has shebang and is executable
            if head -n 1 "$file" 2>/dev/null | grep -q "^#!.*python"; then
                if [ -x "$file" ]; then
                    log "INFO" "✓ Python executable ready: $(basename "$file")"
                else
                    validation_errors+=("Python script with shebang not executable: $file")
                fi
            fi
        fi
    done
    
    # Check Python environment
    log "INFO" "Checking Python environment..."
    
    if [ -f "$APP_DIR/venv/bin/activate" ]; then
        (
            cd "$APP_DIR" || exit 1
            source venv/bin/activate
            
            # Test critical Python imports
            local python_modules=(
                "PyQt5"
                "pandas"
                "requests"
                "slack_sdk"
            )
            
            for module in "${python_modules[@]}"; do
                if python3 -c "import $module" 2>/dev/null; then
                    log "INFO" "✓ Python module available: $module"
                else
                    validation_warnings+=("Python module not available: $module")
                fi
            done
            
            # Test hardware-specific modules (these may fail on non-Pi systems)
            if python3 -c "import RPi.GPIO" 2>/dev/null; then
                log "INFO" "✓ RPi.GPIO available"
            else
                validation_warnings+=("RPi.GPIO not available (expected on non-Pi systems)")
            fi
            
            if python3 -c "import SM16relind" 2>/dev/null; then
                log "INFO" "✓ SM16relind module available"
            else
                validation_warnings+=("SM16relind module not available (may need hardware)")
            fi
        )
    else
        validation_errors+=("Virtual environment activation script not found")
    fi
    
    # Check system configuration
    log "INFO" "Checking system configuration..."
    
    # Check I2C configuration
    local config_file="/boot/config.txt"
    if [ -f "/boot/firmware/config.txt" ]; then
        config_file="/boot/firmware/config.txt"
    fi
    
    if [ -f "$config_file" ]; then
        if grep -q "^dtparam=i2c_arm=on" "$config_file"; then
            log "INFO" "✓ I2C enabled in boot configuration"
        else
            validation_warnings+=("I2C not enabled in boot configuration")
        fi
    else
        validation_warnings+=("Boot configuration file not found")
    fi
    
    # Check user groups
    if groups | grep -q "i2c"; then
        log "INFO" "✓ User is in i2c group"
    else
        validation_warnings+=("User not in i2c group - hardware control may not work")
    fi
    
    # Check system service
    if [ -f "/etc/systemd/system/rodent-regulator.service" ]; then
        log "INFO" "✓ System service file created"
    else
        validation_warnings+=("System service file not created")
    fi
    
    # Check desktop integration
    if [ -f ~/Desktop/RRR.desktop ]; then
        log "INFO" "✓ Desktop shortcut created"
    else
        validation_warnings+=("Desktop shortcut not created")
    fi
    
    # Report validation results
    log "INFO" "=== Installation Validation Results ==="
    
    if [ ${#validation_errors[@]} -eq 0 ]; then
        if [ ${#validation_warnings[@]} -eq 0 ]; then
            log "INFO" "🎉 Installation validation passed with no issues!"
            success_message "All components validated successfully"
            return 0
        else
            log "WARN" "Installation validation passed with warnings:"
            for warning in "${validation_warnings[@]}"; do
                log "WARN" "  ⚠️  $warning"
            done
            log "INFO" "✅ Installation is functional despite warnings"
            return 0
        fi
    else
        log "ERROR" "Installation validation failed with errors:"
        for error in "${validation_errors[@]}"; do
            log "ERROR" "  ❌ $error"
        done
        
        if [ ${#validation_warnings[@]} -gt 0 ]; then
            log "WARN" "Additional warnings:"
            for warning in "${validation_warnings[@]}"; do
                log "WARN" "  ⚠️  $warning"
            done
        fi
        
        log "ERROR" "Installation may not function correctly"
        return 1
    fi
}

# ====================================================================
# INSTALLATION RECOVERY AND CLEANUP
# ====================================================================

setup_cleanup_handler() {
    log "INFO" "Setting up cleanup handlers..."
    
    # Create cleanup function
    cleanup_on_failure() {
        local exit_code=$?
        log "WARN" "Installation interrupted or failed with code $exit_code"
        
        # Perform minimal cleanup to leave system in a recoverable state
        log "INFO" "Performing cleanup..."
        
        # Deactivate virtual environment if active
        if [[ "${VIRTUAL_ENV:-}" != "" ]]; then
            deactivate 2>/dev/null || true
        fi
        
        # Clean up temporary files
        rm -f /tmp/enable_i2c_temp.sh /tmp/configure_i2c.sh /tmp/requirements_modified.txt /tmp/relay_test.py 2>/dev/null || true
        
        # Don't remove the installation directory to allow recovery
        if [ -d "$APP_DIR" ] && [ -f "$APP_DIR/.installation_incomplete" ]; then
            log "INFO" "Partial installation preserved at: $APP_DIR"
            log "INFO" "You can run the installer again to retry"
        fi
        
        log "INFO" "Cleanup completed"
        exit $exit_code
    }
    
    # Set up trap for cleanup
    trap cleanup_on_failure EXIT
    
    # Mark installation as incomplete
    touch "$APP_DIR/.installation_incomplete" 2>/dev/null || true
}

finalize_installation() {
    log "INFO" "Finalizing installation..."
    
    # Remove incomplete marker
    rm -f "$APP_DIR/.installation_incomplete" 2>/dev/null || true
    
    # Create installation info file
    cat > "$APP_DIR/.installation_info" << EOF
# RRR Installation Information
INSTALL_DATE=$(date '+%Y-%m-%d %H:%M:%S')
INSTALLER_VERSION=$SCRIPT_VERSION
SYSTEM_INFO=$(uname -a)
PYTHON_VERSION=$(python3 --version 2>&1)
GIT_COMMIT=$(cd "$APP_DIR" && git rev-parse HEAD 2>/dev/null || echo "unknown")
PI_VERSION=$DETECTED_PI_VERSION
NEEDS_REBOOT=$NEEDS_REBOOT
I2C_DETECTION_SUCCESS=$I2C_DETECTION_SUCCESS
EOF
    
    # Set proper permissions on all created scripts
    find "$APP_DIR" -name "*.sh" -type f -exec chmod +x {} + 2>/dev/null || true
    
    # Clear trap - installation successful
    trap - EXIT
    
    success_message "Installation finalized successfully"
}

# ====================================================================
# MAIN INSTALLATION FLOW
# ====================================================================

display_header() {
    echo ""
    echo "========================================================================"
    echo "    Rodent Refreshment Regulator (RRR) - Robust Installer v$SCRIPT_VERSION"
    echo "========================================================================"
    echo ""
    echo "This installer will set up the complete RRR system with:"
    echo "• Raspberry Pi hardware detection and configuration"
    echo "• I2C interface setup with Pi 5 compatibility"
    echo "• Python environment and dependency management"
    echo "• Application installation with error recovery"
    echo "• Desktop integration and system services"
    echo ""
    echo "Installation log: $INSTALL_LOG"
    echo ""
}

installation_summary() {
    echo ""
    echo "========================================================================"
    echo "                      INSTALLATION SUMMARY"
    echo "========================================================================"
    echo ""
    
    if [ "$NEEDS_REBOOT" = true ]; then
        echo "🔄 REBOOT REQUIRED"
        echo ""
        echo "Configuration changes require a system reboot:"
        echo "  • I2C interface configuration"
        echo "  • Kernel module loading" 
        echo "  • Device permissions"
        echo "  • Power management settings"
        echo ""
        echo "After reboot, start the application using:"
        echo "  1. Desktop shortcut: Double-click 'RRR' icon"
        echo "  2. Command line: ~/rodent-refreshment-regulator/launch_rrr.sh"
        echo ""
        
        if [ "$I2C_DETECTION_SUCCESS" = false ]; then
            echo "⚠️  I2C buses were not detected during installation."
            echo "This is expected and should be resolved after reboot."
            echo ""
        fi
        
        echo "Would you like to reboot now? (y/n)"
        read -r reboot_choice
        
        if [[ $reboot_choice =~ ^[Yy]$ ]]; then
            echo ""
            echo "Rebooting in 5 seconds... (Press Ctrl+C to cancel)"
            sleep 5
            sudo reboot
        else
            echo ""
            echo "Please reboot your system before using the RRR application:"
            echo "  sudo reboot"
        fi
        
    else
        echo "✅ INSTALLATION COMPLETED SUCCESSFULLY"
        echo ""
        echo "The RRR system is ready to use!"
        echo ""
        echo "Start the application:"
        echo "  1. Desktop shortcut: Double-click 'RRR' icon"
        echo "  2. Command line: ~/rodent-refreshment-regulator/launch_rrr.sh"
        echo ""
        
        if [ "$I2C_DETECTION_SUCCESS" = true ]; then
            echo "✅ Hardware control is ready"
        else
            echo "⚠️  Hardware control may require troubleshooting"
            echo "Run: ~/rodent-refreshment-regulator/fix_i2c.sh"
        fi
    fi
    
    echo ""
    echo "📋 Troubleshooting Resources:"
    echo "  • System diagnostics: ~/rodent-refreshment-regulator/diagnose.sh"
    echo "  • Hardware testing: ~/rodent-refreshment-regulator/test_hardware.sh"
    echo "  • I2C troubleshooting: ~/rodent-refreshment-regulator/fix_i2c.sh"
    echo "  • Dependency fixes: ~/rodent-refreshment-regulator/fix_dependencies.sh"
    echo "  • Service management: ~/rodent-refreshment-regulator/toggle_service.sh"
    echo ""
    echo "📖 Documentation: https://github.com/Corticomics/rodRefReg"
    echo "📝 Installation log: $INSTALL_LOG"
    echo ""
}

main() {
    display_header
    
    log "INFO" "Starting RRR installation v$SCRIPT_VERSION"
    log "INFO" "Target user: $USER"
    log "INFO" "Installation directory: $APP_DIR"
    
    # Set up error handling and cleanup
    setup_cleanup_handler
    
    # Phase 1: System Requirements
    log "INFO" "=== Phase 1: System Requirements ==="
    detect_raspberry_pi
    check_system_requirements
    
    # Phase 2: Package Installation
    log "INFO" "=== Phase 2: Package Installation ==="
    update_system_packages
    install_system_dependencies
    validate_python_version
    install_relay_hat_driver
    
    # Phase 3: Hardware Configuration
    log "INFO" "=== Phase 3: Hardware Configuration ==="
    configure_i2c_interface
    detect_i2c_buses || true  # Don't fail if I2C detection fails
    
    # Phase 4: Application Setup
    log "INFO" "=== Phase 4: Application Setup ==="
    setup_application_directory
    setup_repository "$REPO_URL"
    
    # Phase 5: Python Environment
    log "INFO" "=== Phase 5: Python Environment ==="
    setup_python_environment
    install_python_dependencies
    verify_python_dependencies
    
    # Phase 6: System Integration
    log "INFO" "=== Phase 6: System Integration ==="
    create_launcher_script
    create_i2c_configuration_script
    create_update_script
    create_diagnostic_scripts
    create_desktop_integration
    create_system_service
    configure_power_management
    
    # Phase 7: Validation and Finalization
    log "INFO" "=== Phase 7: Validation and Finalization ==="
    validate_installation
    finalize_installation
    
    # Installation Complete
    success_message "Installation completed successfully!"
    installation_summary
}

# Start installation
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 
