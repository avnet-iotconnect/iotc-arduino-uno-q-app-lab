#!/usr/bin/env bash
set -euo pipefail

DEMO_DIR="/home/arduino/demo"

RELAY_SERVER_URL="https://raw.githubusercontent.com/avnet-iotconnect/iotc-relay-service/main/relay-server/iotc-relay-server.py"
RELAY_CLIENT_URL="https://raw.githubusercontent.com/avnet-iotconnect/iotc-relay-service/main/client-module/python/iotc_relay_client.py"

if [[ "$EUID" -ne 0 ]]; then
  echo "Please run as root (sudo)."
  exit 1
fi

RUN_USER="${SUDO_USER:-$USER}"

if [[ "$SKIP_APT" == "0" ]]; then
  apt-get update
  apt-get install -y python3-pip
fi

mkdir -p /home/arduino/demo

# Some relay server builds expect /home/weston/demo by default. Provide a compatibility symlink.
if [[ "$DEMO_DIR" != "/home/weston/demo" ]]; then
  if [[ ! -e "/home/weston" ]]; then
    mkdir -p /home/weston
  fi
  if [[ -L "/home/weston/demo" ]]; then
    true
  elif [[ -e "/home/weston/demo" ]]; then
    true
  else
    ln -s "$DEMO_DIR" /home/weston/demo
    echo "Created symlink: /home/weston/demo -> $DEMO_DIR"
  fi
fi

if command -v curl >/dev/null 2>&1; then
  DL_CMD=(curl -fsSL)
elif command -v wget >/dev/null 2>&1; then
  DL_CMD=(wget -qO-)
else
  echo "Need curl or wget installed."
  exit 1
fi

fetch_file() {
  local url="$1"
  local dest="$2"
  echo "Downloading $url -> $dest"
  "${DL_CMD[@]}" "$url" > "$dest"
}

if [[ ! -f "$DEMO_DIR/iotc-relay-server.py" ]]; then
  fetch_file "$RELAY_SERVER_URL" "$DEMO_DIR/iotc-relay-server.py"
fi

if [[ ! -f "$DEMO_DIR/iotc_relay_client.py" ]]; then
  fetch_file "$RELAY_CLIENT_URL" "$DEMO_DIR/iotc_relay_client.py"
fi

# Install the relay client into site-packages so every App Lab app can
# "from iotc_relay_client import ..." without needing a local copy.
SITE_PACKAGES="$(python3 -c 'import site; print(site.getsitepackages()[0])')"
cp "$DEMO_DIR/iotc_relay_client.py" "$SITE_PACKAGES/iotc_relay_client.py"
echo "Installed iotc_relay_client.py -> $SITE_PACKAGES"

chmod +x "$DEMO_DIR/iotc-relay-server.py"

set +e
python3 -m pip install --upgrade pip
python3 -m pip install --break-system-packages iotconnect-sdk-lite
set -e

cat > /etc/systemd/system/iotc-relay.service <<EOF
[Unit]
Description=IoTConnect Relay Server
After=network.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$DEMO_DIR
ExecStart=/usr/bin/python3 $DEMO_DIR/iotc-relay-server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now iotc-relay.service

echo "Setup complete."
echo "Demo dir: $DEMO_DIR"
if [[ "$NO_SYSTEMD" == "1" ]]; then
  echo "Start manually:"
  echo "  python3 $DEMO_DIR/iotc-relay-server.py"
fi