Ideas for RRR
- yt channel with videos setup instructions step by step
- 



   wget -O setup_rrr.sh https://raw.githubusercontent.com/Corticomics/rodRefReg/main/setup_rrr.sh && chmod +x setup_rrr.sh && ./setup_rrr.sh

Installing collected packages: pip
  Attempting uninstall: pip
    Found existing installation: pip 23.0.1
    Uninstalling pip-23.0.1:
      Successfully uninstalled pip-23.0.1
Successfully installed pip-25.0.1
Installing dependencies from modified requirements file...
Looking in indexes: https://pypi.org/simple, https://www.piwheels.org/simple
Collecting gitpython==3.1.31 (from -r /tmp/requirements_modified.txt (line 3))
  Using cached https://www.piwheels.org/simple/gitpython/GitPython-3.1.31-py3-none-any.whl (184 kB)
Collecting requests==2.31.0 (from -r /tmp/requirements_modified.txt (line 6))
  Using cached https://www.piwheels.org/simple/requests/requests-2.31.0-py3-none-any.whl (62 kB)
Collecting slack_sdk==3.21.3 (from -r /tmp/requirements_modified.txt (line 9))
  Using cached https://www.piwheels.org/simple/slack-sdk/slack_sdk-3.21.3-py3-none-any.whl (276 kB)
Collecting virtualenv==20.24.3 (from -r /tmp/requirements_modified.txt (line 14))
  Using cached https://www.piwheels.org/simple/virtualenv/virtualenv-20.24.3-py3-none-any.whl (3.0 MB)
Requirement already satisfied: lgpio==0.2.2.0 in /usr/lib/python3/dist-packages (from -r /tmp/requirements_modified.txt (line 17)) (0.2.2.0)
Collecting smbus2==0.4.1 (from -r /tmp/requirements_modified.txt (line 18))
  Using cached https://www.piwheels.org/simple/smbus2/smbus2-0.4.1-py2.py3-none-any.whl (11 kB)
Requirement already satisfied: Flask==2.2.2 in /usr/lib/python3/dist-packages (from -r /tmp/requirements_modified.txt (line 21)) (2.2.2)
Requirement already satisfied: Jinja2==3.1.2 in /usr/lib/python3/dist-packages (from -r /tmp/requirements_modified.txt (line 22)) (3.1.2)
Collecting jsonschema==4.23.0 (from -r /tmp/requirements_modified.txt (line 25))
  Using cached https://www.piwheels.org/simple/jsonschema/jsonschema-4.23.0-py3-none-any.whl (88 kB)
Collecting attrs==24.2.0 (from -r /tmp/requirements_modified.txt (line 26))
  Using cached https://www.piwheels.org/simple/attrs/attrs-24.2.0-py3-none-any.whl (63 kB)
Collecting certifi==2024.8.30 (from -r /tmp/requirements_modified.txt (line 29))
  Using cached https://www.piwheels.org/simple/certifi/certifi-2024.8.30-py3-none-any.whl (167 kB)
Collecting idna==3.10 (from -r /tmp/requirements_modified.txt (line 30))
  Using cached https://www.piwheels.org/simple/idna/idna-3.10-py3-none-any.whl (70 kB)
Requirement already satisfied: chardet==5.1.0 in /usr/lib/python3/dist-packages (from -r /tmp/requirements_modified.txt (line 31)) (5.1.0)
Requirement already satisfied: cryptography==38.0.4 in /usr/lib/python3/dist-packages (from -r /tmp/requirements_modified.txt (line 32)) (38.0.4)
Collecting matplotlib-inline==0.1.7 (from -r /tmp/requirements_modified.txt (line 35))
  Using cached https://www.piwheels.org/simple/matplotlib-inline/matplotlib_inline-0.1.7-py3-none-any.whl (9.9 kB)
Collecting gitdb<5,>=4.0.1 (from gitpython==3.1.31->-r /tmp/requirements_modified.txt (line 3))
  Using cached https://www.piwheels.org/simple/gitdb/gitdb-4.0.12-py3-none-any.whl (62 kB)
Requirement already satisfied: charset-normalizer<4,>=2 in /usr/lib/python3/dist-packages (from requests==2.31.0->-r /tmp/requirements_modified.txt (line 6)) (3.0.1)
Requirement already satisfied: urllib3<3,>=1.21.1 in /usr/lib/python3/dist-packages (from requests==2.31.0->-r /tmp/requirements_modified.txt (line 6)) (1.26.12)
Collecting distlib<1,>=0.3.7 (from virtualenv==20.24.3->-r /tmp/requirements_modified.txt (line 14))
  Using cached https://www.piwheels.org/simple/distlib/distlib-0.3.9-py2.py3-none-any.whl (468 kB)
Collecting filelock<4,>=3.12.2 (from virtualenv==20.24.3->-r /tmp/requirements_modified.txt (line 14))
  Using cached https://www.piwheels.org/simple/filelock/filelock-3.18.0-py3-none-any.whl (16 kB)
Collecting platformdirs<4,>=3.9.1 (from virtualenv==20.24.3->-r /tmp/requirements_modified.txt (line 14))
  Using cached https://www.piwheels.org/simple/platformdirs/platformdirs-3.11.0-py3-none-any.whl (17 kB)
Collecting jsonschema-specifications>=2023.03.6 (from jsonschema==4.23.0->-r /tmp/requirements_modified.txt (line 25))
  Using cached https://www.piwheels.org/simple/jsonschema-specifications/jsonschema_specifications-2024.10.1-py3-none-any.whl (18 kB)
Collecting referencing>=0.28.4 (from jsonschema==4.23.0->-r /tmp/requirements_modified.txt (line 25))
  Using cached https://www.piwheels.org/simple/referencing/referencing-0.36.2-py3-none-any.whl (26 kB)
Collecting rpds-py>=0.7.1 (from jsonschema==4.23.0->-r /tmp/requirements_modified.txt (line 25))
  Using cached rpds_py-0.24.0-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (4.1 kB)
Collecting traitlets (from matplotlib-inline==0.1.7->-r /tmp/requirements_modified.txt (line 35))
  Using cached https://www.piwheels.org/simple/traitlets/traitlets-5.14.3-py3-none-any.whl (85 kB)
Collecting smmap<6,>=3.0.1 (from gitdb<5,>=4.0.1->gitpython==3.1.31->-r /tmp/requirements_modified.txt (line 3))
  Using cached https://www.piwheels.org/simple/smmap/smmap-5.0.2-py3-none-any.whl (24 kB)
Requirement already satisfied: typing-extensions>=4.4.0 in /usr/lib/python3/dist-packages (from referencing>=0.28.4->jsonschema==4.23.0->-r /tmp/requirements_modified.txt (line 25)) (4.4.0)
Using cached rpds_py-0.24.0-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (388 kB)
WARNING: Error parsing dependencies of send2trash: Expected matching RIGHT_PARENTHESIS for LEFT_PARENTHESIS, after version specifier
    sys-platform (=="darwin") ; extra == 'objc'
                 ~^
Installing collected packages: smbus2, distlib, traitlets, smmap, slack_sdk, rpds-py, platformdirs, idna, filelock, certifi, attrs, virtualenv, requests, referencing, matplotlib-inline, gitdb, jsonschema-specifications, gitpython, jsonschema
  Attempting uninstall: smbus2
    Found existing installation: smbus2 0.4.2
    Not uninstalling smbus2 at /usr/lib/python3/dist-packages, outside environment /home/rrrinstaller/rodent-refreshment-regulator/venv
    Can't uninstall 'smbus2'. No files were found to uninstall.
  Attempting uninstall: platformdirs
    Found existing installation: platformdirs 2.6.0
    Not uninstalling platformdirs at /usr/lib/python3/dist-packages, outside environment /home/rrrinstaller/rodent-refreshment-regulator/venv
    Can't uninstall 'platformdirs'. No files were found to uninstall.
  Attempting uninstall: idna
    Found existing installation: idna 3.3
    Not uninstalling idna at /usr/lib/python3/dist-packages, outside environment /home/rrrinstaller/rodent-refreshment-regulator/venv
    Can't uninstall 'idna'. No files were found to uninstall.
  Attempting uninstall: certifi
    Found existing installation: certifi 2022.9.24
    Not uninstalling certifi at /usr/lib/python3/dist-packages, outside environment /home/rrrinstaller/rodent-refreshment-regulator/venv
    Can't uninstall 'certifi'. No files were found to uninstall.
  Attempting uninstall: attrs
    Found existing installation: attrs 22.2.0
    Not uninstalling attrs at /usr/lib/python3/dist-packages, outside environment /home/rrrinstaller/rodent-refreshment-regulator/venv
    Can't uninstall 'attrs'. No files were found to uninstall.
  Attempting uninstall: requests
    Found existing installation: requests 2.28.1
    Not uninstalling requests at /usr/lib/python3/dist-packages, outside environment /home/rrrinstaller/rodent-refreshment-regulator/venv
    Can't uninstall 'requests'. No files were found to uninstall.
  Attempting uninstall: jsonschema
    Found existing installation: jsonschema 4.10.3
    Not uninstalling jsonschema at /usr/lib/python3/dist-packages, outside environment /home/rrrinstaller/rodent-refreshment-regulator/venv
    Can't uninstall 'jsonschema'. No files were found to uninstall.
Successfully installed attrs-24.2.0 certifi-2024.8.30 distlib-0.3.9 filelock-3.18.0 gitdb-4.0.12 gitpython-3.1.31 idna-3.10 jsonschema-4.23.0 jsonschema-specifications-2024.10.1 matplotlib-inline-0.1.7 platformdirs-3.11.0 referencing-0.36.2 requests-2.31.0 rpds-py-0.24.0 slack_sdk-3.21.3 smbus2-0.4.1 smmap-5.0.2 traitlets-5.14.3 virtualenv-20.24.3
Dependencies installed successfully.
=== Verifying slack_sdk installation ===
slack_sdk is installed correctly.
=== Verifying PyQt5 is accessible ===
PyQt5 version: 5.15.9
=== Verifying RPi.GPIO is accessible ===
RPi.GPIO version: 0.7.1a4
=== Creating desktop shortcut ===
=== Creating startup script ===
=== Creating hardware test script ===

=== Installation complete! ===
To run the application, you can:
1. Double-click the desktop shortcut
2. Run the startup script: ~/rodent-refreshment-regulator/start_rrr.sh
3. Manually navigate to the Project directory and run: python3 main.py

To test hardware connectivity:
Run: ~/rodent-refreshment-regulator/test_hardware.sh

Note: A system reboot may be required for I2C changes to take effect.
Would you like to reboot now? (y/n)


