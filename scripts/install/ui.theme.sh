# shellcheck shell=bash
# UI theme + capability detection. Sourced by ui.sh.

[[ -n "${_RRR_UI_THEME_LOADED:-}" ]] && return 0
_RRR_UI_THEME_LOADED=1

# ---- capability detection ------------------------------------------------
# Sets _UI_MODE (rich|plain), _UI_HAS_COLOR, _UI_HAS_UNICODE, _UI_FD_TTY.
_UI_MODE=plain
_UI_HAS_COLOR=0
_UI_HAS_UNICODE=0
_UI_FD_TTY=

_ui_detect_caps() {
  local force_plain=0 force_ascii=0
  [[ -n "${RRR_PLAIN:-}" ]]               && force_plain=1
  [[ -n "${NO_COLOR:-}"  ]]               && force_plain=1
  [[ -n "${CI:-}"        ]]               && force_plain=1
  [[ "${TERM:-dumb}" == "dumb" ]]         && force_plain=1
  [[ -n "${RRR_ASCII:-}" ]]               && force_ascii=1
  case "${LC_ALL:-${LANG:-}}" in
    ''|C|POSIX|C.*|POSIX.*) force_ascii=1 ;;
  esac

  if (( ! force_plain )); then
    # Open /dev/tty read-write for direct (non-tee'd) I/O: writes drive the
    # spinner, reads back interactive prompts (see ui_confirm).
    if { exec {_UI_FD_TTY}<>/dev/tty; } 2>/dev/null; then
      _UI_MODE=rich
      _UI_HAS_COLOR=1
      (( force_ascii )) || _UI_HAS_UNICODE=1
    else
      _UI_FD_TTY=
    fi
  fi
}
_ui_detect_caps

# ---- color tokens --------------------------------------------------------
if (( _UI_HAS_COLOR )); then
  C_OK=$'\e[32m'; C_WARN=$'\e[33m'; C_ERR=$'\e[31m'
  C_DIM=$'\e[2m'; C_BOLD=$'\e[1m'; C_RST=$'\e[0m'
else
  C_OK=; C_WARN=; C_ERR=; C_DIM=; C_BOLD=; C_RST=
fi

# ---- glyph set -----------------------------------------------------------
if (( _UI_HAS_UNICODE )); then
  G_OK='✓'; G_FAIL='✗'; G_WARN='!'; G_SKIP='·'; G_INFO='›'
  G_SUB='└'; G_ARROW='→'; G_BAR='──'
  G_SPINNER=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏)
else
  G_OK='[ok]'; G_FAIL='[!!]'; G_WARN='[w]'; G_SKIP='[-]'; G_INFO='>'
  G_SUB=' -'; G_ARROW='>'; G_BAR='--'
  G_SPINNER=('|' '/' '-' '\')
fi
