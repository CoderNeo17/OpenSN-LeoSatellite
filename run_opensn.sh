#!/usr/bin/env bash
# One-shot launcher for OpenSN-LeoSatellite.
# Lives in the OpenSN-LeoSatellite repo root.
#   ./run_opensn.sh [config-file]           (default: opensn_run.conf next to this script)
#   NODE_CONFIG=... TOPO_CONFIG=... LOG_DIR=... ./run_opensn.sh    (env overrides the config file)
#
# tmux session (TMUX_LAYOUT=panes: one window, panes 0/1/2; =windows: one window each):
#   0 daemon        sudo ./NodeDaemon        (Ctrl-C stops it)
#   1 configurator  make (python main.py)    (Ctrl-C stops it)
#   2 control       shell with the "stop dependency containers" command pre-typed
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONF="${1:-$SCRIPT_DIR/opensn_run.conf}"

# Keep env overrides, then load config, then re-apply overrides
_env_node="${NODE_CONFIG:-}"; _env_topo="${TOPO_CONFIG:-}"; _env_log="${LOG_DIR:-}"
[[ -f "$CONF" ]] && source "$CONF" || { echo "Config not found: $CONF"; exit 1; }
[[ -n "$_env_node" ]] && NODE_CONFIG="$_env_node"
[[ -n "$_env_topo" ]] && TOPO_CONFIG="$_env_topo"
[[ -n "$_env_log"  ]] && LOG_DIR="$_env_log"

DAEMON_DIR="$REPO/daemon/opensn-daemon"
CONFIGURATOR_DIR="$REPO/TopoConfigurators/Standard"
S="$TMUX_SESSION"
TS="$(date +%Y%m%d_%H%M%S)"

# absolute as-is, ~/... -> $HOME/..., anything else relative to REPO
abspath() {
  case "$1" in
    /*)   echo "$1" ;;
    "~")  echo "$HOME" ;;
    "~/"*) echo "$HOME/${1#\~/}" ;;
    *)    echo "$REPO/$1" ;;
  esac
}
NODE_CONFIG="$(abspath "$NODE_CONFIG")"
TOPO_CONFIG="$(abspath "$TOPO_CONFIG")"
LOG_DIR="$(abspath "${LOG_DIR:-logs}")"
mkdir -p "$LOG_DIR" || { echo "Cannot create LOG_DIR: $LOG_DIR"; exit 1; }
[[ -w "$LOG_DIR" ]] || { echo "LOG_DIR is not writable: $LOG_DIR"; exit 1; }
LOG_DIR_Q="$(printf '%q' "$LOG_DIR")"   # shell-quoted, for commands typed into tmux

step() { echo -e "\n\033[1;36m==> $*\033[0m"; }
die()  { echo -e "\033[1;31mERROR: $*\033[0m" >&2; exit 1; }

for f in "$NODE_CONFIG" "$TOPO_CONFIG"; do
  [[ -f "$f" ]] || die "file not found: $f"
  jq empty "$f" 2>/dev/null || die "not valid JSON: $f"
done
[[ -x "$DAEMON_DIR/NodeDaemon" ]] || die "NodeDaemon not found in $DAEMON_DIR"

# ---- python environment for the configurator ----
if [[ "${USE_VENV:-no}" == "yes" ]]; then
  [[ -f "$VENV_PATH/bin/activate" ]] || die "virtual env not found: $VENV_PATH (set VENV_PATH or USE_VENV=\"no\" in $CONF)"
  PY="$VENV_PATH/bin/python3"
  PY_ACTIVATE="source '$VENV_PATH/bin/activate' && "
  echo "Configurator python: venv $VENV_PATH"
else
  PY="python3"
  PY_ACTIVATE=""
  echo "Configurator python: system $(command -v python3)"
fi
"$PY" -c 'import ephem, etcd3, loguru, requests' 2>/dev/null \
  || die "configurator packages missing in $PY (pip install -r $CONFIGURATOR_DIR/requirements.txt)"

# ---- sudo password (asked once; also fed to the NodeDaemon tmux pane) ----
step "sudo authentication"
read -rsp "[sudo] password for $USER: " SUDO_PW; echo
printf '%s\n' "$SUDO_PW" | sudo -S -p '' -v 2>/dev/null || die "wrong sudo password"

# ---- 1. kernel settings ----
step "Kernel settings"
echo 4096  | sudo tee /proc/sys/fs/inotify/max_user_instances
echo 8192  | sudo tee /proc/sys/net/ipv4/neigh/default/gc_thresh1
echo 16384 | sudo tee /proc/sys/net/ipv4/neigh/default/gc_thresh2
echo 32768 | sudo tee /proc/sys/net/ipv4/neigh/default/gc_thresh3

# ---- 2. stop previous run ----
step "Stopping previous run (tmux session '$S', NodeDaemon)"
tmux kill-session -t "$S" 2>/dev/null && echo "killed old tmux session" || true
if pgrep -x NodeDaemon >/dev/null; then
  sudo pkill -INT -x NodeDaemon || true
  for _ in $(seq 1 15); do pgrep -x NodeDaemon >/dev/null || break; sleep 1; done
  pgrep -x NodeDaemon >/dev/null && { echo "force killing NodeDaemon"; sudo pkill -KILL -x NodeDaemon || true; sleep 1; }
  echo "old NodeDaemon stopped"
else
  echo "no NodeDaemon running"
fi

# ---- 3. dependency services ----
step "Starting dependency services (log: $LOG_DIR/depend_$TS.log)"
( cd "$DAEMON_DIR" && ./scripts/start_depend_service.sh ) 2>&1 | tee "$LOG_DIR/depend_$TS.log"

# ---- 4. NodeDaemon in tmux ----
# TMUX_LAYOUT=panes   -> one window "opensn", panes 0 daemon / 1 configurator / 2 control
# TMUX_LAYOUT=windows -> separate windows daemon / configurator / control
LAYOUT="${TMUX_LAYOUT:-panes}"
[[ "$LAYOUT" == "panes" || "$LAYOUT" == "windows" ]] || die "TMUX_LAYOUT must be \"panes\" or \"windows\" (got \"$LAYOUT\")"

# new_pane <name> <dir> <pane to split after>  -> prints the new pane id
new_pane() {
  local id
  if [[ "$LAYOUT" == "panes" ]]; then
    id="$(tmux split-window -d -v -t "$3" -c "$2" -P -F '#{pane_id}')"
    tmux select-layout -t "$3" "${TMUX_PANE_LAYOUT:-even-vertical}"
  else
    id="$(tmux new-window -d -t "$S" -n "$1" -c "$2" -P -F '#{pane_id}')"
  fi
  tmux select-pane -t "$id" -T "$1"
  echo "$id"
}

step "Starting NodeDaemon in tmux ($LAYOUT, log: $LOG_DIR/nodedaemon_$TS.log)"
[[ "$LAYOUT" == "panes" ]] && WIN_NAME="opensn" || WIN_NAME="daemon"
P_DAEMON="$(tmux new-session -d -s "$S" -n "$WIN_NAME" -c "$DAEMON_DIR" -x 200 -y 60 -P -F '#{pane_id}')"
tmux select-pane -t "$P_DAEMON" -T daemon
# Pane names in the borders; keep programs from renaming them
tmux set -w -t "$P_DAEMON" pane-border-status top
tmux set -w -t "$P_DAEMON" pane-border-format " #{pane_index}: #{pane_title} "
tmux set -w -t "$P_DAEMON" allow-set-title off 2>/dev/null || true
tmux send-keys -t "$P_DAEMON" "sudo ./NodeDaemon 2>&1 | tee $LOG_DIR_Q/nodedaemon_$TS.log" Enter
# Answer the sudo prompt in the pane via a tmux buffer (password never appears on a command line)
for _ in $(seq 1 10); do
  sleep 0.5
  if tmux capture-pane -p -t "$P_DAEMON" | grep -qi 'password for'; then
    printf '%s' "$SUDO_PW" | tmux load-buffer -b pw -
    tmux paste-buffer -d -b pw -t "$P_DAEMON"
    tmux send-keys -t "$P_DAEMON" Enter
    break
  fi
done
unset SUDO_PW

echo -n "waiting for API $API_URL "
for i in $(seq 1 60); do
  curl -fs "$API_URL/emulation/" >/dev/null 2>&1 && { echo " up"; break; }
  echo -n "."; sleep 1
  [[ $i == 60 ]] && die "NodeDaemon API did not come up. Check: tmux attach -t $S"
done

# ---- 5. upload configs (same calls as the web UI buttons) ----
upload() { # $1 = endpoint, $2 = file, $3 = label
  local resp
  resp="$(curl -fsS -X POST -H 'Content-Type: application/json' --data-binary @"$2" "$API_URL/emulation/$1")" \
    || die "$3 upload failed (HTTP error)"
  [[ "$(jq -r '.code' <<<"$resp" 2>/dev/null)" == "0" ]] || die "$3 upload rejected: $resp"
  echo "$3 uploaded: $(basename "$2")"
}
step "Uploading configuration files"
upload update   "$NODE_CONFIG" "Type configuration"
upload topology "$TOPO_CONFIG" "Topology configuration"

if [[ "$AUTO_START_EMULATION" == "yes" ]]; then
  step "Starting emulation"
  curl -fsS -X POST "$API_URL/emulation/start"; echo
fi

# ---- 6. configurator in tmux ----
step "Starting configurator in tmux (log: $LOG_DIR/configurator_$TS.log)"
P_CONF="$(new_pane configurator "$CONFIGURATOR_DIR" "$P_DAEMON")"
tmux send-keys -t "$P_CONF" "${PY_ACTIVATE}make 2>&1 | tee $LOG_DIR_Q/configurator_$TS.log" Enter

# ---- 7. control pane/window ----
P_CTRL="$(new_pane control "$DAEMON_DIR" "$P_CONF")"
tmux send-keys -t "$P_CTRL" "# Stop: Ctrl-C in 'daemon' and 'configurator'; press Enter here to remove dependency containers" Enter
tmux send-keys -t "$P_CTRL" "sudo docker rm -f opensn_etcd opensn_influxdb opensn_codeserver"
tmux select-window -t "$P_DAEMON"
tmux select-pane -t "$P_DAEMON"

# ---- 8. browser ----
if [[ "$OPEN_BROWSER" == "yes" && -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]] && command -v xdg-open >/dev/null; then
  xdg-open "$UI_URL" >/dev/null 2>&1 &
fi

step "Done"
echo "Simulator UI : $UI_URL"
if [[ "$LAYOUT" == "panes" ]]; then
  echo "tmux session : tmux attach -t $S   (panes 0 daemon / 1 configurator / 2 control; Ctrl-b q then number, Ctrl-b z zoom, Ctrl-b d detach)"
else
  echo "tmux session : tmux attach -t $S   (windows: Ctrl-b n next / Ctrl-b w list, Ctrl-b d detach)"
fi
echo "Logs         : $LOG_DIR/*_$TS.log"

if [[ "$ATTACH" == "yes" && -t 1 ]]; then
  if [[ -n "${TMUX:-}" ]]; then
    tmux switch-client -t "$S"      # already inside tmux
  else
    tmux attach -t "$S"
  fi
fi
