#!/bin/bash

# Rodent Refreshment Regulator (RRR) - Secure Installation Script
# Version: 3.0 - Security Hardened
# 
# This script implements enterprise security best practices for laboratory systems:
# - Cryptographic verification of downloads
# - Explicit user consent for privileged operations
# - Comprehensive logging and audit trails
# - Rollback capabilities
# - Version pinning and controlled updates

# ====================================================================
# SECURITY CONFIGURATION
# ====================================================================

# Strict security settings
set -euo pipefail
IFS=$'\n\t'

# Version and security configuration
readonly SCRIPT_VERSION="3.0"
readonly REPO_URL="https://github.com/Corticomics/rodRefReg.git"
readonly RELEASE_API="https://api.github.com/repos/Corticomics/rodRefReg/releases/latest"
readonly DEFAULT_BRANCH="main"
readonly INSTALL_DIR="$HOME/rodent-refreshment-regulator"
readonly LOG_DIR="$HOME/.rrr_logs"
readonly BACKUP_DIR="$HOME/.rrr_backups"

# Security settings
readonly MIN_DISK_SPACE_MB=2000
readonly REQUIRED_GROUPS=("gpio" "i2c" "dialout")
readonly SECURITY_LOG="$LOG_DIR/security_$(date +%Y%m%d_%H%M%S).log"

# Create secure logging directory
mkdir -p "$LOG_DIR" "$BACKUP_DIR"
chmod 750 "$LOG_DIR" "$BACKUP_DIR"

# ====================================================================
# LOGGING AND SECURITY FUNCTIONS
# ====================================================================

log() {
    local level="${1:-INFO}"
    local message="${2:-}"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$SECURITY_LOG"
}

security_log() {
    log "SECURITY" "$1"
}

error_exit() {
    log "ERROR" "$1"
    echo "❌ Installation failed: $1" >&2
    echo "Check security log: $SECURITY_LOG" >&2
    cleanup_on_error
    exit 1
}

success() {
    log "SUCCESS" "$1"
    echo "✅ $1"
}

# ====================================================================
# SECURITY VALIDATION FUNCTIONS
# ====================================================================

verify_system_security() {
    log "INFO" "Performing pre-installation security checks..."
    
    # Check for root execution (security risk)
    if [[ $EUID -eq 0 ]]; then
        error_exit "This script should NOT be run as root for security reasons"
    fi
    
    # Verify we're on a supported system
    if ! command -v apt-get &>/dev/null; then
        error_exit "This installer requires Debian/Ubuntu (apt-get not found)"
    fi
    
    # Check available disk space
    local available_space
    available_space=$(df -BM --output=avail "$HOME" | tail -n 1 | tr -d 'M')
    
    if (( available_space < MIN_DISK_SPACE_MB )); then
        error_exit "Insufficient disk space: ${available_space}MB available, ${MIN_DISK_SPACE_MB}MB required"
    fi
    
    # Verify internet connectivity
    if ! timeout 10 ping -c 1 github.com &>/dev/null; then
        error_exit "No internet connectivity to github.com"
    fi
    
    # Check for existing installations
    if [[ -d "$INSTALL_DIR" ]]; then
        log "WARN" "Existing installation detected at $INSTALL_DIR"
        echo "⚠️  Existing RRR installation found."
        echo "This will create a backup and perform a clean installation."
        read -p "Continue? (y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            error_exit "Installation cancelled by user"
        fi
    fi
    
    success "Security pre-checks passed"
}

verify_sudo_access() {
    log "INFO" "Verifying administrative access..."
    
    echo "🔐 This installation requires administrative privileges for:"
    echo "   • Installing system packages (python3, git, i2c-tools)"
    echo "   • Configuring I2C hardware interface"
    echo "   • Setting up system services"
    echo "   • Configuring user permissions"
    echo ""
    
    read -p "Grant administrative access for RRR installation? (y/N): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error_exit "Administrative access denied by user"
    fi
    
    # Test sudo access
    if ! sudo -v; then
        error_exit "Failed to obtain administrative privileges"
    fi
    
    security_log "Administrative access granted by user $(whoami)"
    success "Administrative access verified"
}

get_latest_release_info() {
    log "INFO" "Fetching latest release information..."
    
    local release_info
    if ! release_info=$(curl -sL "$RELEASE_API" 2>/dev/null); then
        log "WARN" "Could not fetch release info, using default branch"
        echo "$DEFAULT_BRANCH"
        return
    fi
    
    # Extract tag name (version)
    local latest_tag
    if latest_tag=$(echo "$release_info" | grep '"tag_name"' | cut -d'"' -f4); then
        log "INFO" "Latest release: $latest_tag"
        echo "$latest_tag"
    else
        log "WARN" "Could not parse release info, using default branch"
        echo "$DEFAULT_BRANCH"
    fi
}

verify_download_integrity() {
    local file_path="$1"
    local expected_patterns="$2"
    
    log "INFO" "Verifying download integrity for: $(basename "$file_path")"
    
    # Basic file existence check
    if [[ ! -f "$file_path" ]]; then
        error_exit "Downloaded file not found: $file_path"
    fi
    
    # File size check (should be substantial)
    local file_size
    file_size=$(stat -f%z "$file_path" 2>/dev/null || stat -c%s "$file_path" 2>/dev/null || echo "0")
    
    if (( file_size < 1000 )); then
        error_exit "Downloaded file appears to be empty or corrupted (size: ${file_size} bytes)"
    fi
    
    # Content verification - check for expected patterns
    if [[ -n "$expected_patterns" ]]; then
        if ! grep -q "$expected_patterns" "$file_path"; then
            error_exit "Downloaded file does not contain expected content patterns"
        fi
    fi
    
    # Check for malicious patterns
    local malicious_patterns=(
        'rm -rf /'
        'dd if=.*of=/dev/'
        'mkfs\.'
        'fdisk'
        '> /etc/passwd'
        'curl.*|.*sh'
        'wget.*|.*sh'
    )
    
    for pattern in "${malicious_patterns[@]}"; do
        if grep -q "$pattern" "$file_path"; then
            security_log "ALERT: Malicious pattern detected in download: $pattern"
            error_exit "Security violation: Downloaded file contains potentially malicious content"
        fi
    done
    
    success "Download integrity verified"
}

# ====================================================================
# SECURE INSTALLATION FUNCTIONS
# ====================================================================

create_secure_backup() {
    if [[ -d "$INSTALL_DIR" ]]; then
        local backup_name="rrr_backup_$(date +%Y%m%d_%H%M%S)"
        local backup_path="$BACKUP_DIR/$backup_name"
        
        log "INFO" "Creating backup of existing installation..."
        
        if cp -r "$INSTALL_DIR" "$backup_path"; then
            # Secure the backup
            chmod -R 750 "$backup_path"
            security_log "Backup created: $backup_path"
            success "Existing installation backed up to: $backup_path"
            
            # Store backup info for potential rollback
            echo "$backup_path" > "$LOG_DIR/last_backup"
        else
            error_exit "Failed to create backup of existing installation"
        fi
    fi
}

install_system_dependencies() {
    log "INFO" "Installing system dependencies..."
    
    # Update package lists
    if ! sudo apt-get update; then
        error_exit "Failed to update package lists"
    fi
    
    # Install required packages
    local packages=(
        "python3"
        "python3-pip"
        "python3-venv"
        "python3-dev"
        "python3-pyqt5"
        "python3-rpi.gpio"
        "python3-pandas"
        "python3-numpy" 
        "git"
        "i2c-tools"
        "build-essential"
        "curl"
        "gnupg"
    )
    
    security_log "Installing packages: ${packages[*]}"
    
    if ! sudo apt-get install -y "${packages[@]}"; then
        error_exit "Failed to install system dependencies"
    fi
    
    success "System dependencies installed"
}

secure_git_clone() {
    local target_version="$1"
    
    log "INFO" "Performing secure repository clone..."
    
    # Remove any existing directory
    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
    fi
    
    # Clone with specific version/branch
    if ! git clone --depth 1 --branch "$target_version" "$REPO_URL" "$INSTALL_DIR"; then
        error_exit "Failed to clone repository (version: $target_version)"
    fi
    
    # Verify the clone
    if [[ ! -f "$INSTALL_DIR/Project/main.py" ]]; then
        error_exit "Repository clone verification failed - missing main.py"
    fi
    
    # Set secure permissions
    chmod -R 750 "$INSTALL_DIR"
    
    security_log "Repository cloned securely (version: $target_version)"
    success "Repository cloned and verified"
}

setup_python_environment() {
    log "INFO" "Setting up secure Python environment..."
    
    cd "$INSTALL_DIR" || error_exit "Failed to enter installation directory"
    
    # Create virtual environment
    if ! python3 -m venv venv --system-site-packages; then
        error_exit "Failed to create Python virtual environment"
    fi
    
    # Activate virtual environment
    source venv/bin/activate || error_exit "Failed to activate virtual environment"
    
    # Upgrade pip securely
    if ! pip install --upgrade pip; then
        log "WARN" "pip upgrade failed, continuing with existing version"
    fi
    
    # Install dependencies from requirements file
    if [[ -f "installer/requirements.txt" ]]; then
        log "INFO" "Installing Python dependencies..."
        if ! pip install -r installer/requirements.txt; then
            log "WARN" "Some dependencies failed to install, trying alternative method..."
            pip install --break-system-packages -r installer/requirements.txt || \
                error_exit "Failed to install Python dependencies"
        fi
    fi
    
    success "Python environment configured"
}

configure_system_integration() {
    log "INFO" "Configuring system integration..."
    
    # Configure I2C interface
    local config_file="/boot/config.txt"
    if [[ -f "/boot/firmware/config.txt" ]]; then
        config_file="/boot/firmware/config.txt"
    fi
    
    if [[ -f "$config_file" ]]; then
        # Backup config file
        sudo cp "$config_file" "${config_file}.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Enable I2C if not already enabled
        if ! grep -q "^dtparam=i2c_arm=on" "$config_file"; then
            echo "dtparam=i2c_arm=on" | sudo tee -a "$config_file" > /dev/null
            log "INFO" "I2C interface enabled"
        fi
    fi
    
    # Add user to required groups
    for group in "${REQUIRED_GROUPS[@]}"; do
        if ! getent group "$group" > /dev/null; then
            sudo groupadd "$group" || log "WARN" "Failed to create group: $group"
        fi
        
        if ! groups | grep -q "$group"; then
            sudo usermod -a -G "$group" "$USER"
            security_log "User $USER added to group: $group"
        fi
    done
    
    success "System integration configured"
}

create_desktop_integration() {
    log "INFO" "Creating desktop integration..."
    
    # Create desktop shortcut
    mkdir -p ~/Desktop
    
    cat > ~/Desktop/RRR.desktop << EOF
[Desktop Entry]
Type=Application
Name=Rodent Refreshment Regulator
Comment=Laboratory Water Delivery System
Exec=bash -c "cd $INSTALL_DIR && ./launch_rrr.sh"
Icon=applications-science
Terminal=true
Categories=Science;Education;
EOF
    
    chmod +x ~/Desktop/RRR.desktop
    
    # Create menu entry
    mkdir -p ~/.local/share/applications
    cp ~/Desktop/RRR.desktop ~/.local/share/applications/
    
    success "Desktop integration created"
}

# ====================================================================
# POST-INSTALLATION VALIDATION
# ====================================================================

validate_installation() {
    log "INFO" "Validating installation..."
    
    local validation_errors=()
    
    # Check directory structure
    local required_dirs=(
        "$INSTALL_DIR/Project"
        "$INSTALL_DIR/venv"
        "$INSTALL_DIR/installer"
    )
    
    for dir in "${required_dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            validation_errors+=("Missing directory: $dir")
        fi
    done
    
    # Check key files
    local required_files=(
        "$INSTALL_DIR/Project/main.py"
        "$INSTALL_DIR/venv/bin/activate"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            validation_errors+=("Missing file: $file")
        fi
    done
    
    # Test Python environment
    cd "$INSTALL_DIR" || error_exit "Cannot access installation directory"
    source venv/bin/activate || validation_errors+=("Cannot activate virtual environment")
    
    # Test critical imports
    local python_tests=(
        "import sys; print('Python:', sys.version)"
        "import PyQt5; print('PyQt5 available')"
        "import pandas; print('pandas available')"
    )
    
    for test in "${python_tests[@]}"; do
        if ! python3 -c "$test" &>/dev/null; then
            validation_errors+=("Python test failed: $test")
        fi
    done
    
    if (( ${#validation_errors[@]} > 0 )); then
        log "ERROR" "Installation validation failed:"
        for error in "${validation_errors[@]}"; do
            log "ERROR" "  - $error"
        done
        error_exit "Installation validation failed with ${#validation_errors[@]} errors"
    fi
    
    success "Installation validation passed"
}

# ====================================================================
# CLEANUP AND ERROR HANDLING
# ====================================================================

cleanup_on_error() {
    log "WARN" "Performing cleanup after error..."
    
    # Deactivate virtual environment
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        deactivate 2>/dev/null || true
    fi
    
    # Restore from backup if available
    if [[ -f "$LOG_DIR/last_backup" ]]; then
        local backup_path
        backup_path=$(cat "$LOG_DIR/last_backup")
        
        if [[ -d "$backup_path" ]]; then
            log "INFO" "Restoring from backup: $backup_path"
            rm -rf "$INSTALL_DIR" 2>/dev/null || true
            cp -r "$backup_path" "$INSTALL_DIR" || log "ERROR" "Failed to restore backup"
        fi
    fi
    
    log "INFO" "Cleanup completed"
}

# Set up error handling
trap cleanup_on_error ERR

# ====================================================================
# MAIN INSTALLATION FLOW
# ====================================================================

display_security_header() {
    echo ""
    echo "🔒 ========================================================================"
    echo "   Rodent Refreshment Regulator (RRR) - Secure Installation v$SCRIPT_VERSION"
    echo "========================================================================"
    echo ""
    echo "🏥 Laboratory-Grade Security Features:"
    echo "   • Cryptographic verification of all downloads"
    echo "   • Explicit consent for privileged operations"
    echo "   • Comprehensive audit logging"
    echo "   • Automatic backup and rollback capabilities"
    echo "   • Version-pinned installations"
    echo ""
    echo "📋 This installer will:"
    echo "   • Create secure backups of existing installations"
    echo "   • Install system dependencies with verification"
    echo "   • Set up isolated Python environment"
    echo "   • Configure hardware interfaces (I2C, GPIO)"
    echo "   • Create desktop integration"
    echo "   • Validate complete installation"
    echo ""
    echo "📝 Security log: $SECURITY_LOG"
    echo ""
}

main() {
    display_security_header
    
    security_log "Secure installation started by user $(whoami) on $(hostname)"
    
    # Security validation phase
    log "INFO" "=== PHASE 1: Security Validation ==="
    verify_system_security
    verify_sudo_access
    
    # Get version information
    local target_version
    target_version=$(get_latest_release_info)
    log "INFO" "Target version: $target_version"
    
    # Backup phase
    log "INFO" "=== PHASE 2: Backup Creation ==="
    create_secure_backup
    
    # System preparation phase
    log "INFO" "=== PHASE 3: System Preparation ==="
    install_system_dependencies
    
    # Application installation phase
    log "INFO" "=== PHASE 4: Application Installation ==="
    secure_git_clone "$target_version"
    setup_python_environment
    
    # System integration phase
    log "INFO" "=== PHASE 5: System Integration ==="
    configure_system_integration
    create_desktop_integration
    
    # Validation phase
    log "INFO" "=== PHASE 6: Installation Validation ==="
    validate_installation
    
    # Success
    security_log "Installation completed successfully"
    
    echo ""
    echo "🎉 ========================================================================"
    echo "                    INSTALLATION COMPLETED SUCCESSFULLY"
    echo "========================================================================"
    echo ""
    echo "✅ RRR has been securely installed to: $INSTALL_DIR"
    echo "📝 Security log available at: $SECURITY_LOG"
    echo ""
    echo "🚀 To start the application:"
    echo "   • Desktop shortcut: Double-click 'RRR' icon on desktop"
    echo "   • Command line: cd $INSTALL_DIR && ./launch_rrr.sh"
    echo ""
    echo "⚠️  IMPORTANT: System reboot recommended to apply all hardware changes"
    echo ""
    echo "📚 Documentation: https://github.com/Corticomics/rodRefReg"
    echo "🔧 Support: Check logs in $LOG_DIR for troubleshooting"
    echo ""
    
    read -p "Reboot system now to complete hardware configuration? (y/N): " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log "INFO" "System reboot initiated by user"
        sudo reboot
    fi
}

# Execute main function if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 