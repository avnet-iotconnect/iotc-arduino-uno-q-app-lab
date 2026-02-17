# SPDX-FileCopyrightText: Copyright (C) ARDUINO SRL (http://www.arduino.cc)
#
# SPDX-License-Identifier: MPL-2.0

import json
import time
from datetime import datetime
from arduino.app_utils import *
from arduino.app_bricks.web_ui import WebUI
from arduino.app_bricks.vibration_anomaly_detection import VibrationAnomalyDetection

# ---- IOTCONNECT Relay ----
from iotc_relay_client import IoTConnectRelayClient

RELAY_ENDPOINT = "tcp://172.17.0.1:8899"
RELAY_CLIENT_ID = "vibration_anomaly"
UNOQ_DEMO_NAME = "vibration-anomaly-detection"
LAST_ANOMALY_SCORE = 0.0
LAST_ANOMALY_DETECTED = False
INTERVAL_MAX_ANOMALY_SCORE = 0.0
INTERVAL_HAS_ANOMALY = False
TELEMETRY_INTERVAL_SEC = 2.0
LAST_TELEMETRY_TS = 0.0
LAST_SAMPLE_X = 0.0
LAST_SAMPLE_Y = 0.0
LAST_SAMPLE_Z = 0.0

logger = Logger("vibration-detector")

vibration_detection = VibrationAnomalyDetection(anomaly_detection_threshold=1.0)

ui = WebUI()


def send_telemetry(score, detected, x, y, z, status="ok"):
    payload = {
        "UnoQdemo": UNOQ_DEMO_NAME,
        "anomaly_score": float(score),
        "anomaly_detected": "true" if detected else "false",
        "threshold": float(vibration_detection.anomaly_detection_threshold),
        "interval_sec": float(TELEMETRY_INTERVAL_SEC),
        "x": float(x),
        "y": float(y),
        "z": float(z),
        "status": status,
    }
    print("IOTCONNECT send:", payload)
    relay.send_telemetry(payload)


def emit_interval_telemetry_if_due(status="sample"):
    global LAST_TELEMETRY_TS
    global LAST_ANOMALY_DETECTED
    global INTERVAL_MAX_ANOMALY_SCORE
    global INTERVAL_HAS_ANOMALY

    now = time.time()
    if now - LAST_TELEMETRY_TS >= TELEMETRY_INTERVAL_SEC:
        send_telemetry(
            INTERVAL_MAX_ANOMALY_SCORE,
            INTERVAL_HAS_ANOMALY,
            LAST_SAMPLE_X,
            LAST_SAMPLE_Y,
            LAST_SAMPLE_Z,
            status
        )
        LAST_TELEMETRY_TS = now
        LAST_ANOMALY_DETECTED = False
        INTERVAL_MAX_ANOMALY_SCORE = 0.0
        INTERVAL_HAS_ANOMALY = False


relay = IoTConnectRelayClient(
    RELAY_ENDPOINT,
    client_id=RELAY_CLIENT_ID,
)
relay.start()


def on_override_th(value: float):
    logger.info(f"Setting new anomaly threshold: {value}")
    vibration_detection.anomaly_detection_threshold = value


# IOTCONNECT command

def on_relay_command(command_name, parameters):
    global TELEMETRY_INTERVAL_SEC
    print(f"IOTCONNECT command: {command_name} {parameters}")
    if command_name == "set-threshold":
        try:
            val = parameters.get("threshold") if isinstance(parameters, dict) else parameters
            on_override_th(float(val))
            send_telemetry(LAST_ANOMALY_SCORE, LAST_ANOMALY_DETECTED, 0.0, 0.0, 0.0, "threshold")
        except Exception as e:
            print(f"IOTCONNECT set-threshold failed: {e}")
    elif command_name == "set-interval":
        try:
            val = parameters.get("seconds") if isinstance(parameters, dict) else parameters
            TELEMETRY_INTERVAL_SEC = max(0.1, float(val))
            print(f"IOTCONNECT interval set to {TELEMETRY_INTERVAL_SEC}s")
            send_telemetry(LAST_ANOMALY_SCORE, LAST_ANOMALY_DETECTED, 0.0, 0.0, 0.0, "interval")
        except Exception as e:
            print(f"IOTCONNECT set-interval failed: {e}")


relay.command_callback = on_relay_command

ui.on_message("override_th", lambda sid, threshold: on_override_th(threshold))


def get_fan_status(anomaly_detected: bool):
    return {
        "anomaly": anomaly_detected,
        "status_text": "Anomaly detected!" if anomaly_detected else "No anomaly"
    }


def on_detected_anomaly(anomaly_score: float, classification: dict):
    global LAST_ANOMALY_SCORE
    global LAST_ANOMALY_DETECTED
    global INTERVAL_MAX_ANOMALY_SCORE
    global INTERVAL_HAS_ANOMALY
    LAST_ANOMALY_SCORE = float(anomaly_score)
    LAST_ANOMALY_DETECTED = True
    INTERVAL_MAX_ANOMALY_SCORE = max(INTERVAL_MAX_ANOMALY_SCORE, LAST_ANOMALY_SCORE)
    INTERVAL_HAS_ANOMALY = True

    anomaly_payload = {
        "score": anomaly_score,
        "timestamp": datetime.now().isoformat()
    }
    ui.send_message('anomaly_detected', json.dumps(anomaly_payload))
    ui.send_message('fan_status_update', get_fan_status(True))
    emit_interval_telemetry_if_due("anomaly")


vibration_detection.on_anomaly(on_detected_anomaly)


def record_sensor_movement(x: float, y: float, z: float):
    global LAST_SAMPLE_X
    global LAST_SAMPLE_Y
    global LAST_SAMPLE_Z
    x_ms2 = x * 9.81
    y_ms2 = y * 9.81
    z_ms2 = z * 9.81

    LAST_SAMPLE_X = x_ms2
    LAST_SAMPLE_Y = y_ms2
    LAST_SAMPLE_Z = z_ms2

    ui.send_message('sample', {'x': x_ms2, 'y': y_ms2, 'z': z_ms2})

    vibration_detection.accumulate_samples((x_ms2, y_ms2, z_ms2))

    # Throttle sample telemetry to avoid flooding the relay/cloud path.
    emit_interval_telemetry_if_due("sample")


Bridge.provide("record_sensor_movement", record_sensor_movement)

App.run()
