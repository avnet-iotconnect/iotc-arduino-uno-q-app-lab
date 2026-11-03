#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Avnet
#
# Adds the /IOTCONNECT brick to an Arduino App Lab app on the UNO Q (or removes it again).
#
# Usage: add_iotconnect_brick.sh <app> [--direct | --relay | --auto] [--creds-from <dir>]
#        add_iotconnect_brick.sh <app> --remove
#
#   <app>          App folder, or just the app name under /home/arduino/ArduinoApps
#   --direct       Copy the device credentials into the app (data/iotconnect): the app connects on its own
#   --relay        Use the board's iotc-relay service (workshop section 4): no credentials in the app
#   --auto         Default: --relay when the iotc-relay service is running, --direct otherwise
#   --creds-from   Where the credentials are (default /opt/demo, written by scripts/credentials.sh)
#   --remove       Take the brick out of the app again and restore the classic relay client copy
#
# The script copies bricks/iotconnect into the app and lists the brick in app.yaml. An app written for the
# workshop's relay client ("from iotc_relay_client import ...", every app-configs example) gets a shim in
# python/iotc_relay_client.py and needs no code changes; any other app gets the lines to add to
# python/main.py printed. Run it again any time to update the brick copy.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRICK_SRC="$SCRIPT_DIR/../bricks/iotconnect"
APPS_DIR="${ARDUINO_APPS_DIR:-$HOME/ArduinoApps}"
CREDS_DIR="/opt/demo"
CLASSIC_CLIENT="/opt/demo/iotc_relay_client.py" # installed by scripts/unoq_setup.sh
CRED_FILES=(iotcDeviceConfig.json device-cert.pem device-pkey.pem)
SHIM_MARK="# /IOTCONNECT brick shim"
MODE="auto"
REMOVE=0
APP=""

usage() {
  sed -n '/^# Usage:/,/^# The script/p' "${BASH_SOURCE[0]}" | sed -e '$d' -e 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --direct | --relay | --auto) MODE="${1#--}" ;;
    --remove) REMOVE=1 ;;
    --creds-from)
      [[ $# -ge 2 ]] || { echo "--creds-from needs a folder" >&2; exit 2; }
      CREDS_DIR="$2"
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      [[ -z "$APP" ]] || { echo "Only one app at a time" >&2; exit 2; }
      APP="$1"
      ;;
  esac
  shift
done
[[ -n "$APP" ]] || { usage >&2; exit 2; }

if [[ "$APP" != */* && -d "$APPS_DIR/$APP" ]]; then
  APP_DIR="$APPS_DIR/$APP" # a bare name is an App Lab app, whatever the current directory holds
elif [[ -d "$APP" ]]; then
  APP_DIR="$(cd "$APP" && pwd)"
else
  echo "App folder not found: $APP (also looked in $APPS_DIR)" >&2
  exit 1
fi
echo "App: $APP_DIR"
APP_YAML="$APP_DIR/app.yaml"
[[ -f "$APP_YAML" ]] || { echo "$APP_DIR has no app.yaml - is it an App Lab app?" >&2; exit 1; }
SHIM="$APP_DIR/python/iotc_relay_client.py"
DATA_DIR="$APP_DIR/data/iotconnect"

# --remove: undo everything this script does, leaving the app as the classic README steps make it.
if [[ $REMOVE -eq 1 ]]; then
  if [[ -d "$APP_DIR/bricks/iotconnect" ]]; then
    rm -rf "${APP_DIR:?}/bricks/iotconnect"
    rmdir "$APP_DIR/bricks" 2> /dev/null || true
    echo "Removed $APP_DIR/bricks/iotconnect"
  fi
  rm -rf "${APP_DIR:?}/.cache/iotconnect"
  if grep -qE '^[[:space:]]*-[[:space:]]*iotconnect([[:space:]]*:.*)?[[:space:]]*$' "$APP_YAML"; then
    # Drop the list item with its nested lines (brick variables set in App Lab); a list left empty
    # becomes "bricks: []" so App Lab still parses the file.
    awk '
      BEGIN { skip = -1 }
      {
        match($0, /^[[:space:]]*/); ind = RLENGTH
        if (skip >= 0) {
          if ($0 ~ /^[[:space:]]*$/ || ind > skip) next # nested lines of the removed item
          skip = -1
        }
        if ($0 ~ /^[[:space:]]*-[[:space:]]*iotconnect([[:space:]]*:.*)?[[:space:]]*$/) { skip = ind; next }
        lines[++n] = $0
      }
      END {
        for (i = 1; i <= n; i++) {
          if (lines[i] ~ /^bricks:[[:space:]]*$/) {
            empty = 1
            for (j = i + 1; j <= n; j++) {
              if (lines[j] ~ /^[[:space:]]*(#|$)/) continue
              if (lines[j] ~ /^[[:space:]]*-/) empty = 0
              break
            }
            if (empty) { print "bricks: []"; continue }
          }
          print lines[i]
        }
      }' "$APP_YAML" > "$APP_YAML.tmp" && mv "$APP_YAML.tmp" "$APP_YAML"
    echo "Removed '- iotconnect' from app.yaml"
  fi
  removed=0
  for f in "${CRED_FILES[@]}"; do
    if [[ -f "$DATA_DIR/$f" ]]; then rm -f "${DATA_DIR:?}/${f:?}"; removed=1; fi
  done
  [[ $removed -eq 0 ]] || echo "Removed the device credentials from $DATA_DIR"
  rmdir "$DATA_DIR" 2> /dev/null || true
  if [[ -f "$SHIM" ]] && grep -q "$SHIM_MARK" "$SHIM"; then
    if [[ -f "$SHIM.classic.bak" ]]; then
      mv -f "$SHIM.classic.bak" "$SHIM"
      echo "Restored your relay client copy in python/ from iotc_relay_client.py.classic.bak"
    elif [[ -f "$CLASSIC_CLIENT" ]]; then
      cp "$CLASSIC_CLIENT" "$SHIM"
      echo "Restored the classic relay client in python/ from $CLASSIC_CLIENT"
    else
      rm -f "${SHIM:?}"
      echo "WARNING: $CLASSIC_CLIENT not found, so python/iotc_relay_client.py was deleted. Run scripts/unoq_setup.sh and copy it again." >&2
    fi
  fi
  for f in "$APP_DIR"/python/*.py; do
    [[ -f "$f" ]] || continue
    if grep -qE '^[[:space:]]*(from[[:space:]]+iotconnect([.[:space:]]|$)|import[[:space:]]+iotconnect([.[:space:]]|$))' "$f"; then
      echo "WARNING: python/$(basename "$f") still imports the brick directly, so the app will not start until you put the classic" >&2
      echo "  file back, e.g. cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/<example>/python/main.py $APP_DIR/python/main.py" >&2
    fi
  done
  echo "Done. Restart the app from App Lab."
  exit 0
fi

[[ -f "$BRICK_SRC/brick_config.yaml" ]] || { echo "Brick sources not found at $BRICK_SRC" >&2; exit 1; }

# 1. Copy the brick into the app.
mkdir -p "$APP_DIR/bricks"
if [[ -d "$APP_DIR/bricks/iotconnect" && "$(cd "$APP_DIR/bricks/iotconnect" && pwd -P)" == "$(cd "$BRICK_SRC" && pwd -P)" ]]; then
  echo "$APP_DIR/bricks/iotconnect resolves to the brick source itself (symlink?); refusing to replace it" >&2
  exit 1
fi
rm -rf "${APP_DIR:?}/bricks/iotconnect"
cp -R "$BRICK_SRC" "$APP_DIR/bricks/iotconnect"
find "$APP_DIR/bricks/iotconnect" -name __pycache__ -type d -prune -exec rm -rf {} +
echo "Brick copied to $APP_DIR/bricks/iotconnect"

# 2. List it under "bricks:" in app.yaml.
if grep -qE '^[[:space:]]*-[[:space:]]*iotconnect([[:space:]]*:.*)?[[:space:]]*$' "$APP_YAML"; then
  echo "app.yaml already lists the iotconnect brick"
elif grep -qE '^bricks:[[:space:]]*\[[[:space:]]*\][[:space:]]*$' "$APP_YAML"; then
  sed -i -E 's/^bricks:[[:space:]]*\[[[:space:]]*\][[:space:]]*$/bricks:\n  - iotconnect/' "$APP_YAML"
  echo "Added '- iotconnect' to app.yaml"
elif grep -qE '^bricks:[[:space:]]*$' "$APP_YAML"; then
  # Reuse the indentation of the existing list items: App Lab writes "- id", the examples "  - id".
  found="$(awk '
    /^bricks:[[:space:]]*$/ { in_list = 1; next }
    in_list && /^[[:space:]]*(#|$)/ { next }
    in_list && /^[[:space:]]*-/ { match($0, /^[[:space:]]*/); print "I:" substr($0, 1, RLENGTH); exit }
    in_list && /^[^[:space:]]/ { exit }
  ' "$APP_YAML")"
  if [[ "$found" == I:* ]]; then indent="${found#I:}"; else indent="  "; fi
  awk -v item="${indent}- iotconnect" '
    { print }
    /^bricks:[[:space:]]*$/ && !done { print item; done = 1 }
  ' "$APP_YAML" > "$APP_YAML.tmp" && mv "$APP_YAML.tmp" "$APP_YAML"
  echo "Added '- iotconnect' to app.yaml"
elif grep -qE '^bricks:' "$APP_YAML"; then
  echo "app.yaml has a bricks key in a form this script cannot edit: $(grep -E '^bricks:' "$APP_YAML" | head -1)" >&2
  echo "Add '- iotconnect' under it by hand, then run this script again." >&2
  exit 1
else
  printf '\nbricks:\n  - iotconnect\n' >> "$APP_YAML"
  echo "Added a bricks section with '- iotconnect' to app.yaml"
fi

# 3. An app written for the workshop relay client keeps its code: python/iotc_relay_client.py becomes a shim.
shim_needed=0
for f in "$APP_DIR"/python/*.py; do
  [[ -f "$f" && "$(basename "$f")" != "iotc_relay_client.py" ]] || continue
  if grep -qE '^[[:space:]]*(from[[:space:]]+iotc_relay_client[[:space:]]+import|import[[:space:]]+iotc_relay_client)' "$f"; then
    shim_needed=1
    break
  fi
done
if [[ $shim_needed -eq 1 ]]; then
  if [[ -f "$SHIM" ]] && ! grep -q "$SHIM_MARK" "$SHIM"; then
    if [[ -f "$CLASSIC_CLIENT" ]] && cmp -s "$SHIM" "$CLASSIC_CLIENT"; then
      echo "Replacing the relay client copy in python/ with the brick shim (the original stays at $CLASSIC_CLIENT)"
    else
      cp "$SHIM" "$SHIM.classic.bak"
      echo "Replacing python/iotc_relay_client.py with the brick shim (your copy is saved as iotc_relay_client.py.classic.bak)"
    fi
  fi
  cat > "$SHIM" << 'EOF'
# /IOTCONNECT brick shim - written by scripts/add_iotconnect_brick.sh.
# Keeps "from iotc_relay_client import IoTConnectRelayClient" working while the /IOTCONNECT brick does the work.
# To go back to the classic relay client: add_iotconnect_brick.sh <app> --remove
from iotconnect.compat import IoTConnectRelayClient  # noqa: F401
EOF
  echo "python/ uses the relay client API: python/iotc_relay_client.py is now the brick shim, no code changes needed"
fi

# 4. Decide how the app reaches /IOTCONNECT.
RELAY_ACTIVE=0
RELAY_ENABLED=0
if systemctl is-active --quiet iotc-relay 2> /dev/null; then RELAY_ACTIVE=1; fi
if systemctl is-enabled --quiet iotc-relay 2> /dev/null; then RELAY_ENABLED=1; fi
if [[ "$MODE" == "auto" ]]; then
  if [[ -f "$DATA_DIR/device-pkey.pem" ]]; then
    MODE="direct" # keep what an earlier run set up
  elif [[ $RELAY_ACTIVE -eq 1 ]]; then
    MODE="relay"
  else
    MODE="direct"
  fi
fi

case "$MODE" in
  direct)
    missing=0
    for f in "${CRED_FILES[@]}"; do
      [[ -f "$CREDS_DIR/$f" ]] || { echo "Missing $CREDS_DIR/$f" >&2; missing=1; }
    done
    if [[ $missing -eq 1 ]]; then
      echo "Run scripts/credentials.sh first (README section 3), or pass --creds-from <dir>." >&2
      exit 1
    fi
    mkdir -p "$DATA_DIR"
    for f in "${CRED_FILES[@]}"; do cp "$CREDS_DIR/$f" "$DATA_DIR/$f"; done
    chmod 600 "$DATA_DIR/device-pkey.pem"
    echo "Direct mode: device credentials copied to $DATA_DIR"
    echo "  They are part of the app folder now. Delete data/iotconnect before sharing or exporting the app."
    if [[ $RELAY_ACTIVE -eq 1 || $RELAY_ENABLED -eq 1 ]]; then
      echo "  WARNING: the iotc-relay service is running (or starts at boot) with the same device identity."
      echo "  Two connections for one device keep kicking each other off. Stop the relay with:"
      echo "    sudo systemctl disable --now iotc-relay"
      echo "  or re-run this script with --relay."
    fi
    ;;
  relay)
    removed=0
    for f in "${CRED_FILES[@]}"; do
      if [[ -f "$DATA_DIR/$f" ]]; then rm -f "${DATA_DIR:?}/${f:?}"; removed=1; fi
    done
    [[ $removed -eq 0 ]] || echo "Removed the device credentials from $DATA_DIR (relay mode)"
    rmdir "$DATA_DIR" 2> /dev/null || true
    echo "Relay mode: the app will use the board's iotc-relay service at tcp://172.17.0.1:8899"
    if [[ $RELAY_ACTIVE -eq 0 ]]; then
      echo "  WARNING: the iotc-relay service is not running. Install it with scripts/unoq_setup.sh"
      echo "  (README section 4) or re-run this script with --direct."
    fi
    ;;
esac

if [[ $shim_needed -eq 1 ]]; then
  cat << 'EOF'

Done. The app keeps its relay-client code; the brick now does the work. Start (or restart) the app from App Lab.
To go back to the classic relay client: add_iotconnect_brick.sh <app> --remove
EOF
else
  cat << 'EOF'

Done. In python/main.py:

    import time
    from arduino.app_utils import App
    from iotconnect import IoTConnect

    iotc = IoTConnect()
    iotc.on_command("set-led", lambda args: print("set-led", args))

    def loop():
        iotc.send_telemetry({"status": "ok"})  # the brick connects once App.run() has started
        time.sleep(5)

    App.run(user_loop=loop)

Then start (or restart) the app from App Lab. Reference: bricks/iotconnect/README.md
EOF
fi
