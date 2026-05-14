# shellcheck shell=bash
# Services: install launcher to ~/.local/bin/rrr, desktop entry, and an
# optional systemd --user unit. No system-level service (GUI app).

TARGET_USER=${SUDO_USER:-$USER}
TARGET_HOME=$(getent passwd "$TARGET_USER" | cut -d: -f6)
[[ -n "$TARGET_HOME" && -d "$TARGET_HOME" ]] || die "cannot resolve home for $TARGET_USER"

BIN_DIR="$TARGET_HOME/.local/bin"
APPS_DIR="$TARGET_HOME/.local/share/applications"
UNIT_DIR="$TARGET_HOME/.config/systemd/user"

run install -d -m 0755 -o "$TARGET_USER" -g "$TARGET_USER" \
  "$BIN_DIR" "$APPS_DIR" "$UNIT_DIR"

# ---- rrr launcher ------------------------------------------------------
LAUNCHER_SRC="$REPO_ROOT/scripts/runtime/launch.sh"
LAUNCHER_DST="$BIN_DIR/rrr"
[[ -f "$LAUNCHER_SRC" ]] || die "missing $LAUNCHER_SRC"
run install -m 0755 -o "$TARGET_USER" -g "$TARGET_USER" "$LAUNCHER_SRC" "$LAUNCHER_DST"
info "installed launcher: $LAUNCHER_DST"

# ---- Desktop entry -----------------------------------------------------
DESKTOP_DST="$APPS_DIR/rrr.desktop"
write_file_atomic "$DESKTOP_DST" 0644 "$TARGET_USER:$TARGET_USER" <<EOF
[Desktop Entry]
Type=Application
Name=Rodent Refreshment Regulator
Comment=Lab automation for rodent fluid delivery
Exec=$LAUNCHER_DST
Icon=applications-science
Terminal=false
Categories=Science;Education;
EOF

# ---- Systemd --user unit (optional autostart) -------------------------
UNIT_SRC="$REPO_ROOT/scripts/systemd/rrr.service"
UNIT_DST="$UNIT_DIR/rrr.service"
[[ -f "$UNIT_SRC" ]] || die "missing $UNIT_SRC"
run install -m 0644 -o "$TARGET_USER" -g "$TARGET_USER" "$UNIT_SRC" "$UNIT_DST"
info "installed user unit: $UNIT_DST"

cat <<EOF >&2

To enable autostart on graphical login (run as $TARGET_USER, not root):
    systemctl --user daemon-reload
    systemctl --user enable --now rrr.service

For headless autostart (no graphical login), also enable lingering:
    sudo loginctl enable-linger $TARGET_USER

EOF
