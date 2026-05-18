#!/usr/bin/env bash
# RRR launcher shim — installed to ~/.local/bin/rrr by the installer.
#
# A deliberately minimal, stable entry point: it delegates to the launcher
# inside the current release, so the real launch logic can be updated by a
# release without ever touching ~/.local/bin/rrr.
# See docs/UPDATE_SYSTEM.md §13.2.
exec "${RRR_HOME:-$HOME/rrr}/current/scripts/runtime/launch.sh" "$@"
