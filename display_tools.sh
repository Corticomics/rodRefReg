#!/bin/bash
# User-Friendly Display Management Tools for RRR System
# Provides simple commands for laboratory staff to manage display issues
# Author: RRR Development Team
# Version: 1.0

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly MODULE_NAME="DisplayTools"

# Check if display is working
check_display() {
    echo "=== RRR Display Status Check ==="
    echo ""
    
    if command -v xrandr >/dev/null 2>&1; then
        echo "Display system: Available"
        
        if xrandr --listmonitors 2>/dev/null | grep -q "Monitors: [1-9]"; then
            echo "Display status: ✓ WORKING"
            echo ""
            echo "Connected displays:"
            xrandr --listmonitors | tail -n +2
        else
            echo "Display status: ✗ NO DISPLAY DETECTED"
            echo ""
            echo "Troubleshooting suggestions:"
            echo "1. Check HDMI cable connections"
            echo "2. Ensure monitor is powered on"
            echo "3. Try running: $0 recover"
        fi
    else
        echo "Display system: Not available (running headless?)"
    fi
    
    echo ""
}

# Attempt to recover display
recover_display() {
    echo "=== RRR Display Recovery ==="
    echo "Attempting to recover display connection..."
    echo ""
    
    local success=false
    
    # Method 1: Refresh display detection
    echo "Step 1: Refreshing display detection..."
    if command -v xrandr >/dev/null 2>&1; then
        DISPLAY=:0 xrandr --auto >/dev/null 2>&1 || true
        sleep 2
        
        if xrandr --listmonitors 2>/dev/null | grep -q "Monitors: [1-9]"; then
            echo "✓ Display recovered using xrandr"
            success=true
        fi
    fi
    
    # Method 2: Force HDMI hotplug detection
    if [ "$success" = false ]; then
        echo "Step 2: Forcing HDMI hotplug detection..."
        for hdmi_path in /sys/class/drm/card*/HDMI-A-*/status; do
            if [ -f "$hdmi_path" ]; then
                echo "detect" | sudo tee "$hdmi_path" >/dev/null 2>&1 || true
            fi
        done
        
        sleep 3
        
        if command -v xrandr >/dev/null 2>&1 && xrandr --listmonitors 2>/dev/null | grep -q "Monitors: [1-9]"; then
            echo "✓ Display recovered using hotplug detection"
            success=true
        fi
    fi
    
    # Results
    echo ""
    if [ "$success" = true ]; then
        echo "🎉 Display recovery successful!"
        echo ""
        check_display
    else
        echo "❌ Automatic recovery failed."
        echo ""
        echo "Manual steps to try:"
        echo "1. Power cycle the monitor (turn off and on)"
        echo "2. Check all cable connections"
        echo "3. Try a different HDMI cable"
        echo "4. Restart the Raspberry Pi: sudo reboot"
        echo ""
        echo "If problems persist, contact technical support."
    fi
}

# Show recovery service status
show_service_status() {
    echo "=== RRR Display Recovery Service ==="
    echo ""
    
    local service_name="rrr-display-recovery"
    
    if systemctl list-unit-files | grep -q "$service_name"; then
        echo "Service installed: ✓ YES"
        
        if systemctl is-enabled "$service_name" >/dev/null 2>&1; then
            echo "Service enabled: ✓ YES"
        else
            echo "Service enabled: ✗ NO"
        fi
        
        if systemctl is-active "$service_name" >/dev/null 2>&1; then
            echo "Service running: ✓ YES"
        else
            echo "Service running: ✗ NO"
        fi
        
        echo ""
        echo "Recent service activity:"
        sudo journalctl -u "$service_name" --no-pager -n 5 2>/dev/null || echo "No recent activity"
        
    else
        echo "Service installed: ✗ NO"
        echo ""
        echo "The automatic display recovery service is not installed."
        echo "Run the installer to set up automatic recovery."
    fi
    
    echo ""
}

# Capture current display configuration
capture_config() {
    echo "=== RRR Display Configuration Capture ==="
    echo ""
    
    if ! command -v xrandr >/dev/null 2>&1; then
        echo "❌ Display tools not available"
        echo "This command must be run from the desktop environment."
        exit 1
    fi
    
    if ! xrandr --listmonitors 2>/dev/null | grep -q "Monitors: [1-9]"; then
        echo "❌ No active displays detected"
        echo "Please ensure display is working before capturing configuration."
        exit 1
    fi
    
    echo "Current display configuration:"
    xrandr --listmonitors
    echo ""
    
    # Capture EDID data
    local captured=false
    for port in {0..1}; do
        local edid_path="/sys/devices/platform/axi/axi:gpu/drm/card*/card*-HDMI-A-$((port + 1))/edid"
        for edid_file in $edid_path; do
            if [ -f "$edid_file" ] && [ -s "$edid_file" ]; then
                local output_file="/lib/firmware/rrr_display_port${port}.bin"
                if sudo cp "$edid_file" "$output_file" 2>/dev/null; then
                    echo "✓ Captured EDID for HDMI port $((port + 1))"
                    captured=true
                fi
            fi
        done
    done
    
    if [ "$captured" = true ]; then
        echo ""
        echo "🎉 Display configuration captured successfully!"
        echo "Your display will now automatically recover after power cycling."
    else
        echo ""
        echo "❌ Failed to capture display configuration"
        echo "This may indicate a hardware or driver issue."
    fi
}

# Show usage information
show_usage() {
    cat << EOF
RRR Display Management Tools

COMMANDS:
    check     - Check current display status
    recover   - Attempt to recover display connection
    capture   - Capture current display configuration for automatic recovery
    service   - Show automatic recovery service status
    help      - Show this help message

DESCRIPTION:
    Simple tools for laboratory staff to diagnose and fix display issues
    when monitors are power cycled during experiments.
    
USAGE EXAMPLES:
    $0 check      # Check if display is working
    $0 recover    # Fix display connection issues
    $0 capture    # Save current working display configuration
    $0 service    # Check automatic recovery service
    
TROUBLESHOOTING:
    If display issues persist:
    1. Run '$0 check' to diagnose the problem
    2. Run '$0 recover' to attempt automatic fix
    3. If that fails, try manual steps shown in recovery output
    4. Contact technical support if problems continue
    
EOF
}

# Main execution
main() {
    case "${1:-}" in
        "check")
            check_display
            ;;
        "recover")
            recover_display
            ;;
        "capture")
            capture_config
            ;;
        "service")
            show_service_status
            ;;
        "help"|"--help"|"-h")
            show_usage
            ;;
        "")
            echo "RRR Display Management Tools"
            echo "Run '$0 help' for usage information"
            echo ""
            check_display
            ;;
        *)
            echo "ERROR: Unknown command: $1"
            echo "Run '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Only run main if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi