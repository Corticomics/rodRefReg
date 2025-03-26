rrrinstaller@raspberrypi:~ $ wget -O setup_rrr.sh https://raw.githubusercontent.com/Corticomics/rodRefReg/main/setup_rrr.sh && chmod +x setup_rrr.sh && ./setup_rrr.sh
--2025-03-26 12:34:54--  https://raw.githubusercontent.com/Corticomics/rodRefReg/main/setup_rrr.sh
Resolving raw.githubusercontent.com (raw.githubusercontent.com)... 185.199.109.133, 185.199.110.133, 185.199.111.133, ...
Connecting to raw.githubusercontent.com (raw.githubusercontent.com)|185.199.109.133|:443... connected.
HTTP request sent, awaiting response... 200 OK
Length: 14417 (14K) [text/plain]
Saving to: ‘setup_rrr.sh’

setup_rrr.sh        100%[===================>]  14.08K  --.-KB/s    in 0.005s  

2025-03-26 12:34:54 (2.69 MB/s) - ‘setup_rrr.sh’ saved [14417/14417]

=== Rodent Refreshment Regulator Installation Script ===
This script will install all dependencies and set up your Raspberry Pi

Some installation steps require sudo privileges.
You will be prompted for your password when necessary.
=== Updating package lists ===
Hit:1 http://deb.debian.org/debian bookworm InRelease
Hit:2 http://deb.debian.org/debian-security bookworm-security InRelease
Hit:3 http://deb.debian.org/debian bookworm-updates InRelease   
Hit:4 http://archive.raspberrypi.com/debian bookworm InRelease  
Reading package lists... Done                              
=== Installing Python and pip ===
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
python3 is already the newest version (3.11.2-1+b1).
python3-pip is already the newest version (23.0.1+dfsg-1+rpt1).
python3-venv is already the newest version (3.11.2-1+b1).
The following packages were automatically installed and are no longer required:
  libcamera0.3 libwlroots12
Use 'sudo apt autoremove' to remove them.
0 upgraded, 0 newly installed, 0 to remove and 9 not upgraded.
=== Installing system dependencies ===
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
git is already the newest version (1:2.39.5-0+deb12u2).
i2c-tools is already the newest version (4.3-2+b3).
python3-smbus is already the newest version (4.3-2+b3).
python3-dev is already the newest version (3.11.2-1+b1).
python3-pyqt5 is already the newest version (5.15.9+dfsg-1).
python3-rpi.gpio is already the newest version (0.7.1~a4-1+b4).
python3-gpiozero is already the newest version (2.0.1-0+rpt1).
python3-pandas is already the newest version (1.5.3+dfsg-2).
python3-numpy is already the newest version (1:1.24.2-1+deb12u1).
build-essential is already the newest version (12.9).
The following packages were automatically installed and are no longer required:
  libcamera0.3 libwlroots12
Use 'sudo apt autoremove' to remove them.
0 upgraded, 0 newly installed, 0 to remove and 9 not upgraded.
=== Installing Sequent Microsystems 16-relay HAT driver ===
16relind-rpi repository already exists, updating...
Already up to date.
Reinstalling relay HAT driver...
[Install]
16relind command installed successfully.
Installing Python library for SM16relind...
running install
/usr/lib/python3/dist-packages/setuptools/command/install.py:34: SetuptoolsDeprecationWarning: setup.py install is deprecated. Use build and pip and other standards-based tools.
  warnings.warn(
/usr/lib/python3/dist-packages/setuptools/command/easy_install.py:146: EasyInstallDeprecationWarning: easy_install command is deprecated. Use build and pip and other standards-based tools.
  warnings.warn(
running bdist_egg
running egg_info
writing sm16relind.egg-info/PKG-INFO
writing dependency_links to sm16relind.egg-info/dependency_links.txt
writing requirements to sm16relind.egg-info/requires.txt
writing top-level names to sm16relind.egg-info/top_level.txt
reading manifest file 'sm16relind.egg-info/SOURCES.txt'
adding license file 'LICENSE'
writing manifest file 'sm16relind.egg-info/SOURCES.txt'
installing library code to build/bdist.linux-aarch64/egg
running install_lib
running build_py
creating build/bdist.linux-aarch64/egg
creating build/bdist.linux-aarch64/egg/SM16relind
copying build/lib/SM16relind/__init__.py -> build/bdist.linux-aarch64/egg/SM16relind
byte-compiling build/bdist.linux-aarch64/egg/SM16relind/__init__.py to __init__.cpython-311.pyc
creating build/bdist.linux-aarch64/egg/EGG-INFO
copying sm16relind.egg-info/PKG-INFO -> build/bdist.linux-aarch64/egg/EGG-INFO
copying sm16relind.egg-info/SOURCES.txt -> build/bdist.linux-aarch64/egg/EGG-INFO
copying sm16relind.egg-info/dependency_links.txt -> build/bdist.linux-aarch64/egg/EGG-INFO
copying sm16relind.egg-info/requires.txt -> build/bdist.linux-aarch64/egg/EGG-INFO
copying sm16relind.egg-info/top_level.txt -> build/bdist.linux-aarch64/egg/EGG-INFO
zip_safe flag not set; analyzing archive contents...
creating 'dist/sm16relind-1.0.4-py3.11.egg' and adding 'build/bdist.linux-aarch64/egg' to it
removing 'build/bdist.linux-aarch64/egg' (and everything under it)
Processing sm16relind-1.0.4-py3.11.egg
Removing /usr/local/lib/python3.11/dist-packages/sm16relind-1.0.4-py3.11.egg
Copying sm16relind-1.0.4-py3.11.egg to /usr/local/lib/python3.11/dist-packages
sm16relind 1.0.4 is already the active version in easy-install.pth

Installed /usr/local/lib/python3.11/dist-packages/sm16relind-1.0.4-py3.11.egg
Processing dependencies for sm16relind==1.0.4
Searching for smbus2==0.4.2
Best match: smbus2 0.4.2
Adding smbus2 0.4.2 to easy-install.pth file

Using /usr/lib/python3/dist-packages
Finished processing dependencies for sm16relind==1.0.4
=== Enabling I2C interface ===
I2C is already enabled in config.txt
User added to i2c group
Testing I2C functionality...
Running i2cdetect to scan for devices:
Error: Could not open file `/dev/i2c-1' or `/dev/i2c/1': No such file or directory
Note: If you just enabled I2C, you may need to reboot to see devices.
=== Setting up application directory ===
Repository already exists. Updating...
Updating baecd09..ab31ac7
error: Your local changes to the following files would be overwritten by merge:
	Project/gbg.md
	Project/rrr_database.db
Please commit your changes or stash them before you merge.
Aborting
=== Creating Python virtual environment with system packages ===
=== Creating modified requirements file ===
=== Installing Python dependencies ===
DEPRECATION: Loading egg at /usr/local/lib/python3.11/dist-packages/sm16relind-1.0.4-py3.11.egg is deprecated. pip 25.1 will enforce this behaviour change. A possible replacement is to use pip for package installation. Discussion can be found at https://github.com/pypa/pip/issues/12330
Looking in indexes: https://pypi.org/simple, https://www.piwheels.org/simple
Requirement already satisfied: pip in ./venv/lib/python3.11/site-packages (25.0.1)
WARNING: Error parsing dependencies of send2trash: Expected matching RIGHT_PARENTHESIS for LEFT_PARENTHESIS, after version specifier
    sys-platform (=="darwin") ; extra == 'objc'
                 ~^
Installing dependencies from modified requirements file...
DEPRECATION: Loading egg at /usr/local/lib/python3.11/dist-packages/sm16relind-1.0.4-py3.11.egg is deprecated. pip 25.1 will enforce this behaviour change. A possible replacement is to use pip for package installation. Discussion can be found at https://github.com/pypa/pip/issues/12330
Looking in indexes: https://pypi.org/simple, https://www.piwheels.org/simple
Requirement already satisfied: gitpython==3.1.31 in ./venv/lib/python3.11/site-packages (from -r /tmp/requirements_modified.txt (line 3)) (3.1.31)
Requirement already satisfied: requests==2.31.0 in ./venv/lib/python3.11/site-packages (from -r /tmp/requirements_modified.txt (line 6)) (2.31.0)
Requirement already satisfied: slack_sdk==3.21.3 in ./venv/lib/python3.11/site-packages (from -r /tmp/requirements_modified.txt (line 9)) (3.21.3)
Requirement already satisfied: virtualenv==20.24.3 in ./venv/lib/python3.11/site-packages (from -r /tmp/requirements_modified.txt (line 14)) (20.24.3)
Requirement already satisfied: lgpio==0.2.2.0 in /usr/lib/python3/dist-packages (from -r /tmp/requirements_modified.txt (line 17)) (0.2.2.0)
Requirement already satisfied: smbus2==0.4.1 in ./venv/lib/python3.11/site-packages (from -r /tmp/requirements_modified.txt (line 18)) (0.4.1)
Requirement already satisfied: Flask==2.2.2 in /usr/lib/python3/dist-packages (from -r /tmp/requirements_modified.txt (line 21)) (2.2.2)
Requirement already satisfied: Jinja2==3.1.2 in /usr/lib/python3/dist-packages (from -r /tmp/requirements_modified.txt (line 22)) (3.1.2)
Requirement already satisfied: jsonschema==4.23.0 in ./venv/lib/python3.11/site-packages (from -r /tmp/requirements_modified.txt (line 25)) (4.23.0)
Requirement already satisfied: attrs==24.2.0 in ./venv/lib/python3.11/site-packages (from -r /tmp/requirements_modified.txt (line 26)) (24.2.0)
Requirement already satisfied: certifi==2024.8.30 in ./venv/lib/python3.11/site-packages (from -r /tmp/requirements_modified.txt (line 29)) (2024.8.30)
Requirement already satisfied: idna==3.10 in ./venv/lib/python3.11/site-packages (from -r /tmp/requirements_modified.txt (line 30)) (3.10)
Requirement already satisfied: chardet==5.1.0 in /usr/lib/python3/dist-packages (from -r /tmp/requirements_modified.txt (line 31)) (5.1.0)
Requirement already satisfied: cryptography==38.0.4 in /usr/lib/python3/dist-packages (from -r /tmp/requirements_modified.txt (line 32)) (38.0.4)
Requirement already satisfied: matplotlib-inline==0.1.7 in ./venv/lib/python3.11/site-packages (from -r /tmp/requirements_modified.txt (line 35)) (0.1.7)
Requirement already satisfied: gitdb<5,>=4.0.1 in ./venv/lib/python3.11/site-packages (from gitpython==3.1.31->-r /tmp/requirements_modified.txt (line 3)) (4.0.12)
Requirement already satisfied: charset-normalizer<4,>=2 in /usr/lib/python3/dist-packages (from requests==2.31.0->-r /tmp/requirements_modified.txt (line 6)) (3.0.1)
Requirement already satisfied: urllib3<3,>=1.21.1 in /usr/lib/python3/dist-packages (from requests==2.31.0->-r /tmp/requirements_modified.txt (line 6)) (1.26.12)
Requirement already satisfied: distlib<1,>=0.3.7 in ./venv/lib/python3.11/site-packages (from virtualenv==20.24.3->-r /tmp/requirements_modified.txt (line 14)) (0.3.9)
Requirement already satisfied: filelock<4,>=3.12.2 in ./venv/lib/python3.11/site-packages (from virtualenv==20.24.3->-r /tmp/requirements_modified.txt (line 14)) (3.18.0)
Requirement already satisfied: platformdirs<4,>=3.9.1 in ./venv/lib/python3.11/site-packages (from virtualenv==20.24.3->-r /tmp/requirements_modified.txt (line 14)) (3.11.0)
Requirement already satisfied: jsonschema-specifications>=2023.03.6 in ./venv/lib/python3.11/site-packages (from jsonschema==4.23.0->-r /tmp/requirements_modified.txt (line 25)) (2024.10.1)
Requirement already satisfied: referencing>=0.28.4 in ./venv/lib/python3.11/site-packages (from jsonschema==4.23.0->-r /tmp/requirements_modified.txt (line 25)) (0.36.2)
Requirement already satisfied: rpds-py>=0.7.1 in ./venv/lib/python3.11/site-packages (from jsonschema==4.23.0->-r /tmp/requirements_modified.txt (line 25)) (0.24.0)
Requirement already satisfied: traitlets in ./venv/lib/python3.11/site-packages (from matplotlib-inline==0.1.7->-r /tmp/requirements_modified.txt (line 35)) (5.14.3)
Requirement already satisfied: smmap<6,>=3.0.1 in ./venv/lib/python3.11/site-packages (from gitdb<5,>=4.0.1->gitpython==3.1.31->-r /tmp/requirements_modified.txt (line 3)) (5.0.2)
Requirement already satisfied: typing-extensions>=4.4.0 in /usr/lib/python3/dist-packages (from referencing>=0.28.4->jsonschema==4.23.0->-r /tmp/requirements_modified.txt (line 25)) (4.4.0)
WARNING: Error parsing dependencies of send2trash: Expected matching RIGHT_PARENTHESIS for LEFT_PARENTHESIS, after version specifier
    sys-platform (=="darwin") ; extra == 'objc'
                 ~^
Dependencies installed successfully.
=== Verifying slack_sdk installation ===
DEPRECATION: Loading egg at /usr/local/lib/python3.11/dist-packages/sm16relind-1.0.4-py3.11.egg is deprecated. pip 25.1 will enforce this behaviour change. A possible replacement is to use pip for package installation. Discussion can be found at https://github.com/pypa/pip/issues/12330
slack_sdk is installed correctly.
=== Verifying PyQt5 is accessible ===
PyQt5 version: 5.15.9
=== Verifying RPi.GPIO is accessible ===
RPi.GPIO version: 0.7.1a4
=== Verifying pandas is accessible ===
pandas version: 1.5.3
=== Verifying SM16relind module is accessible ===
  File "<string>", line 1
    try: import SM16relind; print('SM16relind module found'); except ImportError: print('SM16relind module not found, but command line tool should work')
                                                              ^^^^^^
SyntaxError: invalid syntax
Note: SM16relind Python module not found. This is normal if the module uses command line tools instead.
=== Creating desktop shortcut ===
=== Creating startup script ===
=== Creating hardware test script ===
=== Creating diagnostic script ===
=== Creating quick fix script for missing packages ===

=== Installation complete! ===
To run the application, you can:
1. Double-click the desktop shortcut
2. Run the startup script: ~/rodent-refreshment-regulator/start_rrr.sh
3. Manually navigate to the Project directory and run: python3 main.py

If you encounter missing package errors:
Run: ~/rodent-refreshment-regulator/fix_dependencies.sh

To diagnose problems:
Run: ~/rodent-refreshment-regulator/diagnose.sh

To test hardware connectivity:
Run: ~/rodent-refreshment-regulator/test_hardware.sh

Note: A system reboot may be required for I2C changes to take effect.
Would you like to reboot now? (y/n)
n
Please remember to reboot your system later for I2C changes to take effect.
rrrinstaller@raspberrypi:~ $ wget -O setup_rrr.sh https://raw.githubusercontent.com/Corticomics/rodRefReg/main/setup_rrr.sh && chmod +x setup_rrr.sh && ./setup_rrr.sh

