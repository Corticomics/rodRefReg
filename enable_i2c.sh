#!/bin/bash

# Enhanced I2C Interface Enablement Script for Raspberry Pi
# Compatible with: Raspberry Pi 4, Raspberry Pi 5, and other Pi models
# Follows Raspberry Pi Foundation documentation best practices
# 
# This script implements:
# - Automatic Pi version detection
# - Correct config file path selection
# - Appropriate kernel module loading
# - Proper user permissions setup
# - Comprehensive error handling
# - Detailed diagnostic information

# ====================================================================
# CONFIGURATION AND INITIALIZATION
# ====================================================================

set -euo pipefail  # Strict error handling
IFS=$'\n\t'       # Secure Internal Field Separator

# Script metadata
readonly SCRIPT_VERSION="2.0"
readonly SCRIPT_NAME="Enhanced I2C Enablement Script"

# Logging setup
readonly LOG_FILE="/var/log/rrr_i2c_setup.log"

log() {
    local level="${1:-INFO}"
    local message="${2:-}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message" | tee -a "$LOG_FILE"
}

error_exit() {
    log "ERROR" "$1"
    echo "ERROR: $1" >&2
    exit 1
}

success_message() {
    log "SUCCESS" "$1"
}

# ====================================================================
# SYSTEM DETECTION AND VALIDATION
# ====================================================================

check_sudo() {
    if [ "$(id -u)" -ne 0 ]; then
        error_exit "This script must be run with sudo privileges. Please run: sudo $0"
    fi
    
    log "INFO" "Running with appropriate privileges"
}

detect_raspberry_pi() {
    log "INFO" "Detecting Raspberry Pi hardware..."
    
    if [ ! -f /proc/cpuinfo ]; then
        log "WARN" "Unable to read /proc/cpuinfo - assuming compatible hardware"
        return 0
    fi
    
    local pi_version=""
    
    if grep -q "Raspberry Pi 5" /proc/cpuinfo; then
        pi_version="5"
        log "INFO" "Raspberry Pi 5 detected"
    elif grep -q "Raspberry Pi 4" /proc/cpuinfo; then
        pi_version="4"
        log "INFO" "Raspberry Pi 4 detected"
    elif grep -q "Raspberry Pi" /proc/cpuinfo; then
        pi_version="other"
        log "INFO" "Raspberry Pi detected (older model)"
    elif grep -q "BCM" /proc/cpuinfo; then
        pi_version="compatible"
        log "INFO" "BCM-compatible hardware detected"
    else
        log "WARN" "This doesn't appear to be a Raspberry Pi"
        log "WARN" "Some features may not work correctly"
    fi
    
    # Export for use in other functions
    export DETECTED_PI_VERSION="$pi_version"
    return 0
}

validate_system() {
    log "INFO" "Validating system requirements..."
    
    # Check if this is a Debian-based system
    if ! command -v apt-get &>/dev/null; then
        error_exit "This script requires a Debian-based system with apt-get"
    fi
    
    # Check for required commands
    local required_commands=("modprobe" "groupadd" "usermod" "getent")
    
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &>/dev/null; then
            error_exit "Required command not found: $cmd"
        fi
    done
    
    success_message "System validation passed"
}

# ====================================================================
# I2C CONFIGURATION FUNCTIONS
# ====================================================================

enable_i2c_config() {
    log "INFO" "Configuring I2C in boot configuration..."
    
    local config_file="/boot/config.txt"
    local firmware_config="/boot/firmware/config.txt"
    
    # Raspberry Pi 5 uses different config path
    if [ -f "$firmware_config" ]; then
        config_file="$firmware_config"
        log "INFO" "Using Raspberry Pi 5 firmware config path: $config_file"
    else
        log "INFO" "Using standard config path: $config_file"
    fi
    
    if [ ! -f "$config_file" ]; then
        error_exit "Configuration file not found: $config_file"
    fi
    
    # Backup configuration file with timestamp
    local backup_file="${config_file}.bak.$(date +%Y%m%d_%H%M%S)"
    cp "$config_file" "$backup_file"
    log "INFO" "Configuration file backed up to: $backup_file"
    
    local need_reboot=false
    
    # Enable I2C interface
    if ! grep -q "^dtparam=i2c_arm=on" "$config_file"; then
        echo "dtparam=i2c_arm=on" >> "$config_file"
        log "INFO" "I2C interface enabled in configuration"
        need_reboot=true
    else
        log "INFO" "I2C interface already enabled in configuration"
    fi
    
    # Set I2C baudrate for reliability (especially important for Pi 5)
    if ! grep -q "dtparam=i2c_arm_baudrate" "$config_file"; then
        echo "dtparam=i2c_arm_baudrate=100000" >> "$config_file"
        log "INFO" "I2C baudrate set to 100kHz for optimal reliability"
    else
        log "INFO" "I2C baudrate already configured"
    fi
    
    # Export reboot status for main function
    export NEEDS_REBOOT="$need_reboot"
}

load_i2c_modules() {
    log "INFO" "Loading I2C kernel modules..."
    
    # Load i2c-dev module (universal)
    if modprobe i2c-dev 2>/dev/null; then
        log "INFO" "i2c-dev module loaded successfully"
    else
        log "WARN" "i2c-dev module already loaded or not available"
    fi
    
    # Load appropriate I2C bus module based on Pi version
    case "${DETECTED_PI_VERSION:-}" in
        "5")
            if modprobe i2c-bcm2835 2>/dev/null; then
                log "INFO" "i2c-bcm2835 module loaded for Raspberry Pi 5"
            else
                log "WARN" "i2c-bcm2835 module not available"
            fi
            ;;
        "4"|"other"|"compatible")
            if modprobe i2c-bcm2708 2>/dev/null; then
                log "INFO" "i2c-bcm2708 module loaded for Raspberry Pi 4/older"
            else
                log "WARN" "i2c-bcm2708 module not available"
            fi
            ;;
        *)
            # Try both modules for unknown hardware
            log "INFO" "Unknown Pi version, trying both module types"
            modprobe i2c-bcm2835 2>/dev/null || log "INFO" "i2c-bcm2835 not available"
            modprobe i2c-bcm2708 2>/dev/null || log "INFO" "i2c-bcm2708 not available"
            ;;
    esac
    
    # Ensure modules are loaded at boot
    local modules_file="/etc/modules"
    
    if ! grep -q "^i2c-dev" "$modules_file"; then
        echo "i2c-dev" >> "$modules_file"
        log "INFO" "Added i2c-dev to boot modules"
    fi
    
    # Add appropriate bus module based on Pi version
    case "${DETECTED_PI_VERSION:-}" in
        "5")
            if ! grep -q "^i2c-bcm2835" "$modules_file"; then
                echo "i2c-bcm2835" >> "$modules_file"
                log "INFO" "Added i2c-bcm2835 to boot modules"
            fi
            ;;
        *)
            if ! grep -q "^i2c-bcm2708" "$modules_file"; then
                echo "i2c-bcm2708" >> "$modules_file"
                log "INFO" "Added i2c-bcm2708 to boot modules"
            fi
            ;;
    esac
    
    success_message "I2C kernel modules configured"
}

install_i2c_tools() {
    log "INFO" "Installing I2C tools and dependencies..."
    
    # Update package lists
    if ! apt-get update; then
        log "WARN" "Package list update failed, continuing anyway"
    fi
    
    # Install required packages
    local packages=("i2c-tools" "python3-smbus" "python3-smbus2")
    
    for package in "${packages[@]}"; do
        if apt-get install -y "$package"; then
            log "INFO" "Installed package: $package"
        else
            log "WARN" "Failed to install package: $package"
        fi
    done
    
    success_message "I2C tools installation completed"
}

configure_user_permissions() {
    log "INFO" "Configuring user permissions for I2C access..."
    
    # Determine the actual user (when run with sudo)
    local username="${SUDO_USER:-$USER}"
    
    if [ -z "$username" ] || [ "$username" = "root" ]; then
        log "WARN" "Unable to determine target username, skipping user configuration"
        return 0
    fi
    
    log "INFO" "Configuring permissions for user: $username"
    
    # Create i2c group if it doesn't exist
    if ! getent group i2c > /dev/null; then
        if groupadd i2c; then
            log "INFO" "Created i2c group"
        else
            error_exit "Failed to create i2c group"
        fi
    else
        log "INFO" "i2c group already exists"
    fi
    
    # Add user to i2c group
    if usermod -a -G i2c "$username"; then
        log "INFO" "Added user '$username' to i2c group"
    else
        error_exit "Failed to add user to i2c group"
    fi
    
    # Set up udev rules for proper permissions
    cat > /etc/udev/rules.d/99-i2c.rules << 'EOF'
SUBSYSTEM=="i2c-dev", GROUP="i2c", MODE="0664"
KERNEL=="i2c-[0-9]*", GROUP="i2c", MODE="0664"
EOF
    
    log "INFO" "Created udev rules for I2C device permissions"
    
    # Reload udev rules
    if command -v udevadm &>/dev/null; then
        udevadm control --reload-rules
        udevadm trigger
        log "INFO" "Reloaded udev rules"
    fi
    
    success_message "User permissions configured"
}

# ====================================================================
# I2C TESTING AND VALIDATION
# ====================================================================

test_i2c_functionality() {
    log "INFO" "Testing I2C functionality..."
    
    # Check if i2cdetect is available
    if ! command -v i2cdetect &>/dev/null; then
        log "WARN" "i2cdetect command not found - I2C tools may not be installed correctly"
        return 1
    fi
    
    # Find available I2C buses
    local available_buses=()
    local bus_found=false
    
    log "INFO" "Scanning for I2C buses..."
    
    for i in $(seq 0 10); do
        if [ -e "/dev/i2c-$i" ]; then
            available_buses+=("$i")
            log "INFO" "Found I2C bus: /dev/i2c-$i"
            bus_found=true
        fi
    done
    
    if [ "$bus_found" = false ]; then
        log "WARN" "No I2C buses detected"
        log "INFO" "This is normal before reboot if I2C was just enabled"
        return 1
    fi
    
    # Test each available bus
    log "INFO" "Testing I2C buses with i2cdetect..."
    
    for bus in "${available_buses[@]}"; do
        log "INFO" "Scanning I2C bus $bus:"
        
        # Capture output and display it
        if i2cdetect -y "$bus" 2>/dev/null; then
            log "INFO" "Successfully scanned I2C bus $bus"
        else
            log "WARN" "Failed to scan I2C bus $bus"
        fi
    done
    
    success_message "I2C functionality test completed"
    return 0
}

provide_diagnostic_info() {
    log "INFO" "=== I2C Diagnostic Information ==="
    
    # Kernel modules
    log "INFO" "Loaded I2C kernel modules:"
    lsmod | grep i2c || log "INFO" "No I2C modules currently loaded"
    
    # Device files
    log "INFO" "Available I2C device files:"
    ls -la /dev/i2c-* 2>/dev/null || log "INFO" "No I2C device files found"
    
    # User groups
    local username="${SUDO_USER:-$USER}"
    if [ "$username" != "root" ]; then
        log "INFO" "User '$username' groups:"
        groups "$username" 2>/dev/null || log "WARN" "Unable to check user groups"
    fi
    
    # Configuration status
    local config_file="/boot/config.txt"
    if [ -f "/boot/firmware/config.txt" ]; then
        config_file="/boot/firmware/config.txt"
    fi
    
    log "INFO" "I2C configuration in $config_file:"
    grep -E "^dtparam=i2c" "$config_file" 2>/dev/null || log "INFO" "No I2C configuration found"
}

# ====================================================================
# MAIN EXECUTION FLOW
# ====================================================================

display_header() {
    echo ""
    echo "========================================================================"
    echo "               $SCRIPT_NAME v$SCRIPT_VERSION"
    echo "========================================================================"
    echo ""
    echo "This script will enable and configure the I2C interface for the"
    echo "Rodent Refreshment Regulator (RRR) system with full Raspberry Pi 5 support."
    echo ""
    echo "The script will:"
    echo "• Detect your Raspberry Pi model"
    echo "• Configure the appropriate I2C settings"
    echo "• Load required kernel modules"
    echo "• Set up user permissions"
    echo "• Test I2C functionality"
    echo ""
    echo "Installation log: $LOG_FILE"
    echo ""
}

installation_summary() {
    echo ""
    echo "========================================================================"
    echo "                    I2C CONFIGURATION SUMMARY"
    echo "========================================================================"
    echo ""
    
    provide_diagnostic_info
    
    echo ""
    if [ "${NEEDS_REBOOT:-false}" = true ]; then
        echo "🔄 REBOOT REQUIRED"
        echo ""
        echo "I2C configuration changes require a system reboot to take full effect."
        echo "After reboot, I2C devices should be available and accessible."
        echo ""
        echo "To test I2C after reboot, run:"
        echo "  sudo i2cdetect -y 1"
        echo ""
        echo "Would you like to reboot now? (y/n)"
        read -r -n 1 reboot_choice
        echo ""
        
        if [[ $reboot_choice =~ ^[Yy]$ ]]; then
            echo "Rebooting in 5 seconds... (Press Ctrl+C to cancel)"
            sleep 5
            reboot
        else
            echo "Please remember to reboot for all changes to take effect:"
            echo "  sudo reboot"
        fi
    else
        echo "✅ I2C CONFIGURATION COMPLETED"
        echo ""
        echo "I2C interface should now be available."
        echo "You can test it with: sudo i2cdetect -y 1"
    fi
    
    echo ""
    echo "📝 Configuration log: $LOG_FILE"
    echo ""
}

main() {
    # Initialize logging
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"
    
    display_header
    
    log "INFO" "Starting I2C configuration v$SCRIPT_VERSION"
    
    # Phase 1: System Validation
    log "INFO" "=== Phase 1: System Validation ==="
    check_sudo
    detect_raspberry_pi
    validate_system
    
    # Phase 2: I2C Configuration
    log "INFO" "=== Phase 2: I2C Configuration ==="
    enable_i2c_config
    load_i2c_modules
    
    # Phase 3: Tools and Permissions
    log "INFO" "=== Phase 3: Tools and Permissions ==="
    install_i2c_tools
    configure_user_permissions
    
    # Phase 4: Testing and Validation
    log "INFO" "=== Phase 4: Testing and Validation ==="
    test_i2c_functionality || log "WARN" "I2C testing incomplete (may require reboot)"
    
    # Installation Complete
    success_message "I2C configuration completed successfully!"
    installation_summary
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 