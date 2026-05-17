# shellcheck shell=bash
# Services: install launcher to ~/.local/bin/rrr, desktop entry, and an
# optional systemd --user unit. No system-level service (GUI app).

TARGET_USER=${SUDO_USER:-$USER}
TARGET_HOME=$(getent passwd "$TARGET_USER" | cut -d: -f6)
[[ -n "$TARGET_HOME" && -d "$TARGET_HOME" ]] || die "cannot resolve home for $TARGET_USER"

BIN_DIR="$TARGET_HOME/.local/bin"
APPS_DIR="$TARGET_HOME/.local/share/applications"
UNIT_DIR="$TARGET_HOME/.config/systemd/user"
# Localized "Desktop" folder name varies by locale; honor the user's setting.
DESKTOP_DIR=$(
  sudo -u "$TARGET_USER" -- xdg-user-dir DESKTOP 2>/dev/null \
    || echo "$TARGET_HOME/Desktop"
)

run install -d -m 0755 -o "$TARGET_USER" -g "$TARGET_USER" \
  "$BIN_DIR" "$APPS_DIR" "$UNIT_DIR" "$DESKTOP_DIR"

# ---- rrr launcher ------------------------------------------------------
LAUNCHER_SRC="$REPO_ROOT/scripts/runtime/launch.sh"
LAUNCHER_DST="$BIN_DIR/rrr"
[[ -f "$LAUNCHER_SRC" ]] || die "missing $LAUNCHER_SRC"
run install -m 0755 -o "$TARGET_USER" -g "$TARGET_USER" "$LAUNCHER_SRC" "$LAUNCHER_DST"
info "installed launcher: $LAUNCHER_DST"

# ---- Desktop entry -----------------------------------------------------
# Menu entry under Applications.
APPS_DST="$APPS_DIR/rrr.desktop"
write_file_atomic "$APPS_DST" 0644 "$TARGET_USER:$TARGET_USER" <<EOF
[Desktop Entry]
Type=Application
Name=Rodent Refreshment Regulator
Comment=Lab automation for rodent fluid delivery
Exec=$LAUNCHER_DST
Icon=applications-science
Terminal=false
Categories=Science;Education;
EOF

# Icon on the desktop itself. On Pi OS Bookworm (Wayfire/PCManFM) the file
# must be executable; some file managers also require the GIO "trusted"
# metadata flag. Set both; ignore failures (gio may be absent on some setups).
DESKTOP_DST="$DESKTOP_DIR/rrr.desktop"
run install -m 0755 -o "$TARGET_USER" -g "$TARGET_USER" "$APPS_DST" "$DESKTOP_DST"
run sudo -u "$TARGET_USER" -- \
  gio set -t string "$DESKTOP_DST" metadata::trusted true 2>/dev/null || true
info "installed desktop icon: $DESKTOP_DST"

# ---- Systemd --user unit (optional autostart) -------------------------
UNIT_SRC="$REPO_ROOT/scripts/systemd/rrr.service"
UNIT_DST="$UNIT_DIR/rrr.service"
[[ -f "$UNIT_SRC" ]] || die "missing $UNIT_SRC"
run install -m 0644 -o "$TARGET_USER" -g "$TARGET_USER" "$UNIT_SRC" "$UNIT_DST"
info "installed user unit: $UNIT_DST"

info "autostart on graphical login (run as $TARGET_USER, not root):"
info "    systemctl --user daemon-reload && systemctl --user enable --now rrr.service"
info "headless autostart also needs lingering:"
info "    sudo loginctl enable-linger $TARGET_USER"
