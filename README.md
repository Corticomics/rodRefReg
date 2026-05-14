# Rodent Refreshment Regulator (RRR)

**A Simple Water Delivery System for Laboratory Animal Care**

![RRR System](https://github.com/user-attachments/assets/d616c02f-4deb-492b-9152-173165b6e278)

## What is the Rodent Refreshment Regulator?

The Rodent Refreshment Regulator (RRR) helps you automatically deliver precise amounts of water to laboratory animals on a schedule. It takes the guesswork out of water delivery and ensures your research animals receive consistent care.

**No programming knowledge needed!** The system has a simple, user-friendly interface designed for laboratory staff with any level of technical experience.

## Why Use the RRR System?

- ✅ **Consistent Care**: Delivers precise water amounts every time
- ✅ **Time-Saving**: Automates routine water delivery tasks
- ✅ **Animal Welfare**: Ensures animals receive proper hydration
- ✅ **Research Quality**: Improves consistency in experimental conditions
- ✅ **Remote Monitoring**: Sends alerts about system status

## Getting Started: Step-by-Step Guide

### 1. Setting Up Your System

If the system is already installed in your lab, skip to [Using the Application](#2-using-the-application). If you need to set up a new system, contact your IT support team for assistance with hardware installation.

To install the software on a new Raspberry Pi:

1. Open a terminal window on your Raspberry Pi
2. Run the following command to download and start the installation script:

```
wget -O setup_rrr.sh https://raw.githubusercontent.com/Corticomics/rodRefReg/main/setup_rrr.sh && chmod +x setup_rrr.sh && ./setup_rrr.sh
```

3. Follow the on-screen prompts to complete the installation

### 2. Using the Application

#### First-Time Login

1. Start the RRR application by clicking the desktop icon or running `./start_rrr.sh`
2. You'll see a login screen - if you don't have an account, click "Create Account" to continue
3. The main screen will appear with several tabs

#### Adding Your Animals

1. Go to the **Animals** tab
2. Click **Add Animal**
3. Enter the animal's information as requested
4. Click **Save**
5. Repeat for each animal

#### Naming Cages

1. Go to the **Cages** tab to see a visual layout of the relay board
2. Click any cage tile to assign a custom name (e.g., "Rack A — Cage 3")
3. Names sync automatically to the Wizard, Schedules, and Calibration views

#### Creating a Water Delivery Schedule

The **Schedule Wizard** walks you through schedule creation in 4 steps:

1. Go to the **Wizard** tab (or click **+ New Schedule** in the Schedules hub)
2. **Step 1 — Type**: Choose between:
   - **Instant Delivery**: All animals receive their volume at the same time; conflicting times are auto-queued
   - **Staggered Delivery**: The total volume is divided uniformly across the selected time window
3. **Step 2 — Animals**: Multi-select the animals/cages to include (limited by your hardware — typically 15 cages per HAT)
4. **Step 3 — Parameters**: Set per-animal volume, time window, and schedule name
5. **Step 4 — Review**: Confirm the configuration and click **Save Schedule**

The new schedule appears as a card in the **Schedules** hub.

#### Managing Schedules

- The **Schedules** tab is a hub that shows every schedule as a card with a search bar and multi-select for bulk delete
- Click **Edit** on any card to reopen the wizard-style editor
- Click **Info** for full schedule details

#### Starting Water Delivery

1. In the **Schedules** hub, drag a schedule card onto the **Run/Stop** drop area on the right
2. Click **Run Program**
3. The **Execution Monitor** tab appears next to the Terminal and shows live per-cage progress
4. Monitor the terminal output or the Execution Monitor cards for real-time updates


#### Stopping the Program

1. Click **Stop Program** to halt water delivery
2. The system will stop immediately

#### Unattended Operation

The RRR system is designed to run continuously even when you disconnect your display, keyboard, or mouse. For long-term experiments:

1. **Service Mode**: Enable service mode for 24/7 operation
   ```bash
   ~/rodent-refreshment-regulator/toggle_service.sh
   ```
   
2. **Power Management**: The installation automatically disables power saving features
   - HDMI sleep is disabled
   - Console blanking is turned off
   - Service keeps running even when you log out

3. **Remote Monitoring**: You can check the service status remotely via SSH
   ```bash
   ssh pi@your-pi-ip 'systemctl status rodent-regulator.service'
   ```

## Daily Use Guide

### Routine

1. **Check System Status**: Open the RRR application and verify it's running/Ran correctly
2. **Update Animal Weights**: Record new animal weights in the Animals tab
3. **Inspect Water Lines**: Check for any leaks or blockages
4. **Water Reservoir**: Ensure the water reservoir has sufficient clean water


5. **Check Delivery Log**: Review the delivery history in the terminal
6. **Verify Schedules**: Confirm schedules for the next day
7. **Backup Data** (optional): Export/Import animal data if needed

## Common Questions

### What if the system isn't delivering water?

1. Check that the **Run Program** button has been clicked
2. Verify that your time window settings are correct (is a future time if start time has passed but end time not, the system will NOT start)
3. Inspect the water tubes for air bubbles or blockages (make sure to prime the tubes and pumpos prior to first use)
4. Check that the water reservoir has enough water

### How do I know how much water each animal received?

The system keeps a log of all water deliveries. You can view this in the terminal window or export the data for your records from the database table called "logs".

### What if I need to change a schedule mid-experiment?

You can create a new schedule at any time. Stop the current program, create your new schedule, and start the program again with the new settings.

### How do I calibrate the system for accurate water delivery?

Go to **Settings → Calibration** and click **Run Calibration Wizard**. The wizard guides you through:

1. Selecting which cages to calibrate (uses the same custom names you set in the Cages tab)
2. Priming the tubing via the **Priming** sub-tab if you haven't already
3. Dispensing a measured pulse per cage and recording the actual volume
4. Saving per-cage calibration factors automatically

Calibrate before starting a new experiment and periodically to maintain accuracy. The **Priming** sub-tab in Settings can be used independently any time you swap tubing or refill the reservoir.

### How do I resolve "i2c-1 not found" or other I2C errors?

If you encounter I2C-related errors when starting the application:

1. Run the I2C troubleshooting script:
   ```bash
   ~/rodent-refreshment-regulator/fix_i2c.sh
   ```

2. This script will:
   - Check if I2C is properly enabled in your Raspberry Pi
   - Test all available I2C buses
   - Fix permissions issues
   - Run the I2C fix script that adapts to different Raspberry Pi models

3. After running the script, reboot your system if prompted:
   ```bash
   sudo reboot
   ```

Different Raspberry Pi models use different I2C bus numbering schemes. The RRR system now includes auto-detection to work with any Pi model.

## Getting Help

If you need assistance with the RRR system:

1. Click the **Help** tab in the application for detailed guides
2. Use the search bar to find specific help topics
3. Contact your laboratory manager or IT support
4. For urgent issues, contact [zepaulojr2@gmail.com](mailto:support@example.com)

## Important Safety Notes

- Always monitor the system during the first few days of a new setup
- Check animals regularly to ensure they are receiving adequate hydration and to check if the hardware setup was made correctly do not leave the subjects by themselves for the first few uses to ensure correct software and hardware setup and safety 
- Keep water lines and pumps clean to prevent contamination
- Never modify the hardware without consulting technical staff

---

**Remember**: The RRR system is designed to assist with animal care, not replace regular monitoring. Always follow your institution's animal welfare guidelines and protocols.
