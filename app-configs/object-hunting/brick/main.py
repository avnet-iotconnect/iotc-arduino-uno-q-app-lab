# SPDX-FileCopyrightText: Copyright (C) ARDUINO SRL (http://www.arduino.cc)
#
# SPDX-License-Identifier: MPL-2.0

# Brick variant of ../python/main.py: the same object-hunting app, but wired to the
# /IOTCONNECT brick (bricks/iotconnect) instead of the workshop's relay client.
# Run `bash scripts/add_iotconnect_brick.sh <app>` on the app first: it copies the brick
# into <app>/bricks/iotconnect and lists it in app.yaml. App Lab puts /app/bricks on
# PYTHONPATH, which is what makes `from iotconnect import IoTConnect` work.

from arduino.app_utils import App
from arduino.app_bricks.web_ui import WebUI
from arduino.app_bricks.video_objectdetection import VideoObjectDetection
from datetime import datetime, UTC
import base64
import time
import json

# ---- /IOTCONNECT brick (bricks/iotconnect, see bricks/iotconnect/README.md) ----
from iotconnect import IoTConnect

# ---- /IOTCONNECT Video Streaming (optional) ----
# With the KVS brick installed (scripts/add_kvs_brick.sh <app>) the camera is also streamed to the device's
# Video Streaming tab in /IOTCONNECT and to the App Lab Cloud Console. Without the brick this does nothing.
try:
    from kvs import KvsStream
    kvs_stream = KvsStream()
except ImportError:
    kvs_stream = None

UNOQ_DEMO_NAME = "object-hunting"
IOTC_INTERVAL_SEC = 5
IOTC_LAST_SEND = 0.0
CURRENT_CONFIDENCE = 0.5

iotc = IoTConnect()  # mode, relay endpoint and client id come from the brick's variables


@iotc.command("set-interval")
def on_set_interval(args: list[str]) -> str:
    """set-interval <seconds>: minimum time between two telemetry messages."""
    global IOTC_INTERVAL_SEC
    print(f"IOTCONNECT command: set-interval {args}")
    try:
        IOTC_INTERVAL_SEC = int(args[0].strip())
    except Exception as e:
        print(f"IOTCONNECT interval update failed: {e}")
        raise  # failed ack, with the error as the message
    print(f"IOTCONNECT interval set to {IOTC_INTERVAL_SEC}s")
    return f"interval {IOTC_INTERVAL_SEC}s"


@iotc.command("set-confidence")
def on_set_confidence(args: list[str]) -> str:
    """set-confidence <0..1>: detection threshold, also applied to the video stream."""
    global CURRENT_CONFIDENCE
    print(f"IOTCONNECT command: set-confidence {args}")
    try:
        CURRENT_CONFIDENCE = max(0.0, min(1.0, float(args[0].strip())))
        detection_stream.override_threshold(CURRENT_CONFIDENCE)
    except Exception as e:
        print(f"IOTCONNECT confidence update failed: {e}")
        raise  # failed ack, with the error as the message
    print(f"IOTCONNECT confidence set to {CURRENT_CONFIDENCE}")
    return f"confidence {CURRENT_CONFIDENCE}"


ui = WebUI()
detection_stream = VideoObjectDetection(confidence=CURRENT_CONFIDENCE, camera_preview=True)


def send_camera_frame(frame: bytes):
    if not frame:
        return
    ui.send_message("camera_frame", {
        "image": "data:image/jpeg;base64," + base64.b64encode(frame).decode("utf-8"),
        "timestamp": datetime.now(UTC).isoformat(),
    })


def top_confidence(value) -> float:
    # VideoObjectDetection's on_detect_all payload maps each label to a *list*
    # of {"confidence": ..., "bounding_box_xyxy": ...} dicts, not a single dict.
    if isinstance(value, list):
        confs = [v.get("confidence", 0.0) for v in value if isinstance(v, dict)]
        return max(confs) if confs else 0.0
    if isinstance(value, dict):
        return float(value.get("confidence", 0.0))
    return float(value or 0.0)

ui.on_message("override_th", lambda sid, threshold: detection_stream.override_threshold(threshold))


def build_slots(detections):
    top = sorted(detections, key=lambda d: d.get("confidence", 0), reverse=True)[:4]
    slots = {}
    for i in range(4):
        if i < len(top):
            slots[f"class_name_{i+1}"] = top[i].get("class_name", "")
            slots[f"confidence_{i+1}"] = float(top[i].get("confidence", 0))
        else:
            slots[f"class_name_{i+1}"] = ""
            slots[f"confidence_{i+1}"] = 0.0
    return slots


def send_telemetry(detections):
    global IOTC_LAST_SEND
    now = time.time()
    if now - IOTC_LAST_SEND < IOTC_INTERVAL_SEC:
        return
    IOTC_LAST_SEND = now
    confs = [d.get("confidence") for d in detections if isinstance(d.get("confidence"), (int, float))]
    max_conf = max(confs) if confs else 0.0
    avg_conf = (sum(confs) / len(confs)) if confs else 0.0
    payload = {
        "UnoQdemo": UNOQ_DEMO_NAME,
        "interval_sec": int(IOTC_INTERVAL_SEC),
        "detection_count": len(detections),
        "max_confidence": float(max_conf),
        "avg_confidence": float(avg_conf),
        "detections_json": json.dumps(detections),
        "status": "ok",
    }
    payload.update(build_slots(detections))
    print("IOTCONNECT send:", payload)
    ok = iotc.send_telemetry(payload)
    print("IOTCONNECT send result:", ok)


def send_detections_to_ui(detections: dict, frame: bytes = None):
    send_camera_frame(frame)
    det_list = []
    for key, value in detections.items():
        entry = {
            "content": key,
            "timestamp": datetime.now(UTC).isoformat()
        }
        ui.send_message("detection", message=entry)
        det_list.append({"class_name": key, "confidence": top_confidence(value)})

    send_telemetry(det_list)


detection_stream.on_detect_all(send_detections_to_ui)

App.run()
