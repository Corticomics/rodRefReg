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
2. You'll see a login screen - if you don't have an account, click "Guest Mode" to continue
3. The main screen will appear with several tabs

#### Adding Your Animals

1. Go to the **Animals** tab
2. Click **Add Animal**
3. Enter the animal's:
   - ID number
   - Name
   - Weight (in grams)
4. Click **Save**
5. Repeat for each animal

![Adding Animals](https://github.com/Corticomics/rodRefReg/assets/161750793/f99ebd3d-7b86-44a6-b370-95083e91e388)

#### Creating a Water Delivery Schedule

1. Go to the **Schedules** tab
2. Click **Create New Schedule**
3. Enter a name for your schedule
4. Choose between:
   - **Instant Delivery**: All animals get water at the same time
   - **Staggered Delivery**: Animals get water one after another
5. Set your water delivery times
6. Drag animals from the list to assign them to water pumps
7. Click **Save Schedule**

#### Starting Water Delivery

1. Select your saved schedule from the dropdown menu
2. Click **Run Program**
3. The system will begin delivering water according to your schedule
4. Monitor the terminal window for real-time updates

![Run Program](https://github.com/Corticomics/rodRefReg/assets/161750793/f99ebd3d-7b86-44a6-b370-95083e91e388)

#### Stopping the Program

1. Click **Stop Program** to halt water delivery
2. The system will complete any delivery in progress before stopping completely

## Daily Use Guide

### Morning Routine

1. **Check System Status**: Open the RRR application and verify it's running correctly
2. **Update Animal Weights**: Record new animal weights in the Animals tab
3. **Inspect Water Lines**: Check for any leaks or blockages
4. **Water Reservoir**: Ensure the water reservoir has sufficient clean water

### End of Day

1. **Check Delivery Log**: Review the delivery history in the terminal
2. **Verify Schedules**: Confirm schedules for the next day
3. **Backup Data** (optional): Export animal data if needed

## Common Questions

### What if the system isn't delivering water?

1. Check that the **Run Program** button has been clicked
2. Verify that your time window settings are correct (24-hour format)
3. Inspect the water tubes for air bubbles or blockages
4. Check that the water reservoir has enough water

### How do I know how much water each animal received?

The system keeps a log of all water deliveries. You can view this in the terminal window or export the data for your records.

### What if I need to change a schedule mid-experiment?

You can create a new schedule at any time. Stop the current program, create your new schedule, and start the program again with the new settings.

### How do I calibrate the system for accurate water delivery?

Go to the **Settings** tab and follow the calibration instructions. This should be done before starting a new experiment and periodically to ensure accuracy.

## Getting Help

If you need assistance with the RRR system:

1. Click the **Help** tab in the application for detailed guides
2. Use the search bar to find specific help topics
3. Contact your laboratory manager or IT support
4. For urgent issues, contact [support@example.com](mailto:support@example.com)

## Important Safety Notes

- Always monitor the system during the first few days of a new setup
- Check animals regularly to ensure they are receiving adequate hydration
- Keep water lines and pumps clean to prevent contamination
- Never modify the hardware without consulting technical staff

---

**Remember**: The RRR system is designed to assist with animal care, not replace regular monitoring. Always follow your institution's animal welfare guidelines and protocols.
