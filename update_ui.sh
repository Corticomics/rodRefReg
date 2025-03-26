#!/bin/bash

# UI Update Script for Rodent Refreshment Regulator
# This script checks for UI updates and applies them automatically

echo "=== Checking for UI Updates ==="

# Navigate to app directory
cd ~/rodent-refreshment-regulator

# Current git branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Current branch: $BRANCH"

# Store current git hash
CURRENT_HASH=$(git rev-parse HEAD)
echo "Current commit: $CURRENT_HASH"

# Attempt to update from repository without changing local database
echo "Fetching latest updates..."
git fetch origin $BRANCH

# Get remote hash
REMOTE_HASH=$(git rev-parse origin/$BRANCH)
echo "Latest remote commit: $REMOTE_HASH"

# Compare hashes to see if an update is available
if [ "$CURRENT_HASH" == "$REMOTE_HASH" ]; then
    echo "UI is already up to date."
else
    echo "Updates available. Backing up important files..."
    
    # Backup database file if it exists
    if [ -f "Project/rrr_database.db" ]; then
        echo "Backing up database..."
        cp Project/rrr_database.db Project/rrr_database.db.bak
    fi

    # Backup settings if they exist
    if [ -f "Project/settings.json" ]; then
        echo "Backing up settings..."
        cp Project/settings.json Project/settings.json.bak
    fi
    
    # Stash any local changes (should be rare, but just in case)
    git stash

    # Pull the latest updates, focusing on UI files and keeping database intact
    echo "Applying UI updates..."
    # Use sparse-checkout to only update UI files
    git config core.sparseCheckout true
    echo "Project/ui/" > .git/info/sparse-checkout
    git checkout origin/$BRANCH -- Project/ui/
    
    echo "UI files updated successfully!"
    
    # Restore any backed up files if they were overwritten
    if [ -f "Project/rrr_database.db.bak" ]; then
        echo "Restoring database..."
        mv Project/rrr_database.db.bak Project/rrr_database.db
    fi
    
    if [ -f "Project/settings.json.bak" ]; then
        echo "Restoring settings..."
        mv Project/settings.json.bak Project/settings.json
    fi
    
    # Disable sparse checkout
    git config core.sparseCheckout false
    
    # Create update notification for the app
    echo "Creating update notification..."
    UPDATE_DATE=$(date "+%Y-%m-%d %H:%M:%S")
    cat > Project/ui_updated.json << EOF
{
    "updated": true,
    "date": "$UPDATE_DATE",
    "changes": [
        "Reduced calendar widget size in Schedules tab",
        "Improved layout of relay unit widgets",
        "Fixed animal table display to show all data",
        "Made UI more compact and user-friendly"
    ],
    "previous_commit": "$CURRENT_HASH",
    "new_commit": "$REMOTE_HASH"
}
EOF
    echo "Update notification created. User will be informed on next launch."
fi

echo "UI update check complete." 