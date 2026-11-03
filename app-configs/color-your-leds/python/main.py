# SPDX-FileCopyrightText: Copyright (C) Arduino s.r.l. and/or its affiliated companies
#
# SPDX-License-Identifier: MPL-2.0

import json
import re
from arduino.app_utils import *
from arduino.app_bricks.web_ui import WebUI

# ---- IOTCONNECT Relay ----
from iotc_relay_client import IoTConnectRelayClient

RELAY_ENDPOINT = "tcp://172.17.0.1:8899"
RELAY_CLIENT_ID = "color_your_leds"
UNOQ_DEMO_NAME = "color-your-leds"

COLOR_NAMES = {
    "off": (0, 0, 0),
    "black": (0, 0, 0),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "white": (255, 255, 255),
}

# Last color applied to each LED (0-255 per channel)
led_colors = {ledid: {"r": 0, "g": 0, "b": 0} for ledid in (1, 2, 3, 4)}

ui = WebUI()

relay = IoTConnectRelayClient(
    RELAY_ENDPOINT,
    client_id=RELAY_CLIENT_ID,
)
relay.start()


def _hex(rgb: dict) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        int(rgb.get("r", 0)) & 0xFF, int(rgb.get("g", 0)) & 0xFF, int(rgb.get("b", 0)) & 0xFF
    )


def send_telemetry(ledid=0, status="ok"):
    rgb = led_colors.get(ledid, {"r": 0, "g": 0, "b": 0})
    payload = {
        "UnoQdemo": UNOQ_DEMO_NAME,
        "led_id": int(ledid) if ledid in led_colors else 0,
        "led_color": _hex(rgb),
        "led_state": "on" if any(int(v) != 0 for v in rgb.values()) else "off",
        "led1_color": _hex(led_colors[1]),
        "led2_color": _hex(led_colors[2]),
        "led3_color": _hex(led_colors[3]),
        "led4_color": _hex(led_colors[4]),
        "status": status,
    }
    print("IOTCONNECT send:", payload)
    relay.send_telemetry(payload)


def apply_color(ledid: int, rgb_color: dict):
    # Led 1 and 2 are controlled by directly (MPU), while Led 3 and 4 are controlled via Bridge (MCU)
    match ledid:
        case 1:
            Leds.set_led1_color(rgb_color["r"] != 0, rgb_color["g"] != 0, rgb_color["b"] != 0)
        case 2:
            Leds.set_led2_color(rgb_color["r"] != 0, rgb_color["g"] != 0, rgb_color["b"] != 0)
        case 3:
            Bridge.call("set_led3_color", rgb_color["r"], rgb_color["g"], rgb_color["b"])
        case 4:
            Bridge.call("set_led4_color", rgb_color["r"] != 0, rgb_color["g"] != 0, rgb_color["b"] != 0)
    led_colors[ledid] = {"r": int(rgb_color["r"]), "g": int(rgb_color["g"]), "b": int(rgb_color["b"])}


def _validate(ledid, rgb_color):
    if ledid not in (1, 2, 3, 4):
        raise ValueError(f"Unknown led '{ledid}'")
    if not rgb_color or not all(k in rgb_color for k in ("r", "g", "b")):
        raise ValueError("Color must be an object with 'r', 'g', 'b' keys")


def on_set_color(id, message: dict):
    ledid = message.get("led")
    rgb_color = message.get("color")
    try:
        _validate(ledid, rgb_color)
        apply_color(ledid, rgb_color)
        send_telemetry(ledid, "ok")
    except Exception as e:
        ui.send_message("error", f"LED color set error: {e}")
        send_telemetry(ledid, f"error:{e}")


# ---- IOTCONNECT command handling ----
def _parse_color(value) -> dict:
    """Accept {"r","g","b"}, "#rrggbb", "r,g,b" or a color name."""
    if isinstance(value, dict):
        return {k: int(value.get(k, 0)) for k in ("r", "g", "b")}
    s = str(value if value is not None else "").strip().lower()
    if s in COLOR_NAMES:
        r, g, b = COLOR_NAMES[s]
        return {"r": r, "g": g, "b": b}
    if s.startswith("#") and len(s) == 7:
        return {"r": int(s[1:3], 16), "g": int(s[3:5], 16), "b": int(s[5:7], 16)}
    parts = [p for p in re.split(r"[,\s]+", s) if p]
    if len(parts) == 3:
        return {"r": int(parts[0]), "g": int(parts[1]), "b": int(parts[2])}
    raise ValueError(f"Unsupported color '{value}'")


def _parse_led_id(value) -> int:
    s = str(value if value is not None else "").strip().lower().replace("led", "").strip()
    return int(s)


def _parse_command(parameters):
    """Accept {"led":3,"color":...}, "3 red", "3 #ff8800", "3 255,128,0" or "led:3 color:red"."""
    data = parameters
    if isinstance(data, (list, tuple)) and len(data) == 1:
        data = data[0]
    if isinstance(data, (bytes, bytearray)):
        data = data.decode("utf-8", errors="strict")
    if isinstance(data, str):
        s = data.strip()
        try:
            data = json.loads(s)
        except Exception:
            kv = {}
            for t in s.split():
                if ":" in t or "=" in t:
                    k, v = re.split(r"[:=]", t, maxsplit=1)
                    kv[k.strip().strip('"').lower()] = v.strip().strip('"')
            if "led" in kv and "color" in kv:
                data = kv
            else:
                tokens = s.split(None, 1)
                if len(tokens) != 2:
                    raise ValueError(f"Unsupported payload: {s[:80]}")
                data = {"led": tokens[0], "color": tokens[1]}
    if not isinstance(data, dict):
        raise ValueError(f"Unsupported payload type: {type(parameters).__name__}")
    ledid = _parse_led_id(data.get("led", data.get("id", data.get("name"))))
    color = _parse_color(data.get("color", data.get("state")))
    return ledid, color


def on_relay_command(command_name, parameters):
    print(f"IOTCONNECT command: {command_name} {parameters}")
    if command_name in ("set-led", "set_led"):
        ledid = 0
        try:
            ledid, rgb_color = _parse_command(parameters)
            _validate(ledid, rgb_color)
            apply_color(ledid, rgb_color)
            send_telemetry(ledid, "ok")
        except Exception as e:
            send_telemetry(ledid, f"error:{e}")


relay.command_callback = on_relay_command

# Initialize LEDs to off state (only 1 and 2 here, 3 and 4 will be set in MCU setup)
apply_color(1, {"r": 0, "g": 0, "b": 0})
apply_color(2, {"r": 0, "g": 0, "b": 0})

ui.on_message("set_color", on_set_color)

App.run()
