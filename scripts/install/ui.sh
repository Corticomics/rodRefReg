# shellcheck shell=bash
# Terminal UI renderer. Sourced by lib.sh.
#
# Design:
#   - Persistent lines go to stderr (which install.sh tees into LOG_FILE).
#   - The spinner writes to /dev/tty directly, bypassing the tee — so the
#     log file contains result lines but no transient animation frames.
#   - Module logic never touches ANSI; it calls step/verify/section/etc.

[[ -n "${_RRR_UI_LOADED:-}" ]] && return 0
_RRR_UI_LOADED=1

# shellcheck source=ui.theme.sh
source "${BASH_SOURCE[0]%/*}/ui.theme.sh"

# ---- state ---------------------------------------------------------------
_UI_STEP_LABEL=
_UI_STEP_START=
_UI_SPINNER_PID=
_UI_SECTION=
declare -A _UI_COUNTS=([ok]=0 [warn]=0 [skip]=0 [fail]=0)
_UI_FAILS=()
_UI_WARNS=()

# ---- low-level helpers ---------------------------------------------------
_ui_now() { printf '%s' "${EPOCHREALTIME:-$(date +%s.%N)}"; }
_ui_elapsed() { awk -v s="$1" -v e="$2" 'BEGIN { d=e-s; if (d<0) d=0; printf "%.1f", d }'; }

_ui_tty_write() {
  [[ -n "$_UI_FD_TTY" ]] || return 0
  printf '%s' "$1" >&"$_UI_FD_TTY" 2>/dev/null || true
}

_ui_emit() {
  # $1 = styled (for the terminal), $2 = plain (for the log).
  # Rich mode: styled goes to /dev/tty, plain goes to stderr (tee'd to the
  # log) — so the log file never contains ANSI escapes.
  # Plain mode: plain goes to stderr, which tee mirrors to terminal + log.
  if [[ "$_UI_MODE" == "rich" ]]; then
    printf '%s\n' "$1" >&"$_UI_FD_TTY" 2>/dev/null || true
    printf '%s\n' "$2" >&2
  else
    printf '%s\n' "$2" >&2
  fi
}

# Section prefix for summary entries; empty when no section is active.
_ui_tag() { [[ -n "$_UI_SECTION" ]] && printf '%s: ' "$_UI_SECTION"; }

_ui_hide_cursor() { _ui_tty_write $'\e[?25l'; }
_ui_show_cursor() { _ui_tty_write $'\e[?25h'; }
_ui_clear_active() { _ui_tty_write $'\r\e[K'; }

# Spinner subshell. Killed via SIGTERM by _ui_stop_spinner.
# Sleeps before the first frame so sub-100ms steps never flash a spinner.
_ui_spinner_loop() {
  trap 'exit 0' TERM INT
  local label=$1 i=0 n=${#G_SPINNER[@]}
  while :; do
    sleep 0.1 2>/dev/null || exit 0
    printf '\r  %s%s%s  %s\e[K' "$C_OK" "${G_SPINNER[i]}" "$C_RST" "$label" >&"$_UI_FD_TTY" 2>/dev/null || exit 0
    i=$(( (i + 1) % n ))
  done
}

_ui_stop_spinner() {
  if [[ -n "$_UI_SPINNER_PID" ]]; then
    kill "$_UI_SPINNER_PID" 2>/dev/null || true
    wait "$_UI_SPINNER_PID" 2>/dev/null || true
    _UI_SPINNER_PID=
  fi
  _ui_clear_active
}

# ---- public: banner, section --------------------------------------------
ui_banner() {
  local name=${1:-Rodent Refreshment Regulator}
  local sub=${2:-installer}
  _ui_emit "${C_BOLD}${name}${C_RST} ${C_DIM}·${C_RST} ${sub}" "${name} · ${sub}"
  if [[ -n "${LOG_FILE:-}" ]]; then
    _ui_emit "${C_DIM}log: ${LOG_FILE}${C_RST}" "log: ${LOG_FILE}"
  fi
  _ui_emit "" ""
}

section() {
  _UI_SECTION=$1
  _ui_emit "" ""
  _ui_emit "${C_DIM}${G_BAR} ${1} ${G_BAR}${C_RST}" "-- ${1} --"
}

# ---- public: step lifecycle ---------------------------------------------
step_begin() {
  _UI_STEP_LABEL=$1
  _UI_STEP_START=$(_ui_now)
  if [[ "$_UI_MODE" == "rich" ]]; then
    _ui_hide_cursor
    _ui_spinner_loop "$_UI_STEP_LABEL" &
    _UI_SPINNER_PID=$!
    disown "$_UI_SPINNER_PID" 2>/dev/null || true
  else
    printf '  ..  %s\n' "$_UI_STEP_LABEL" >&2
  fi
}

_ui_finalize() {
  # $1=glyph $2=color $3=status_key $4=extra (optional)
  local glyph=$1 color=$2 status=$3 extra=${4:-}
  _ui_stop_spinner
  _ui_show_cursor
  local end el
  end=$(_ui_now)
  el=$(_ui_elapsed "${_UI_STEP_START:-$end}" "$end")
  local elstyled="" elplain=""
  if awk -v t="$el" 'BEGIN { exit !(t+0 >= 0.5) }'; then
    elstyled="  ${C_DIM}(${el}s)${C_RST}"
    elplain=" (${el}s)"
  fi
  local lab=$_UI_STEP_LABEL
  [[ -n "$extra" ]] && lab="${lab} — ${extra}"
  _ui_emit "  ${color}${glyph}${C_RST}  ${lab}${elstyled}" "  ${glyph} ${lab}${elplain}"
  _UI_COUNTS[$status]=$(( ${_UI_COUNTS[$status]:-0} + 1 ))
  _UI_STEP_LABEL=
  _UI_STEP_START=
}

step_ok()   { _ui_finalize "$G_OK"   "$C_OK"   ok   "${1:-}"; }
step_skip() { _ui_finalize "$G_SKIP" "$C_DIM"  skip "${1:-}"; }
step_warn() {
  local extra=${1:-}
  _UI_WARNS+=("$(_ui_tag)${_UI_STEP_LABEL}${extra:+ — $extra}")
  _ui_finalize "$G_WARN" "$C_WARN" warn "$extra"
}
step_fail() {
  local extra=${1:-}
  _UI_FAILS+=("$(_ui_tag)${_UI_STEP_LABEL}${extra:+ ($extra)}")
  _ui_finalize "$G_FAIL" "$C_ERR" fail "$extra"
}

# ---- public: step (command wrapper) -------------------------------------
# Usage: step "label" -- cmd args…
# Captures stdout+stderr to a tmpfile; appends to LOG_FILE; shows tail on
# failure. Honors DRY_RUN by neither animating long nor running.
step() {
  local label=$1; shift
  [[ "${1:-}" == "--" ]] && shift
  local tmp; tmp=$(mktemp)
  step_begin "$label"
  local rc=0
  if (( ${DRY_RUN:-0} )); then
    printf '[dry-run] %s\n' "$(_quote "$@" 2>/dev/null || printf '%s ' "$@")" >"$tmp"
  else
    "$@" >"$tmp" 2>&1 || rc=$?
  fi
  if [[ -n "${LOG_FILE:-}" && -s "$tmp" ]]; then
    {
      printf '\n--- output: %s ---\n' "$label"
      cat "$tmp"
      printf '--- end output ---\n'
    } >>"$LOG_FILE" 2>/dev/null || true
  fi
  if (( rc == 0 )); then
    step_ok
  else
    step_fail "exit $rc"
    if [[ -s "$tmp" ]]; then
      _ui_emit "    ${C_DIM}${G_SUB} last output:${C_RST}" "    ${G_SUB} last output:"
      local line
      while IFS= read -r line; do
        _ui_emit "      ${C_DIM}${line}${C_RST}" "      ${line}"
      done < <(tail -n 20 "$tmp")
    fi
    [[ -n "${LOG_FILE:-}" ]] && \
      _ui_emit "    ${C_DIM}${G_ARROW} see log: ${LOG_FILE}${C_RST}" \
               "    ${G_ARROW} see log: ${LOG_FILE}"
  fi
  rm -f "$tmp"
  return $rc
}

# Synchronous verification: no spinner, immediate result line.
# Usage: verify "label" -- cmd args…
verify() {
  local label=$1; shift
  [[ "${1:-}" == "--" ]] && shift
  if "$@" >/dev/null 2>&1; then
    _ui_emit "  ${C_OK}${G_OK}${C_RST}  ${label}" "  ${G_OK} ${label}"
    _UI_COUNTS[ok]=$(( ${_UI_COUNTS[ok]} + 1 ))
    return 0
  fi
  _ui_emit "  ${C_ERR}${G_FAIL}${C_RST}  ${label}" "  ${G_FAIL} ${label}"
  _UI_COUNTS[fail]=$(( ${_UI_COUNTS[fail]} + 1 ))
  _UI_FAILS+=("$(_ui_tag)${label}")
  return 1
}

# Soft check: warns on failure rather than failing. Returns 0 either way.
verify_soft() {
  local label=$1; shift
  [[ "${1:-}" == "--" ]] && shift
  if "$@" >/dev/null 2>&1; then
    _ui_emit "  ${C_OK}${G_OK}${C_RST}  ${label}" "  ${G_OK} ${label}"
    _UI_COUNTS[ok]=$(( ${_UI_COUNTS[ok]} + 1 ))
  else
    _ui_emit "  ${C_WARN}${G_WARN}${C_RST}  ${label}" "  ${G_WARN} ${label}"
    _UI_COUNTS[warn]=$(( ${_UI_COUNTS[warn]} + 1 ))
    _UI_WARNS+=("$(_ui_tag)${label}")
  fi
  return 0
}

# with_retry N delay -- cmd args…
with_retry() {
  local n=$1 delay=$2; shift 2
  [[ "${1:-}" == "--" ]] && shift
  local i=1 rc=0
  while (( i <= n )); do
    if "$@"; then return 0; fi
    rc=$?
    (( i < n )) && sleep "$delay"
    i=$(( i + 1 ))
  done
  return $rc
}

# ---- free-form lines (no step semantics) --------------------------------
ui_info() {
  _ui_emit "  ${C_DIM}${G_INFO}${C_RST}  $*" "  ${G_INFO} $*"
}
ui_warn() {
  _ui_emit "  ${C_WARN}${G_WARN}${C_RST}  $*" "  ${G_WARN} $*"
  _UI_COUNTS[warn]=$(( ${_UI_COUNTS[warn]} + 1 ))
  _UI_WARNS+=("$(_ui_tag)$*")
}
ui_err() {
  _ui_emit "  ${C_ERR}${G_FAIL}${C_RST}  $*" "  ${G_FAIL} $*"
}

# Interactive yes/no prompt. Returns 0 for yes, 1 for no.
# Reads/writes /dev/tty directly so it works even when stdout is tee'd.
# Returns 1 (no) when no interactive terminal is available.
ui_confirm() {
  local q=$1 ans=
  if [[ -n "$_UI_FD_TTY" ]]; then
    printf '  %s%s%s  %s [y/N] ' "$C_BOLD" "$G_INFO" "$C_RST" "$q" >&"$_UI_FD_TTY"
    IFS= read -r ans <&"$_UI_FD_TTY" || { printf '\n' >&"$_UI_FD_TTY"; return 1; }
  elif [[ -t 0 ]]; then
    printf '  %s %s [y/N] ' "$G_INFO" "$q" >&2
    IFS= read -r ans || return 1
  else
    return 1
  fi
  [[ "$ans" == [Yy] || "$ans" == [Yy][Ee][Ss] ]]
}

# ---- summary -------------------------------------------------------------
summary() {
  _ui_emit "" ""
  local glyph=$G_OK color=$C_OK word="complete"
  if (( ${_UI_COUNTS[fail]} > 0 )); then
    glyph=$G_FAIL; color=$C_ERR; word="failed"
  elif (( ${_UI_COUNTS[warn]} > 0 )); then
    glyph=$G_WARN; color=$C_WARN; word="complete with warnings"
  fi
  _ui_emit "${color}${glyph}${C_RST}  ${C_BOLD}install ${word}${C_RST}" "${glyph} install ${word}"
  _ui_emit "  ${C_DIM}${_UI_COUNTS[ok]} ok · ${_UI_COUNTS[warn]} warn · ${_UI_COUNTS[skip]} skip · ${_UI_COUNTS[fail]} fail${C_RST}" \
           "  ${_UI_COUNTS[ok]} ok · ${_UI_COUNTS[warn]} warn · ${_UI_COUNTS[skip]} skip · ${_UI_COUNTS[fail]} fail"
  if (( ${#_UI_FAILS[@]} > 0 )); then
    _ui_emit "  ${C_ERR}failures:${C_RST}" "  failures:"
    local f
    for f in "${_UI_FAILS[@]}"; do
      _ui_emit "    ${C_DIM}${G_SUB}${C_RST} ${f}" "    ${G_SUB} ${f}"
    done
  fi
  if (( ${#_UI_WARNS[@]} > 0 )); then
    _ui_emit "  ${C_WARN}warnings:${C_RST}" "  warnings:"
    local w
    for w in "${_UI_WARNS[@]}"; do
      _ui_emit "    ${C_DIM}${G_SUB}${C_RST} ${w}" "    ${G_SUB} ${w}"
    done
  fi
  [[ -n "${LOG_FILE:-}" ]] && \
    _ui_emit "  ${C_DIM}log: ${LOG_FILE}${C_RST}" "  log: ${LOG_FILE}"
}

# ---- cleanup on signals/exit --------------------------------------------
_ui_cleanup() {
  local rc=$?
  if [[ -n "$_UI_STEP_LABEL" ]]; then
    _ui_finalize "$G_WARN" "$C_WARN" warn "interrupted"
    _UI_FAILS+=("$(_ui_tag)interrupted")
  fi
  _ui_stop_spinner
  _ui_show_cursor
  [[ -n "$_UI_FD_TTY" ]] && { exec {_UI_FD_TTY}>&-; } 2>/dev/null || true
  return $rc
}
trap _ui_cleanup EXIT
