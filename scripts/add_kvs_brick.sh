#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Avnet
#
# Adds the KVS Video Stream brick (bricks/kvs) to an Arduino App Lab app, or removes it again.
#
# Usage: add_kvs_brick.sh <app> [--creds-from <dir>] [--libs-cache <dir>]
#        add_kvs_brick.sh <app> --remove
#
#   <app>          App folder, or just the app name under /home/arduino/ArduinoApps
#   --creds-from   Where iotcDeviceConfig.json, device-cert.pem and device-pkey.pem are
#                  (default: /opt/demo, or $HOME/.iotconnect when /opt/demo has none)
#   --libs-cache   Where the downloaded KVS producer libraries are kept (default: $HOME/.cache/kvs-brick)
#   --remove       Take the brick, its libraries and the credentials out of the app again
#
# The script copies bricks/kvs into the app, lists it in app.yaml, copies the device credentials to
# <app>/data/kvs and puts the AWS KVS producer GStreamer plugin (kvssink, prebuilt for aarch64 by Avnet for the
# Tria Vision AI-KIT 6490) plus the few Debian libraries it needs into <app>/data/kvs/libs. Internet access is
# needed the first time; the downloads are cached for the next app. Then add to python/main.py, before App.run():
#
#   from kvs import KvsStream
#   kvs = KvsStream()
#
# and make sure the device template has Video Streaming enabled in /IOTCONNECT (see bricks/kvs/README.md).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRICK_SRC="$SCRIPT_DIR/../bricks/kvs"
APPS_DIR="${ARDUINO_APPS_DIR:-$HOME/ArduinoApps}"
CREDS_DIR="/opt/demo"
[[ -f "/opt/demo/iotcDeviceConfig.json" ]] || CREDS_DIR="$HOME/.iotconnect"
CACHE_DIR="${KVS_LIBS_CACHE:-$HOME/.cache/kvs-brick}"
CRED_FILES=(iotcDeviceConfig.json device-cert.pem device-pkey.pem)
BRICK_ID="kvs"
REMOVE=0
APP=""

# Prebuilt kvssink + producer libraries (aarch64) from Avnet's Tria Vision AI-KIT 6490 PutMedia demo.
KVS_PACKAGE_URL="https://raw.githubusercontent.com/avnet-iotconnect/iotc-python-lite-sdk-demos/main/tria-vision-ai-kit-6490/kvs-putmedia/package.tar.gz"
# Debian packages that provide what the App Lab container (Debian 13, GStreamer 1.26) lacks: h264parse
# (gst-plugins-bad) and the LDAP libraries the bundled libcurl links against. The pool keeps only the current
# revision, so the script looks the file name up when the pinned one is gone.
DEB_POOL="https://deb.debian.org/debian/pool/main"
DEBS=(
  "g/gst-plugins-bad1.0|gstreamer1.0-plugins-bad_1.26.2-3+deb13u3_arm64.deb|gstreamer1.0-plugins-bad_1.26"
  "g/gst-plugins-bad1.0|libgstreamer-plugins-bad1.0-0_1.26.2-3+deb13u3_arm64.deb|libgstreamer-plugins-bad1.0-0_1.26"
  "o/openldap|libldap-2.5-0_2.5.13+dfsg-5_arm64.deb|libldap-2.5-0_"
  "c/cyrus-sasl2|libsasl2-2_2.1.28+dfsg1-12_arm64.deb|libsasl2-2_"
)

usage() {
  sed -n '/^# Usage:/,/^# The script/p' "${BASH_SOURCE[0]}" | sed -e '$d' -e 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remove) REMOVE=1 ;;
    --creds-from)
      [[ $# -ge 2 ]] || { echo "--creds-from needs a folder" >&2; exit 2; }
      CREDS_DIR="$2"; shift ;;
    --libs-cache)
      [[ $# -ge 2 ]] || { echo "--libs-cache needs a folder" >&2; exit 2; }
      CACHE_DIR="$2"; shift ;;
    -h | --help) usage; exit 0 ;;
    -*) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    *) [[ -z "$APP" ]] || { echo "Only one app at a time" >&2; exit 2; }; APP="$1" ;;
  esac
  shift
done
[[ -n "$APP" ]] || { usage >&2; exit 2; }

if [[ "$APP" != */* && -d "$APPS_DIR/$APP" ]]; then
  APP_DIR="$APPS_DIR/$APP"
elif [[ -d "$APP" ]]; then
  APP_DIR="$(cd "$APP" && pwd)"
else
  echo "App folder not found: $APP (also looked in $APPS_DIR)" >&2
  exit 1
fi
echo "App: $APP_DIR"
APP_YAML="$APP_DIR/app.yaml"
[[ -f "$APP_YAML" ]] || { echo "$APP_DIR has no app.yaml - is it an App Lab app?" >&2; exit 1; }
DATA_DIR="$APP_DIR/data/kvs"

remove_from_yaml() {
  if grep -qE "^[[:space:]]*-[[:space:]]*$BRICK_ID([[:space:]]*:.*)?[[:space:]]*$" "$APP_YAML"; then
    awk -v id="$BRICK_ID" '
      { lines[NR] = $0 }
      END {
        for (i = 1; i <= NR; i++) {
          if (lines[i] ~ ("^[[:space:]]*-[[:space:]]*" id "([[:space:]]*:.*)?[[:space:]]*$")) continue
          if (lines[i] ~ /^bricks:[[:space:]]*$/) {
            empty = 1
            for (j = i + 1; j <= NR; j++) {
              if (lines[j] ~ /^[[:space:]]*-/) { if (lines[j] !~ ("^[[:space:]]*-[[:space:]]*" id "([[:space:]]*:.*)?[[:space:]]*$")) { empty = 0; break } }
              else if (lines[j] !~ /^[[:space:]]*$/) break
            }
            if (empty) { print "bricks: []"; continue }
          }
          print lines[i]
        }
      }' "$APP_YAML" > "$APP_YAML.tmp" && mv "$APP_YAML.tmp" "$APP_YAML"
    echo "Removed '- $BRICK_ID' from app.yaml"
  fi
}

if [[ $REMOVE -eq 1 ]]; then
  remove_from_yaml
  rm -rf "$APP_DIR/bricks/$BRICK_ID" && echo "Removed $APP_DIR/bricks/$BRICK_ID"
  rm -rf "$DATA_DIR" && echo "Removed $DATA_DIR (credentials and libraries)"
  rmdir "$APP_DIR/bricks" "$APP_DIR/data" 2> /dev/null || true
  echo "Done. Remove 'from kvs import KvsStream' / 'KvsStream()' from python/main.py if the app uses them, then restart the app."
  exit 0
fi

# 1. Copy the brick into the app.
[[ -f "$BRICK_SRC/brick_config.yaml" ]] || { echo "Brick source not found: $BRICK_SRC" >&2; exit 1; }
mkdir -p "$APP_DIR/bricks"
rm -rf "$APP_DIR/bricks/$BRICK_ID"
cp -r "$BRICK_SRC" "$APP_DIR/bricks/$BRICK_ID"
find "$APP_DIR/bricks/$BRICK_ID" -name "__pycache__" -type d -prune -exec rm -rf {} +
echo "Brick copied to $APP_DIR/bricks/$BRICK_ID"

# 2. List it under "bricks:" in app.yaml.
if grep -qE "^[[:space:]]*-[[:space:]]*$BRICK_ID([[:space:]]*:.*)?[[:space:]]*$" "$APP_YAML"; then
  echo "app.yaml already lists the $BRICK_ID brick"
elif grep -qE '^bricks:[[:space:]]*\[[[:space:]]*\][[:space:]]*$' "$APP_YAML"; then
  sed -i -E "s/^bricks:[[:space:]]*\[[[:space:]]*\][[:space:]]*$/bricks:\n  - $BRICK_ID/" "$APP_YAML"
  echo "Added '- $BRICK_ID' to app.yaml"
elif grep -qE '^bricks:[[:space:]]*$' "$APP_YAML"; then
  # Match the indentation of the existing list items (App Lab writes them at column 0, people often indent by 2).
  awk -v id="$BRICK_ID" '
    { lines[NR] = $0 }
    END {
      for (i = 1; i <= NR; i++) {
        print lines[i]
        if (!done && lines[i] ~ /^bricks:[[:space:]]*$/) {
          indent = "  "
          for (j = i + 1; j <= NR; j++) {
            if (lines[j] ~ /^[[:space:]]*-/) { match(lines[j], /^[[:space:]]*/); indent = substr(lines[j], 1, RLENGTH); break }
            else if (lines[j] !~ /^[[:space:]]*$/) break
          }
          print indent "- " id
          done = 1
        }
      }
    }' "$APP_YAML" > "$APP_YAML.tmp" && mv "$APP_YAML.tmp" "$APP_YAML"
  echo "Added '- $BRICK_ID' to app.yaml"
elif grep -qE '^bricks:' "$APP_YAML"; then
  echo "app.yaml has a bricks key in a form this script cannot edit: $(grep -E '^bricks:' "$APP_YAML" | head -1)" >&2
  exit 1
else
  printf '\nbricks:\n  - %s\n' "$BRICK_ID" >> "$APP_YAML"
  echo "Added a bricks section with '- $BRICK_ID' to app.yaml"
fi

# 3. Device credentials: the brick reads the device identity and kvssink authenticates with the device certificate.
mkdir -p "$DATA_DIR"
for f in "${CRED_FILES[@]}"; do
  [[ -f "$CREDS_DIR/$f" ]] || { echo "Credential file not found: $CREDS_DIR/$f (use --creds-from)" >&2; exit 1; }
  cp "$CREDS_DIR/$f" "$DATA_DIR/$f"
done
chmod 600 "$DATA_DIR/device-pkey.pem"
echo "Device credentials copied to $DATA_DIR"

# 4. KVS producer plugin + libraries (downloaded once into the cache).
fetch() { # url dest
  if command -v curl > /dev/null; then curl -fsSL --retry 3 -o "$2" "$1"; else wget -q -O "$2" "$1"; fi
}
deb_url() { # pool-dir pinned-file name-prefix -> echoes a URL that exists
  local dir="$1" pinned="$2" prefix="$3" listing latest
  if curl -fsIL --max-time 20 "$DEB_POOL/$dir/$pinned" > /dev/null 2>&1; then echo "$DEB_POOL/$dir/$pinned"; return; fi
  listing="$(curl -fsL --max-time 30 "$DEB_POOL/$dir/" 2> /dev/null || true)"
  latest="$(echo "$listing" | grep -oE "href=\"${prefix}[^\"]*_arm64\.deb\"" | sed 's/href="//; s/"//' | sort -V | tail -1)"
  [[ -n "$latest" ]] || { echo "Could not find $prefix*_arm64.deb in $DEB_POOL/$dir/" >&2; return 1; }
  echo "$DEB_POOL/$dir/$latest"
}
if [[ ! -f "$CACHE_DIR/libs/libgstkvssink.so" || ! -f "$CACHE_DIR/libs/libgstvideoparsersbad.so" ]]; then
  echo "Downloading the KVS producer libraries into $CACHE_DIR (one time)..."
  command -v dpkg-deb > /dev/null || { echo "dpkg-deb is needed to unpack the Debian packages" >&2; exit 1; }
  rm -rf "$CACHE_DIR/work"
  mkdir -p "$CACHE_DIR/work/pkg" "$CACHE_DIR/work/deb" "$CACHE_DIR/libs.new"
  fetch "$KVS_PACKAGE_URL" "$CACHE_DIR/work/package.tar.gz"
  tar -xzf "$CACHE_DIR/work/package.tar.gz" -C "$CACHE_DIR/work/pkg" ./libs
  cp -a "$CACHE_DIR/work/pkg/libs/." "$CACHE_DIR/libs.new/"
  for entry in "${DEBS[@]}"; do
    IFS='|' read -r dir pinned prefix <<< "$entry"
    url="$(deb_url "$dir" "$pinned" "$prefix")"
    echo "  $url"
    fetch "$url" "$CACHE_DIR/work/$(basename "$url")"
    dpkg-deb -x "$CACHE_DIR/work/$(basename "$url")" "$CACHE_DIR/work/deb"
  done
  LIBDIR="$CACHE_DIR/work/deb/usr/lib/aarch64-linux-gnu"
  cp -a "$LIBDIR"/libldap-2.5.so* "$LIBDIR"/liblber-2.5.so* "$LIBDIR"/libsasl2.so* "$LIBDIR"/libgstcodecparsers-1.0.so* "$CACHE_DIR/libs.new/"
  cp -a "$LIBDIR/gstreamer-1.0/libgstvideoparsersbad.so" "$CACHE_DIR/libs.new/"
  ( cd "$CACHE_DIR/libs.new" && for full in *.so.*.*.*; do [[ -f "$full" ]] || continue; soname="${full%.*.*}"; [[ -e "$soname" ]] || ln -sf "$full" "$soname"; done )
  rm -rf "$CACHE_DIR/libs"
  mv "$CACHE_DIR/libs.new" "$CACHE_DIR/libs"
  rm -rf "$CACHE_DIR/work"
  echo "Libraries ready: $(ls "$CACHE_DIR/libs" | wc -l) files"
fi
rm -rf "$DATA_DIR/libs"
cp -a "$CACHE_DIR/libs" "$DATA_DIR/libs"
rm -f "$DATA_DIR/libs/.gst-registry.bin"
echo "KVS producer libraries copied to $DATA_DIR/libs"

cat << EOF

KVS brick installed. If python/main.py does not use it yet, add before App.run():

    from kvs import KvsStream
    kvs = KvsStream()

Video Streaming must be enabled on the device's template in /IOTCONNECT (Templates -> <template> -> Settings
-> Video Streaming: Kinesis Video Stream). Then start (or restart) the app from App Lab: the stream appears on
the device's Video Streaming tab and on the App Lab Cloud Console. Reference: bricks/kvs/README.md
EOF
