# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Avnet
"""Blink the LED from Python, report it to /IOTCONNECT and take commands from the cloud.

Telemetry (every `interval_sec` seconds): UnoQdemo, interval_sec, led_state, status
Commands: set-interval <seconds>, set-led <0|1>
Both match the workshop's master device template ("arduino") and app-configs/blink/device-template.json.
"""

import time

from arduino.app_utils import App, Bridge
from iotconnect import IoTConnect

UNOQ_DEMO_NAME = "iotconnect-blink"
BLINK_PERIOD_S = 1.0

interval_sec = 5  # seconds between telemetry messages (the template's data frequency is 5 s)
led_state = False
last_sent = 0.0

iotc = IoTConnect()  # mode, credentials and relay endpoint come from the brick's variables


@iotc.command("set-interval")
def set_interval(args: list[str]) -> str:
    """set-interval <seconds>: change how often telemetry is sent."""
    global interval_sec
    interval_sec = max(1, int(float(args[0])))  # a bad argument raises -> failed ack
    return f"interval {interval_sec}s"


@iotc.command("set-led")
def set_led(args: list[str]) -> str:
    """set-led <0|1>: force the LED state (blinking continues from there)."""
    global led_state
    led_state = args[0].strip().lower() in ("1", "on", "true")
    Bridge.call("set_led_state", led_state)
    return f"led {'on' if led_state else 'off'}"


def send_telemetry() -> None:
    global last_sent
    now = time.monotonic()
    if now - last_sent < interval_sec:
        return
    last_sent = now
    payload = {
        "UnoQdemo": UNOQ_DEMO_NAME,
        "interval_sec": interval_sec,
        "led_state": "on" if led_state else "off",
        "status": "ok",
    }
    if iotc.send_telemetry(payload):
        print("IOTCONNECT send:", payload)


def loop() -> None:
    global led_state
    time.sleep(BLINK_PERIOD_S)
    led_state = not led_state
    Bridge.call("set_led_state", led_state)
    send_telemetry()


App.run(user_loop=loop)
