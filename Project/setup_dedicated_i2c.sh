#!/bin/bash

# RRR Dedicated I2C Bus Setup for Production
# This script configures I2C bus 3 on GPIO 12/13 for the flow sensor

echo "=== RRR Production I2C Bus Setup ==="
echo "Setting up dedicated I2C bus 3 for SLF3S-0600F flow sensor"
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/cpuinfo ] || ! grep -q "Raspberry Pi" /proc/cpuinfo; then
    echo "Warning: This script is designed for Raspberry Pi hardware"
    exit 1
fi

# Backup config.txt
echo "Backing up /boot/firmware/config.txt..."
sudo cp /boot/firmware/config.txt /boot/firmware/config.txt.rrr_backup

# Check if overlay is already enabled
if grep -q "dtoverlay=i2c3,pins_12_13" /boot/firmware/config.txt; then
    echo "✓ I2C bus 3 overlay already enabled"
else
    echo "Adding I2C bus 3 overlay to /boot/firmware/config.txt..."
    echo "" | sudo tee -a /boot/firmware/config.txt
    echo "# RRR Flow Sensor - Dedicated I2C Bus 3 (GPIO 12/13)" | sudo tee -a /boot/firmware/config.txt
    echo "dtoverlay=i2c3,pins_12_13" | sudo tee -a /boot/firmware/config.txt
    echo "✓ I2C bus 3 overlay added"
fi

# Update RRR settings to use bus 3
echo "Updating RRR settings for dedicated I2C bus..."
if [ -f "settings.json" ]; then
    # Backup settings
    cp settings.json settings.json.backup
    
    # Update i2c_bus setting using Python
    python3 << 'EOF'
import json
try:
    with open('settings.json', 'r') as f:
        settings = json.load(f)
    
    settings['i2c_bus'] = 3
    print(f"Updated i2c_bus from {settings.get('i2c_bus', 'unknown')} to 3")
    
    with open('settings.json', 'w') as f:
        json.dump(settings, f, indent=4)
    
    print("✓ Settings updated successfully")
except Exception as e:
    print(f"✗ Error updating settings: {e}")
EOF
else
    echo "Settings file not found, will be created on first app launch"
fi

echo ""
echo "=== Wiring Instructions ==="
echo "Connect your SLF3S-0600F flow sensor to these Pi pins:"
echo ""
echo "SLF3S-0600F    →  Raspberry Pi 5"
echo "─────────────────────────────────────"
echo "VDD (3.3V)     →  Pin 17 (3.3V Power)"
echo "GND            →  Pin 20 (Ground)"
echo "SDA            →  Pin 32 (GPIO 12)"
echo "SCL            →  Pin 33 (GPIO 13)"
echo ""
echo "Leave your relay HAT connected to pins 3/5 (I2C bus 1)"
echo ""

echo "=== Next Steps ==="
echo "1. Reboot your Pi: sudo reboot"
echo "2. After reboot, verify I2C bus 3 exists: ls /dev/i2c-*"
echo "3. Test sensor detection: sudo i2cdetect -y 3"
echo "4. Run RRR and test delivery schedule"
echo ""

echo "Need to reboot for I2C overlay to take effect."
echo "Reboot now? (y/n)"
read choice
if [[ $choice == "y" || $choice == "Y" ]]; then
    echo "Rebooting..."
    sudo reboot
else
    echo "Please reboot manually when ready: sudo reboot"
fi
