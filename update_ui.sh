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
    cat > Project/update_info.json << EOF
{
    "updated": true,
    "date": "$UPDATE_DATE",
    "commit_message": "$(echo "$COMMIT_MSG" | head -n 1)",
    "previous_commit": "$CURRENT_HASH",
    "new_commit": "$REMOTE_HASH",
    "changes_summary": "The application has been updated to the latest version."
}
EOF

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