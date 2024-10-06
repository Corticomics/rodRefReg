import shutil
import subprocess

def check_dependencies():
    missing = []
    if not shutil.which("pip3"):
        missing.append("pip3")
    if not shutil.which("git"):
        missing.append("git")
    return missing

def install_dependencies(dependencies):
    try:
        for dep in dependencies:
            subprocess.run(["sudo", "apt", "install", "-y", dep], check=True)
        return True
    except subprocess.CalledProcessError:
        return False
