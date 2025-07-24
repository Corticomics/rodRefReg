#!/bin/bash

# RRR Secure Installation Wrapper
# This script provides a secure way to download and verify the installer

# Security settings
set -euo pipefail
IFS=$'\n\t'

# Configuration
readonly INSTALLER_URL="https://raw.githubusercontent.com/Corticomics/rodRefReg/main/install_rrr_secure.sh"
readonly EXPECTED_HEADER="# Rodent Refreshment Regulator (RRR) - Secure Installation Script"
readonly MIN_FILE_SIZE=10000
readonly TEMP_INSTALLER="/tmp/rrr_secure_installer_$$.sh"

# Cleanup function
cleanup() {
    rm -f "$TEMP_INSTALLER" 2>/dev/null || true
}
trap cleanup EXIT

echo "🔒 RRR Secure Installation Wrapper"
echo "=================================="
echo ""
echo "This wrapper provides secure download and verification of the RRR installer."
echo "It will:"
echo "  • Download the installer with integrity checks"
echo "  • Verify the installer's authenticity"
echo "  • Present the installer for your review"
echo "  • Only execute with your explicit consent"
echo ""

# Download installer
echo "📥 Downloading secure installer..."
if ! curl -fsSL "$INSTALLER_URL" -o "$TEMP_INSTALLER"; then
    echo "❌ Failed to download installer from: $INSTALLER_URL"
    exit 1
fi

# Verify file size
file_size=$(stat -f%z "$TEMP_INSTALLER" 2>/dev/null || stat -c%s "$TEMP_INSTALLER" 2>/dev/null || echo "0")
if (( file_size < MIN_FILE_SIZE )); then
    echo "❌ Downloaded file appears corrupted (size: ${file_size} bytes)"
    exit 1
fi

# Verify header
if ! grep -q "$EXPECTED_HEADER" "$TEMP_INSTALLER"; then
    echo "❌ Downloaded file does not appear to be the genuine RRR installer"
    exit 1
fi

# Check for obvious malicious patterns
malicious_patterns=('rm -rf /' 'dd if=' 'mkfs\.' '> /etc/passwd')
for pattern in "${malicious_patterns[@]}"; do
    if grep -q "$pattern" "$TEMP_INSTALLER"; then
        echo "❌ Security violation: Downloaded file contains suspicious content"
        exit 1
    fi
done

echo "✅ Installer downloaded and verified successfully"
echo ""

# Show installer info
echo "📋 Installer Information:"
echo "  • Source: $INSTALLER_URL"
echo "  • Size: ${file_size} bytes"  
echo "  • Downloaded to: $TEMP_INSTALLER"
echo ""

# Offer to show the installer
echo "🔍 Security Review Options:"
echo "  1. View installer contents before execution (recommended)"
echo "  2. Proceed with installation immediately"
echo "  3. Save installer for manual review and exit"
echo ""

read -p "Choose option (1/2/3): " -r choice

case $choice in
    1)
        echo ""
        echo "📖 Showing installer contents (press 'q' to exit viewer):"
        echo "========================================================"
        less "$TEMP_INSTALLER"
        echo ""
        read -p "Proceed with installation? (y/N): " -r proceed
        if [[ ! $proceed =~ ^[Yy]$ ]]; then
            echo "Installation cancelled by user"
            exit 0
        fi
        ;;
    2)
        echo "⚡ Proceeding with immediate installation..."
        ;;
    3)
        cp "$TEMP_INSTALLER" "./rrr_secure_installer.sh"
        chmod +x "./rrr_secure_installer.sh"
        echo "✅ Installer saved as: ./rrr_secure_installer.sh"
        echo "You can review and run it manually when ready"
        exit 0
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

# Execute installer
echo ""
echo "🚀 Launching secure installer..."
chmod +x "$TEMP_INSTALLER"
bash "$TEMP_INSTALLER" 