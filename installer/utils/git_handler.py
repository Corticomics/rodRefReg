import subprocess

def clone_repository():
    try:
        subprocess.run(["git", "clone", "https://github.com/Corticomics/rodRefReg.git"], check=True)
        return True
    except subprocess.CalledProcessError:
        return False
