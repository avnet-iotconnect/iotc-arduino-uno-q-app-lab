# SPDX-FileCopyrightText: Copyright (C) ARDUINO SRL (http://www.arduino.cc)
#
# SPDX-License-Identifier: MPL-2.0

import json, ast, re, shlex, threading
from datetime import datetime, UTC
from arduino.app_utils import *
from arduino.app_bricks.web_ui import WebUI

# ---- IOTCONNECT Relay ----
from iotc_relay_client import IoTConnectRelayClient

RELAY_ENDPOINT = "tcp://172.17.0.1:8899"
RELAY_CLIENT_ID = "unoq_pin_toggle"
UNOQ_DEMO_NAME = "unoq-pin-toggle"
SOFTWARE_VERSION = "2026.02.19.1"
PATTERN_DELAY_SEC = 0.35

relay = IoTConnectRelayClient(
    RELAY_ENDPOINT,
    client_id=RELAY_CLIENT_ID,
)
relay.start()
print(f"IOTCONNECT software version: {SOFTWARE_VERSION}")

# ---------- Pin config: add pins here ----------
PIN_CONFIG = {
    # JDIGITAL
    "D21": {"active_low": False},
    "D20": {"active_low": False},
    "D13": {"active_low": False},
    "D12": {"active_low": False},
    "D11": {"active_low": False},
    "D10": {"active_low": False},
    "D9": {"active_low": False},
    "D8": {"active_low": False},
    "D7": {"active_low": False},
    "D6": {"active_low": False},
    "D5": {"active_low": False},
    "D4": {"active_low": False},
    "D3": {"active_low": False},
    "D2": {"active_low": False},
    "D1": {"active_low": False},
    "D0": {"active_low": False},
    # JANALOG
    "A0": {"active_low": False},
    "A1": {"active_low": False},
    "A2": {"active_low": False},
    "A3": {"active_low": False},
    "A4": {"active_low": False},
    "A5": {"active_low": False},
    # STM LEDS
    "LED3_R": {"active_low": True},
    "LED3_G": {"active_low": True},
    "LED3_B": {"active_low": True},
    "LED4_R": {"active_low": True},
    "LED4_G": {"active_low": True},
    "LED4_B": {"active_low": True},

}
PIN_NAMES = tuple(PIN_CONFIG.keys())
LED_GROUPS = {
    "LED3": ("LED3_R", "LED3_G", "LED3_B"),
    "LED4": ("LED4_R", "LED4_G", "LED4_B"),
}
LED_COLORS = {
    "off": (False, False, False),
    "red": (True, False, False),
    "green": (False, True, False),
    "blue": (False, False, True),
    "yellow": (True, True, False),
    "cyan": (False, True, True),
    "magenta": (True, False, True),
    "white": (True, True, True),
}
LED_PATTERNS = {"rainbow", "blink", "police"}

pin_states = {name: False for name in PIN_NAMES}
pattern_controls = {}
RGB_TO_COLOR = {v: k for k, v in LED_COLORS.items()}
led_annotations = {"LED3": "off", "LED4": "off"}

ui = WebUI()

def _iso_now() -> str:
    return datetime.now(UTC).isoformat()

def _normalize_state(value) -> bool:
    if isinstance(value, bool): return value
    if isinstance(value, (int, float)): return bool(int(value))
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("on","true","1"):  return True
        if v in ("off","false","0"): return False
    raise ValueError(f"Invalid state value: {value!r}")


def _normalize_name(value) -> str:
    return str(value or "").strip().upper()


def _pack_bits(pin_list):
    value = 0
    for idx, pin in enumerate(pin_list):
        if pin_states.get(pin, False):
            value |= (1 << idx)
    return value


def _led_color_from_pins(group: str) -> str:
    channels = LED_GROUPS[group]
    rgb = (
        bool(pin_states.get(channels[0], False)),
        bool(pin_states.get(channels[1], False)),
        bool(pin_states.get(channels[2], False)),
    )
    return RGB_TO_COLOR.get(rgb, "off")


def _pin_state_object():
    return {
        "D0_D3": _pack_bits(("D0", "D1", "D2", "D3")),
        "D4_D7": _pack_bits(("D4", "D5", "D6", "D7")),
        "D8_D11": _pack_bits(("D8", "D9", "D10", "D11")),
        "D12_D21": _pack_bits(("D12", "D13", "D20", "D21")),
        "A0_A2": _pack_bits(("A0", "A1", "A2")),
        "A3_A5": _pack_bits(("A3", "A4", "A5")),
        "LED3": _pack_bits(("LED3_R", "LED3_G", "LED3_B")),
        "LED4": _pack_bits(("LED4_R", "LED4_G", "LED4_B")),
        "LED3_color": led_annotations["LED3"],
        "LED4_color": led_annotations["LED4"],
    }

def _ensure_dict(payload):
    if isinstance(payload, (list, tuple)) and len(payload) == 1:
        payload = payload[0]
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, (bytes, bytearray)):
        payload = payload.decode("utf-8", errors="strict")
    if isinstance(payload, str):
        s = payload.strip()
        try:
            return json.loads(s)
        except Exception:
            try:
                val = ast.literal_eval(s)
                if isinstance(val, (list, tuple)) and len(val) == 1 and isinstance(val[0], dict):
                    return val[0]
                if isinstance(val, dict):
                    return val
            except Exception:
                pass
        # Allow IoTConnect text command forms:
        # - "D12 on"
        # - "name:D12 state:on"
        # - "\"name\":\"D12\" \"state\":\"on\""
        try:
            tokens = shlex.split(s)
        except Exception:
            tokens = s.split()

        if len(tokens) >= 2 and ":" not in tokens[0] and "=" not in tokens[0]:
            return {"name": tokens[0], "state": tokens[1]}

        kv = {}
        for t in tokens:
            if ":" in t:
                k, v = t.split(":", 1)
            elif "=" in t:
                k, v = t.split("=", 1)
            else:
                continue
            k = k.strip().strip('"').strip("'").lower()
            v = v.strip().strip('"').strip("'")
            if k in ("name", "state"):
                kv[k] = v
        if "name" in kv and "state" in kv:
            return kv

        rx = re.findall(r'"?(name|state)"?\s*[:=]\s*"?([^\s",]+)"?', s, flags=re.IGNORECASE)
        if rx:
            parsed = {}
            for k, v in rx:
                parsed[k.lower()] = v
            if "name" in parsed and "state" in parsed:
                return parsed
        raise ValueError(f"Unsupported string payload: {s[:80]}...")
    raise ValueError(f"Unsupported payload type: {type(payload).__name__}")

def _state_for_hw(name: str, logical_state: bool) -> bool:
    cfg = PIN_CONFIG.get(name, {})
    return (not logical_state) if cfg.get("active_low") else logical_state


def _set_pin_logical(name: str, logical_state: bool):
    pin_states[name] = logical_state
    state_for_hw = _state_for_hw(name, logical_state)
    Bridge.call("set_pin_by_name", name, state_for_hw)


def _iter_led_groups(target: str):
    return LED_GROUPS.keys() if target == "LED" else (target,)


def _stop_led_pattern_for_group(group: str):
    ctl = pattern_controls.get(group)
    if not ctl:
        return
    ctl["stop"].set()
    thread = ctl.get("thread")
    if thread is not None and thread.is_alive():
        thread.join(timeout=0.5)
    pattern_controls.pop(group, None)


def _stop_led_pattern(target: str):
    for group in _iter_led_groups(target):
        _stop_led_pattern_for_group(group)


def _set_led_group_color(group: str, color: str):
    channels = LED_GROUPS[group]
    rgb = LED_COLORS[color]
    _set_pin_logical(channels[0], bool(rgb[0]))
    _set_pin_logical(channels[1], bool(rgb[1]))
    _set_pin_logical(channels[2], bool(rgb[2]))
    led_annotations[group] = color


def _set_led_target_color(target: str, color: str):
    for group in _iter_led_groups(target):
        _set_led_group_color(group, color)


def _run_led_pattern_for_group(group: str, pattern: str, stop_event: threading.Event, phase: int = 0):
    if pattern == "blink":
        sequence = ["white", "off"]
    elif pattern == "police":
        sequence = ["red", "blue"]
    else:
        sequence = ["red", "yellow", "green", "cyan", "blue", "magenta", "white"]

    idx = phase % len(sequence)
    while not stop_event.is_set():
        _set_led_group_color(group, sequence[idx])
        if stop_event.wait(PATTERN_DELAY_SEC):
            return
        idx = (idx + 1) % len(sequence)


def _start_led_pattern(target: str, pattern: str):
    if target == "LED":
        _stop_led_pattern("LED")
        phase_for_group = {
            "LED3": 0,
            "LED4": 1 if pattern == "police" else 0,
        }
        for group in ("LED3", "LED4"):
            stop_event = threading.Event()
            thread = threading.Thread(
                target=_run_led_pattern_for_group,
                args=(group, pattern, stop_event, phase_for_group[group]),
                daemon=True,
            )
            pattern_controls[group] = {"stop": stop_event, "thread": thread}
            led_annotations[group] = f"pattern:{pattern}"
            thread.start()
        return

    _stop_led_pattern(target)
    stop_event = threading.Event()
    thread = threading.Thread(
        target=_run_led_pattern_for_group, args=(target, pattern, stop_event, 0), daemon=True
    )
    pattern_controls[target] = {"stop": stop_event, "thread": thread}
    led_annotations[target] = f"pattern:{pattern}"
    thread.start()


def _handle_led_command(name: str, state_value) -> str:
    state_token = str(state_value or "").strip().lower()
    if state_token in LED_COLORS:
        _stop_led_pattern(name)
        _set_led_target_color(name, state_token)
        return state_token
    if state_token in LED_PATTERNS:
        _start_led_pattern(name, state_token)
        return f"pattern:{state_token}"
    raise ValueError(
        f"Unsupported LED state '{state_value}'. Use colors {sorted(LED_COLORS.keys())} "
        f"or patterns {sorted(LED_PATTERNS)}"
    )


def _led_group_for_pin(name: str):
    if name.startswith("LED3_"):
        return "LED3"
    if name.startswith("LED4_"):
        return "LED4"
    return None


def send_telemetry(name, status="pin_set"):
    payload = {
        "UnoQdemo": UNOQ_DEMO_NAME,
        "sw_version": SOFTWARE_VERSION,
        "pin_name": name,
        "pin_state": _pin_state_object(),
        "status": status,
    }
    print("IOTCONNECT send:", payload)
    relay.send_telemetry(payload)


def on_relay_command(command_name, parameters):
    print(f"IOTCONNECT command: {command_name} {parameters}")
    if command_name in ("set-pin", "set_pin"):
        try:
            data = _ensure_dict(parameters)
            name = _normalize_name(data.get("name"))
            state_value = data.get("state")
            if name in LED_GROUPS or name == "LED":
                _handle_led_command(name, state_value)
                send_telemetry(name, "pin_set")
                return
            if name not in PIN_NAMES:
                raise ValueError(f"Unknown Pin '{name}'")
            logical = _normalize_state(state_value)
            led_group = _led_group_for_pin(name)
            if led_group:
                _stop_led_pattern(led_group)
            _set_pin_logical(name, logical)
            if led_group:
                led_annotations[led_group] = _led_color_from_pins(led_group)
            send_telemetry(name, "pin_set")
        except Exception as e:
            send_telemetry("", f"error:{e}")


relay.command_callback = on_relay_command


def on_pin_toggle(sid, message):
    try:
        data = _ensure_dict(message)
        name = _normalize_name(data.get("name"))
        if name not in PIN_NAMES:
            raise ValueError(f"Unknown Pin '{name}'")

        logical = _normalize_state(data.get("state"))
        led_group = _led_group_for_pin(name)
        if led_group:
            _stop_led_pattern(led_group)
        _set_pin_logical(name, logical)
        if led_group:
            led_annotations[led_group] = _led_color_from_pins(led_group)
        state_for_hw = _state_for_hw(name, logical)

        print(f"[{_iso_now()}] [{sid}] {name} -> logical={'ON' if logical else 'OFF'} hw={state_for_hw}")
        ui.send_message("pin_state_update", {
            "name": name,
            "state": logical,
            "timestamp": _iso_now()
        })

        send_telemetry(name, "pin_set")

    except Exception as e:
        ui.send_message("error", f"Pin toggle error: {e}")
        send_telemetry("", f"error:{e}")


def on_get_states():
    return {"timestamp": _iso_now(), "states": pin_states}

ui.on_message("pin_toggle", on_pin_toggle)
ui.expose_api("GET", "/states", on_get_states)

App.run()
