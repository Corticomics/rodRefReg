#!/bin/bash

# Rodent Refreshment Regulator - Minimal Secure Installer
# Preserves one-line installation while fixing security vulnerabilities

set -e
trap 'echo "Error at line $LINENO: $BASH_COMMAND" >&2' ERR

# === IMMEDIATE SECURITY FIX ===
# Detect real user and target directory correctly
if [ -n "$SUDO_USER" ]; then
    REAL_USER="$SUDO_USER"
    REAL_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    echo "🔐 Security: Running with sudo, installing for user: $REAL_USER"
else
    REAL_USER="$USER"
    REAL_HOME="$HOME"
fi

# Prevent root user installation
if [ "$REAL_USER" = "root" ]; then
    echo "❌ ERROR: Don't run as root user directly."
    echo "   Use your regular user account instead."
    exit 1
fi

TARGET_DIR="$REAL_HOME/rodent-refreshment-regulator"
echo "📁 Target directory: $TARGET_DIR"

# === CLEAN UP BROKEN INSTALLATION ===
echo "🧹 Cleaning up any broken installations..."
if [ -d "/root/rodent-refreshment-regulator" ]; then
    echo "   Removing broken root installation..."
    sudo rm -rf "/root/rodent-refreshment-regulator"
fi

# === SYSTEM PACKAGES (with sudo) ===
echo "📦 Installing system packages..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git i2c-tools python3-pyqt5 python3-rpi.gpio python3-pandas python3-numpy build-essential

# === APPLICATION SETUP (as user) ===
echo "⬇️  Setting up application repository..."

# Function to run as real user
run_as_user() {
    if [ "$(id -u)" -eq 0 ]; then
        sudo -u "$REAL_USER" -H "$@"
    else
        "$@"
    fi
}

# Clean repository setup
if [ -d "$TARGET_DIR" ]; then
    echo "   Found existing directory, checking state..."
    cd "$TARGET_DIR"
    if git status &>/dev/null; then
        echo "   Valid git repo, updating..."
        run_as_user git pull origin main || run_as_user git pull origin master || {
            echo "   Update failed, fresh clone..."
            cd ..
            rm -rf "$TARGET_DIR"
            run_as_user git clone https://github.com/Corticomics/rodRefReg.git "$TARGET_DIR"
        }
    else
        echo "   Not a git repo, fresh clone..."
        cd ..
        rm -rf "$TARGET_DIR"
        run_as_user git clone https://github.com/Corticomics/rodRefReg.git "$TARGET_DIR"
    fi
else
    echo "   Fresh installation..."
    run_as_user git clone https://github.com/Corticomics/rodRefReg.git "$TARGET_DIR"
fi

cd "$TARGET_DIR"

# Verify installation
if [ ! -f "Project/main.py" ]; then
    echo "❌ ERROR: Project/main.py not found after repository setup"
    exit 1
fi

echo "✅ Repository verified: Project/main.py found"

# === PYTHON ENVIRONMENT ===
echo "🐍 Setting up Python environment..."
run_as_user python3 -m venv venv --system-site-packages
run_as_user bash -c "source venv/bin/activate && pip install --upgrade pip"

# === I2C SETUP ===
echo "🔌 Configuring I2C..."
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt 2>/dev/null; then
    sudo sh -c 'echo "dtparam=i2c_arm=on" >> /boot/config.txt'
fi
sudo usermod -a -G i2c "$REAL_USER"

# === RELAY HAT DRIVER ===
echo "🔧 Installing relay HAT driver..."
TEMP_DIR="/tmp/relay-install-$$"
run_as_user git clone https://github.com/SequentMicrosystems/16relind-rpi.git "$TEMP_DIR"
cd "$TEMP_DIR"
sudo make install
cd "$TARGET_DIR"
rm -rf "$TEMP_DIR"

# === CREATE LAUNCHER ===
echo "🚀 Creating launcher..."
run_as_user cat > start_rrr.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
cd Project
python3 main.py
EOF

run_as_user chmod +x start_rrr.sh

# === FIX OWNERSHIP ===
echo "🔒 Setting correct file ownership..."
if [ "$(id -u)" -eq 0 ]; then
    chown -R "$REAL_USER:$REAL_USER" "$TARGET_DIR"
fi

# === COMPLETION ===
echo ""
echo "✅ ===== INSTALLATION COMPLETE ===== ✅"
echo ""
echo "📍 Installation location: $TARGET_DIR"
echo "👤 Installed for user: $REAL_USER"
echo ""
echo "🚀 To start the application:"
echo "   cd $TARGET_DIR"
echo "   ./start_rrr.sh"
echo ""
echo "⚠️  Reboot recommended for I2C changes"
echo "" 