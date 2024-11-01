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

conelab-rrr2@raspberrypi:~/Documents/GitHub/rodRefReg/RRR_Installer $ ./dist/installer_main
Looking in indexes: https://pypi.org/simple, https://www.piwheels.org/simple
Collecting requests
  Downloading https://www.piwheels.org/simple/requests/requests-2.32.3-py3-none-any.whl (64 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 64.9/64.9 kB 207.9 kB/s eta 0:00:00
Collecting slack_sdk
  Downloading slack_sdk-3.33.3-py2.py3-none-any.whl (291 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 292.0/292.0 kB 2.8 MB/s eta 0:00:00
Collecting charset-normalizer<4,>=2
  Downloading charset_normalizer-3.4.0-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (138 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 138.2/138.2 kB 4.4 MB/s eta 0:00:00
Collecting idna<4,>=2.5
  Downloading https://www.piwheels.org/simple/idna/idna-3.10-py3-none-any.whl (70 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 70.4/70.4 kB 411.0 kB/s eta 0:00:00
Collecting urllib3<3,>=1.21.1
  Downloading https://www.piwheels.org/simple/urllib3/urllib3-2.2.3-py3-none-any.whl (126 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 126.3/126.3 kB 763.5 kB/s eta 0:00:00
Collecting certifi>=2017.4.17
  Downloading https://www.piwheels.org/simple/certifi/certifi-2024.8.30-py3-none-any.whl (167 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 167.3/167.3 kB 2.3 MB/s eta 0:00:00
Installing collected packages: urllib3, slack_sdk, idna, charset-normalizer, certifi, requests
ERROR: Could not install packages due to an OSError: [Errno 13] Permission denied: '/opt/rrr/venv/lib/python3.11/site-packages/urllib3'
Check the permissions.

remote: Enumerating objects: 8, done.
remote: Counting objects: 100% (8/8), done.
remote: Compressing objects: 100% (4/4), done.
remote: Total 8 (delta 4), reused 8 (delta 4), pack-reused 0 (from 0)
Unpacking objects: 100% (8/8), 1.85 KiB | 270.00 KiB/s, done.
From https://github.com/Corticomics/rodRefReg
   a2c2535..3192ee6  OOP-enhancement -> origin/OOP-enhancement
Already up to date.
/opt/rrr/venv/bin/python: can't open file '/opt/rrr/main.py': [Errno 2] No such file or directory


