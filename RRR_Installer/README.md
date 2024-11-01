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
  Using cached https://www.piwheels.org/simple/requests/requests-2.32.3-py3-none-any.whl (64 kB)
Collecting slack_sdk
  Using cached slack_sdk-3.33.3-py2.py3-none-any.whl (291 kB)
Collecting charset-normalizer<4,>=2
  Using cached charset_normalizer-3.4.0-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (138 kB)
Collecting idna<4,>=2.5
  Using cached https://www.piwheels.org/simple/idna/idna-3.10-py3-none-any.whl (70 kB)
Collecting urllib3<3,>=1.21.1
  Using cached https://www.piwheels.org/simple/urllib3/urllib3-2.2.3-py3-none-any.whl (126 kB)
Collecting certifi>=2017.4.17
  Using cached https://www.piwheels.org/simple/certifi/certifi-2024.8.30-py3-none-any.whl (167 kB)
Installing collected packages: urllib3, slack_sdk, idna, charset-normalizer, certifi, requests
Successfully installed certifi-2024.8.30 charset-normalizer-3.4.0 idna-3.10 requests-2.32.3 slack_sdk-3.33.3 urllib3-2.2.3
Cloning into '/home/conelab-rrr2/.rrr/rrr_app'...
remote: Enumerating objects: 11812, done.
remote: Counting objects: 100% (200/200), done.
remote: Compressing objects: 100% (130/130), done.
remote: Total 11812 (delta 122), reused 133 (delta 67), pack-reused 11612 (from 1)
Receiving objects: 100% (11812/11812), 118.53 MiB | 15.03 MiB/s, done.
Resolving deltas: 100% (5263/5263), done.
Updating files: 100% (8867/8867), done.
/home/conelab-rrr2/.rrr/venv/bin/python: can't open file '/home/conelab-rrr2/.rrr/rrr_app/main.py': [Errno 2] No such file or directory
