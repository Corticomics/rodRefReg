Rodent Refreshment Regulator Installer
======================================

Thank you for choosing the Rodent Refreshment Regulator (RRR) application.

Installation Instructions:

1. **Download the Installer**

   - Download the `RRR_Installer.zip` file from the provided link.

2. **Extract the Installer**

   - Right-click the `RRR_Installer.zip` file and select "Extract Here" or "Extract to RRR_Installer/".

3. **Run the Installer**

   - Open the extracted `RRR_Installer` folder.
   - Ensure that the `installer_main` file has execute permissions:
     ```bash
     chmod +x installer_main
     ```
   - Double-click on the `RRR Installer.desktop` file.
   - If prompted with a security warning, select "Trust and Launch".

4. **Follow the Installation Steps**

   - Enter your **Slack Token** and **Channel ID** when prompted.
   - Click **"Install"** to begin the installation.
   - The installer will guide you through the process, including installing any missing dependencies.
   - You may be prompted to enter your password to authorize administrative actions.

5. **After Installation**

   - Once the installation is complete, you will receive a confirmation message.
   - The RRR application is now installed and configured.
   - Instructions on how to start and use the application are provided below.

**Starting the RRR Application**

- To start the RRR application, you can:

  - Run the application from the terminal using the command:

    ```bash
    python3 /opt/rrr/main.py
    ```

  - Or set up a desktop shortcut or menu entry if desired.

**Troubleshooting**

- **Installer Does Not Start**

  - Ensure that the `installer_main` file has execute permissions.
    - Right-click the file, select "Properties," go to the "Permissions" tab, and check "Allow executing file as program".

- **Permission Errors**

  - If you receive errors related to permissions, ensure that you are not running the installer as root.
  - The installer should be run as a normal user; it will prompt for administrative permissions when needed.

- **Missing Dependencies**

  - The installer will check for and install required dependencies automatically.
  - Ensure that your Raspberry Pi is connected to the internet during installation.

- **Network Issues**

  - If network issues occur, retry the installation after checking your connection.

**Support**

For assistance, please contact support@example.com.

Thank you!

conelab-rrr2@raspberrypi:~/Documents/GitHub/rodRefReg/RRR_Installer $ cd dist
conelab-rrr2@raspberrypi:~/Documents/GitHub/rodRefReg/RRR_Installer/dist $ ./installer_main
Hit:1 http://deb.debian.org/debian bookworm InRelease
Hit:2 http://deb.debian.org/debian-security bookworm-security InRelease
Hit:3 http://deb.debian.org/debian bookworm-updates InRelease                  
Get:4 http://archive.raspberrypi.com/debian bookworm InRelease [39.0 kB]       
Get:5 http://archive.raspberrypi.com/debian bookworm/main arm64 Packages [501 kB]
Get:6 http://archive.raspberrypi.com/debian bookworm/main armhf Packages [531 kB]
Fetched 1,072 kB in 2s (498 kB/s) 
Reading package lists... Done
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
python3-pyqt5 is already the newest version (5.15.9+dfsg-1).
python3-pyqt5 set to manually installed.
0 upgraded, 0 newly installed, 0 to remove and 13 not upgraded.
PyQt5 is still not available after installation. Exiting.
