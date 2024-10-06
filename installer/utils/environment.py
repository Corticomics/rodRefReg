import subprocess
import os

def setup_virtualenv():
    try:
        subprocess.run(["python3", "-m", "venv", "venv"], check=True)
        subprocess.run(["venv/bin/pip", "install", "--upgrade", "pip"], check=True)
        subprocess.run(["venv/bin/pip", "install", "-r", "requirements.txt"], check=True)
        return True
    except subprocess.CalledProcessError:
        return False
