# shellcheck shell=bash
# Shared layout definitions for the blue-green install tree.
#
# Sourced by lib.sh, so every install module sees these variables — there is
# no other source of truth for the tree's paths. Never executed directly.
# See docs/UPDATE_SYSTEM.md §13.

if [[ -z "${_RRR_LAYOUT_LOADED:-}" ]]; then
_RRR_LAYOUT_LOADED=1

# Resolve the user the install is *for* — not root, when run via sudo (B1).
RRR_TARGET_USER=${SUDO_USER:-$USER}
RRR_TARGET_HOME=$(getent passwd "$RRR_TARGET_USER" 2>/dev/null | cut -d: -f6)
[[ -n "${RRR_TARGET_HOME:-}" && -d "$RRR_TARGET_HOME" ]] || RRR_TARGET_HOME=$HOME

# Blue-green tree under the target user's home (docs/UPDATE_SYSTEM.md §13.0).
RRR_HOME="$RRR_TARGET_HOME/rrr"
RRR_RELEASES="$RRR_HOME/releases"
RRR_CURRENT="$RRR_HOME/current"
RRR_SHARED="$RRR_HOME/shared"
RRR_VENV="$RRR_SHARED/venv"
RRR_DATA_DIR="$RRR_SHARED/data"
RRR_LOGS_DIR="$RRR_SHARED/logs"
RRR_BACKUPS_DIR="$RRR_SHARED/backups"
RRR_STATE="$RRR_HOME/state"

export RRR_TARGET_USER RRR_TARGET_HOME RRR_HOME RRR_RELEASES RRR_CURRENT \
       RRR_SHARED RRR_VENV RRR_DATA_DIR RRR_LOGS_DIR RRR_BACKUPS_DIR RRR_STATE

fi # _RRR_LAYOUT_LOADED
