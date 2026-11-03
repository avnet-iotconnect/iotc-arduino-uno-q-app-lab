# SPDX-FileCopyrightText: Copyright (C) Arduino s.r.l. and/or its affiliated companies
#
# SPDX-License-Identifier: MPL-2.0

import json
import secrets
import string
import time
from collections import deque
from threading import Lock

from arduino.app_utils import App
from arduino.app_bricks.web_ui import WebUI
from arduino.app_peripherals.remote_sensor import RemoteSensor

# ---- IOTCONNECT Relay ----
from iotc_relay_client import IoTConnectRelayClient

RELAY_ENDPOINT = "tcp://172.17.0.1:8899"
RELAY_CLIENT_ID = "mobile_remote_sensor"
UNOQ_DEMO_NAME = "mobile-remote-sensor"
IOTC_INTERVAL_SEC = 2
IOTC_LAST_SEND = 0.0
SENSOR_STATUS = "disconnected"
SENSOR_JSON_MAX_CHARS = 2000


def generate_secret() -> str:
    characters = string.digits
    return ''.join(secrets.choice(characters) for _ in range(6))


secret = generate_secret()

ui = WebUI()  # set use_tls=True to enable TLS encryption for HTTPS
sensor = RemoteSensor(secret=secret)  # WebSocket server on port 8090, HMAC-authenticated with the secret

# Keep the most recent datapoints so a browser opened mid-stream catches up instantly.
HISTORY_MAX = 200
history: deque = deque(maxlen=HISTORY_MAX)
history_lock = Lock()

relay = IoTConnectRelayClient(
    RELAY_ENDPOINT,
    client_id=RELAY_CLIENT_ID,
)
relay.start()


def on_relay_command(command_name, parameters):
    global IOTC_INTERVAL_SEC
    print(f"IOTCONNECT command: {command_name} {parameters}")
    if command_name == "set-interval":
        try:
            if isinstance(parameters, dict):
                IOTC_INTERVAL_SEC = int(parameters.get("seconds", IOTC_INTERVAL_SEC))
            else:
                IOTC_INTERVAL_SEC = int(str(parameters).strip())
            print(f"IOTCONNECT interval set to {IOTC_INTERVAL_SEC}s")
        except Exception as e:
            print(f"IOTCONNECT interval update failed: {e}")


relay.command_callback = on_relay_command


def _num(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _gps(data: dict):
    gps = data.get("gps")
    if not isinstance(gps, dict):
        return 0.0, 0.0
    lat = gps.get("lat", gps.get("latitude", 0.0))
    lon = gps.get("lng", gps.get("lon", gps.get("longitude", 0.0)))
    return _num(lat), _num(lon)


def build_payload(data: dict, status="ok") -> dict:
    # Datapoint keys are the ones the Arduino IoT Remote app streams
    # (see assets/app.js in the upstream example).
    lat, lon = _gps(data)
    return {
        "UnoQdemo": UNOQ_DEMO_NAME,
        "interval_sec": int(IOTC_INTERVAL_SEC),
        "state": SENSOR_STATUS,
        "x": _num(data.get("accelerometerX")),
        "y": _num(data.get("accelerometerY")),
        "z": _num(data.get("accelerometerZ")),
        "gyro_x": _num(data.get("gyroscopeX")),
        "gyro_y": _num(data.get("gyroscopeY")),
        "gyro_z": _num(data.get("gyroscopeZ")),
        "mag_x": _num(data.get("magnetometerX")),
        "mag_y": _num(data.get("magnetometerY")),
        "mag_z": _num(data.get("magnetometerZ")),
        "compass": _num(data.get("compass")),
        "barometer": _num(data.get("barometer")),
        "brightness": _num(data.get("brightness")),
        "battery": _num(data.get("battery")),
        "sound_level": _num(data.get("soundLevel")),
        "sound_pitch": _num(data.get("soundPitch")),
        "lat": lat,
        "lon": lon,
        "sensor_json": json.dumps(data)[:SENSOR_JSON_MAX_CHARS],
        "status": status,
    }


def send_telemetry(data: dict, status="ok", force=False):
    global IOTC_LAST_SEND
    now = time.time()
    if not force and now - IOTC_LAST_SEND < IOTC_INTERVAL_SEC:
        return
    IOTC_LAST_SEND = now
    payload = build_payload(data, status)
    print("IOTCONNECT send:", payload)
    relay.send_telemetry(payload)


def pairing_payload() -> dict:
    return {
        "secret": secret,
        "status": sensor.status,
        "ip": sensor.ip,
        "port": sensor.port,
        "protocol": sensor.protocol,
    }


def on_ui_connect(sid):
    # Send connection details to the newly connected client only, so it can
    # draw the pairing QR code, then replay the recent history to it so the
    # dashboard fills up immediately.
    ui.send_message("welcome", pairing_payload(), room=sid)
    with history_lock:
        ui.send_message("history", list(history), room=sid)


ui.on_connect(on_ui_connect)


def on_status_changed(status: str, info: dict):
    # Lifecycle events: "disconnected", "connected".
    global SENSOR_STATUS
    SENSOR_STATUS = str(status)
    ui.send_message("sensor_status", {"status": status, "info": info})
    with history_lock:
        last = dict(history[-1]) if history else {}
    send_telemetry(last, f"sensor_{status}", force=True)


sensor.on_status_changed(on_status_changed)


def on_datapoint(raw: bytes):
    # The peripheral delivers raw bytes; the phone sends one JSON object per message.
    try:
        data = json.loads(raw.decode())
    except Exception:
        return
    if not isinstance(data, dict):
        return
    with history_lock:
        history.append(data)
    ui.send_message("datapoint", data)
    send_telemetry(data)


sensor.on_datapoint(on_datapoint)

sensor.start()

App.run()
