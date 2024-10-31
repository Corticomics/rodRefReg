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

(venv) conelab-rrr2@raspberrypi:~/Documents/GitHub/rodRefReg/RRR_Installer $ pip install pyqt5
Looking in indexes: https://pypi.org/simple, https://www.piwheels.org/simple
WARNING: Retrying (Retry(total=4, connect=None, read=None, redirect=None, status=None)) after connection broken by 'SSLError(SSLZeroReturnError(6, 'TLS/SSL connection has been closed (EOF) (_ssl.c:992)'))': /simple/pyqt5/
Collecting pyqt5
  Downloading PyQt5-5.15.11.tar.gz (3.2 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.2/3.2 MB 9.1 MB/s eta 0:00:00
  Installing build dependencies ... done
  Getting requirements to build wheel ... done
  Preparing metadata (pyproject.toml) ... error
  error: subprocess-exited-with-error
  
  × Preparing metadata (pyproject.toml) did not run successfully.
  │ exit code: 1
  ╰─> [25 lines of output]
      Traceback (most recent call last):
        File "/home/conelab-rrr2/Documents/GitHub/rodRefReg/RRR_Installer/venv/lib/python3.11/site-packages/pip/_vendor/pyproject_hooks/_in_process/_in_process.py", line 353, in <module>
          main()
        File "/home/conelab-rrr2/Documents/GitHub/rodRefReg/RRR_Installer/venv/lib/python3.11/site-packages/pip/_vendor/pyproject_hooks/_in_process/_in_process.py", line 335, in main
          json_out['return_val'] = hook(**hook_input['kwargs'])
                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        File "/home/conelab-rrr2/Documents/GitHub/rodRefReg/RRR_Installer/venv/lib/python3.11/site-packages/pip/_vendor/pyproject_hooks/_in_process/_in_process.py", line 152, in prepare_metadata_for_build_wheel
          whl_basename = backend.build_wheel(metadata_directory, config_settings)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        File "/tmp/pip-build-env-s_ycucdc/overlay/lib/python3.11/site-packages/sipbuild/api.py", line 28, in build_wheel
          project = AbstractProject.bootstrap('wheel',
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        File "/tmp/pip-build-env-s_ycucdc/overlay/lib/python3.11/site-packages/sipbuild/abstract_project.py", line 74, in bootstrap
          project.setup(pyproject, tool, tool_description)
        File "/tmp/pip-build-env-s_ycucdc/overlay/lib/python3.11/site-packages/sipbuild/project.py", line 608, in setup
          self.apply_user_defaults(tool)
        File "/tmp/pip-install-24e5byvm/pyqt5_c9538dd606fe4cce97a1af1df9d6c61d/project.py", line 68, in apply_user_defaults
          super().apply_user_defaults(tool)
        File "/tmp/pip-build-env-s_ycucdc/overlay/lib/python3.11/site-packages/pyqtbuild/project.py", line 51, in apply_user_defaults
          super().apply_user_defaults(tool)
        File "/tmp/pip-build-env-s_ycucdc/overlay/lib/python3.11/site-packages/sipbuild/project.py", line 237, in apply_user_defaults
          self.builder.apply_user_defaults(tool)
        File "/tmp/pip-build-env-s_ycucdc/overlay/lib/python3.11/site-packages/pyqtbuild/builder.py", line 50, in apply_user_defaults
          raise PyProjectOptionException('qmake',
      sipbuild.pyproject.PyProjectOptionException
      [end of output]
  
  note: This error originates from a subprocess, and is likely not a problem with pip.
error: metadata-generation-failed

× Encountered error while generating package metadata.
╰─> See above for output.

note: This is an issue with the package mentioned above, not pip.
hint: See above for details.

