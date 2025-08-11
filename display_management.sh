#!/bin/bash
# Enterprise Display Management Module for RRR Laboratory System
# Handles Raspberry Pi 5 HDMI hotplug detection and display recovery
# Author: RRR Development Team
# Version: 1.0

set -euo pipefail

# Module configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly MODULE_NAME="DisplayManagement"
readonly MODULE_VERSION="1.0.0"
readonly LOG_FILE="${HOME}/rrr_display_management.log"

# Logging function
log() {
    local level="$1"
    local message="$2"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$MODULE_NAME] [$level] $message" | tee -a "$LOG_FILE"
}

# Detect Raspberry Pi model and configuration paths
detect_system_config() {
    if [ -f "/boot/firmware/config.txt" ]; then
        echo "/boot/firmware"
    elif [ -f "/boot/config.txt" ]; then
        echo "/boot"
    else
        log "ERROR" "Cannot detect boot configuration directory"
        return 1
    fi
}

# Configure HDMI settings for robust hotplug detection
configure_hdmi_settings() {
    local boot_path="$1"
    local config_file="${boot_path}/config.txt"
    
    log "INFO" "Configuring HDMI settings in $config_file"
    
    # Backup original configuration
    sudo cp "$config_file" "${config_file}.backup_$(date +%Y%m%d_%H%M%S)"
    
    # Remove existing HDMI settings to avoid conflicts
    sudo sed -i '/^hdmi_blanking=/d' "$config_file"
    sudo sed -i '/^hdmi_force_hotplug=/d' "$config_file"
    sudo sed -i '/^config_hdmi_boost=/d' "$config_file"
    
    # Add optimized HDMI configuration
    cat << 'EOF' | sudo tee -a "$config_file" > /dev/null

# RRR Display Management - Pi 5 HDMI Hotplug Fix
hdmi_blanking=0
hdmi_force_hotplug=1
config_hdmi_boost=4
disable_overscan=1
EOF
    
    log "INFO" "HDMI configuration updated successfully"
}

# Configure kernel parameters for display stability
configure_kernel_parameters() {
    local boot_path="$1"
    local cmdline_file="${boot_path}/cmdline.txt"
    
    log "INFO" "Configuring kernel display parameters"
    
    # Backup cmdline.txt
    sudo cp "$cmdline_file" "${cmdline_file}.backup_$(date +%Y%m%d_%H%M%S)"
    
    # Read current parameters
    local current_params
    current_params=$(cat "$cmdline_file")
    
    # Remove existing display parameters
    current_params=$(echo "$current_params" | sed -e 's/video=[^ ]* //g' -e 's/consoleblank=[^ ]* //g')
    
    # Add display stability parameters
    local new_params="consoleblank=0 video=HDMI-A-1:1920x1080M@60D"
    
    # Write updated parameters
    echo "$current_params $new_params" | sudo tee "$cmdline_file" > /dev/null
    
    log "INFO" "Kernel display parameters configured"
}

# Main installation function
install_display_management() {
    log "INFO" "Installing RRR Display Management System v$MODULE_VERSION"
    
    # Detect system configuration
    local boot_path
    boot_path=$(detect_system_config)
    
    if [ $? -ne 0 ]; then
        log "ERROR" "Failed to detect system configuration"
        return 1
    fi
    
    log "INFO" "Detected boot configuration path: $boot_path"
    
    # Configure HDMI and kernel parameters
    configure_hdmi_settings "$boot_path"
    configure_kernel_parameters "$boot_path"
    
    log "INFO" "Display management installation completed successfully"
    log "INFO" "A system reboot is required for changes to take effect"
    
    return 0
}

# Module self-test
test_display_management() {
    log "INFO" "Running display management self-test"
    
    # Test 1: Check if required files exist
    local boot_path
    boot_path=$(detect_system_config)
    
    if [ ! -f "${boot_path}/config.txt" ]; then
        log "ERROR" "config.txt not found at $boot_path"
        return 1
    fi
    
    if [ ! -f "${boot_path}/cmdline.txt" ]; then
        log "ERROR" "cmdline.txt not found at $boot_path"
        return 1
    fi
    
    # Test 2: Verify HDMI configuration
    if grep -q "hdmi_force_hotplug=1" "${boot_path}/config.txt"; then
        log "INFO" "✓ HDMI hotplug configuration verified"
    else
        log "WARN" "HDMI hotplug configuration not found"
    fi
    
    # Test 3: Verify kernel parameters
    if grep -q "consoleblank=0" "${boot_path}/cmdline.txt"; then
        log "INFO" "✓ Console blanking disabled"
    else
        log "WARN" "Console blanking configuration not found"
    fi
    
    log "INFO" "Self-test completed"
    return 0
}

# Usage information
show_usage() {
    cat << EOF
RRR Display Management Module v$MODULE_VERSION

USAGE:
    $0 install    - Install display management configuration
    $0 test       - Run self-test
    $0 --help     - Show this help message

DESCRIPTION:
    This module configures Raspberry Pi 5 HDMI settings to prevent
    display detection issues when monitors are power cycled.
    
    Specifically addresses:
    - HDMI hotplug detection failures
    - EDID communication timeouts
    - Display recovery after monitor power cycling
    
EXAMPLES:
    $0 install    # Install the display management system
    $0 test       # Verify installation
    
EOF
}

# Main execution logic
main() {
    case "${1:-}" in
        "install")
            install_display_management
            ;;
        "test")
            test_display_management
            ;;
        "--help"|"-h"|"help")
            show_usage
            ;;
        *)
            log "ERROR" "Invalid command: ${1:-}"
            show_usage
            exit 1
            ;;
    esac
}

# Only run main if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi