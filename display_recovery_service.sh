#!/bin/bash
# Display Recovery Service Module for RRR Laboratory System
# Provides automatic display recovery when monitors are power cycled
# Author: RRR Development Team
# Version: 1.0

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly MODULE_NAME="DisplayRecoveryService"
readonly SERVICE_NAME="rrr-display-recovery"
readonly LOG_FILE="${HOME}/rrr_display_recovery.log"

# Logging function
log() {
    local level="$1"
    local message="$2"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$MODULE_NAME] [$level] $message" | tee -a "$LOG_FILE"
}

# Create the display monitoring script
create_monitor_script() {
    local install_dir="$1"
    local monitor_script="${install_dir}/tools/display_monitor.sh"
    
    log "INFO" "Creating display monitoring script at $monitor_script"
    
    mkdir -p "$(dirname "$monitor_script")"
    
    cat > "$monitor_script" << 'EOF'
#!/bin/bash
# RRR Display Monitor - Detects and recovers from display disconnections
set -euo pipefail

readonly CHECK_INTERVAL=30
readonly LOG_FILE="$HOME/rrr_display_monitor.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S'): $1" | tee -a "$LOG_FILE"
}

check_display_active() {
    if [ -n "${DISPLAY:-}" ] && command -v xrandr >/dev/null 2>&1; then
        local monitor_count
        monitor_count=$(xrandr --listmonitors 2>/dev/null | head -1 | grep -o '[0-9]\+' || echo "0")
        [ "$monitor_count" -gt 0 ]
    else
        return 1
    fi
}

recover_display() {
    log "Attempting display recovery..."
    
    # Method 1: Refresh display detection
    if command -v xrandr >/dev/null 2>&1; then
        DISPLAY=:0 xrandr --auto >/dev/null 2>&1 || true
        sleep 2
    fi
    
    # Method 2: Force HDMI hotplug detection
    for hdmi_path in /sys/class/drm/card*/HDMI-A-*/status; do
        if [ -f "$hdmi_path" ]; then
            echo "detect" | sudo tee "$hdmi_path" >/dev/null 2>&1 || true
        fi
    done
    
    sleep 3
    
    if check_display_active; then
        log "Display recovery successful"
        return 0
    else
        log "Display recovery failed"
        return 1
    fi
}

# Main monitoring loop
main() {
    log "Display monitoring service started"
    
    local last_status="unknown"
    
    while true; do
        if check_display_active; then
            if [ "$last_status" != "active" ]; then
                log "Display is active"
                last_status="active"
            fi
        else
            if [ "$last_status" != "inactive" ]; then
                log "Display inactive - triggering recovery"
                last_status="inactive"
                recover_display &
            fi
        fi
        
        sleep $CHECK_INTERVAL
    done
}

main "$@"
EOF
    
    chmod +x "$monitor_script"
    log "INFO" "Monitor script created successfully"
}

# Create the systemd service
create_systemd_service() {
    local install_dir="$1"
    local service_file="/etc/systemd/system/${SERVICE_NAME}.service"
    
    log "INFO" "Creating systemd service: $service_file"
    
    sudo tee "$service_file" > /dev/null << EOF
[Unit]
Description=RRR Display Recovery Monitor
Documentation=https://github.com/Corticomics/rodRefReg
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
ExecStart=${install_dir}/tools/display_monitor.sh
Restart=always
RestartSec=10
User=${USER}
Group=${USER}
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/${USER}/.Xauthority

[Install]
WantedBy=graphical-session.target
EOF
    
    log "INFO" "Systemd service created"
}

# Install the recovery service
install_recovery_service() {
    local install_dir="$1"
    
    log "INFO" "Installing display recovery service"
    
    # Create monitor script
    create_monitor_script "$install_dir"
    
    # Create systemd service
    create_systemd_service "$install_dir"
    
    # Enable and start service
    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    
    log "INFO" "Display recovery service installed and enabled"
    log "INFO" "Service will start automatically after reboot"
}

# Start the service immediately
start_service() {
    log "INFO" "Starting display recovery service"
    
    if sudo systemctl start "$SERVICE_NAME"; then
        log "INFO" "Service started successfully"
    else
        log "WARN" "Failed to start service - will start after reboot"
    fi
}

# Stop the service
stop_service() {
    log "INFO" "Stopping display recovery service"
    sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true
}

# Uninstall the service
uninstall_service() {
    log "INFO" "Uninstalling display recovery service"
    
    stop_service
    sudo systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    sudo rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
    sudo systemctl daemon-reload
    
    log "INFO" "Service uninstalled successfully"
}

# Check service status
status_service() {
    echo "=== RRR Display Recovery Service Status ==="
    
    if systemctl is-enabled "$SERVICE_NAME" >/dev/null 2>&1; then
        echo "Service: ENABLED"
    else
        echo "Service: DISABLED"
    fi
    
    if systemctl is-active "$SERVICE_NAME" >/dev/null 2>&1; then
        echo "Status: RUNNING"
    else
        echo "Status: STOPPED"
    fi
    
    echo ""
    echo "Recent logs:"
    sudo journalctl -u "$SERVICE_NAME" --no-pager -n 10 2>/dev/null || echo "No logs available"
}

# Usage information
show_usage() {
    cat << EOF
RRR Display Recovery Service Module

USAGE:
    $0 install <install_dir>  - Install the recovery service
    $0 start                  - Start the service
    $0 stop                   - Stop the service
    $0 status                 - Show service status
    $0 uninstall              - Remove the service
    $0 --help                 - Show this help

DESCRIPTION:
    Provides automatic display recovery for laboratory environments
    where monitors are frequently power cycled during experiments.
    
EXAMPLES:
    $0 install /home/pi/rodent-refreshment-regulator
    $0 status
    $0 start
    
EOF
}

# Main execution
main() {
    case "${1:-}" in
        "install")
            if [ -z "${2:-}" ]; then
                echo "ERROR: Install directory required"
                show_usage
                exit 1
            fi
            install_recovery_service "$2"
            ;;
        "start")
            start_service
            ;;
        "stop")
            stop_service
            ;;
        "status")
            status_service
            ;;
        "uninstall")
            uninstall_service
            ;;
        "--help"|"-h"|"help")
            show_usage
            ;;
        *)
            echo "ERROR: Invalid command: ${1:-}"
            show_usage
            exit 1
            ;;
    esac
}

# Only run main if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi