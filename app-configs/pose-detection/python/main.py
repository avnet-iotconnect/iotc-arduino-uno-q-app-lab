# SPDX-FileCopyrightText: Copyright (C) Arduino s.r.l. and/or its affiliated companies
#
# SPDX-License-Identifier: MPL-2.0

# /IOTCONNECT-enabled version of the Arduino "Pose Detection" example (Arduino VENTUNO Q).
# The game itself is unchanged; this file adds the /IOTCONNECT brick (bricks/iotconnect, see
# bricks/iotconnect/README.md) in direct mode, so the app is the /IOTCONNECT device itself.
# Run `bash scripts/add_iotconnect_brick.sh <app> --direct` on the app first: it copies the brick
# into <app>/bricks/iotconnect, lists it in app.yaml and copies the device credentials into
# <app>/data/iotconnect. App Lab puts /app/bricks on PYTHONPATH, which is what makes
# `from iotconnect import IoTConnect` work.

import time

from arduino.app_utils import App
from arduino.app_bricks.pose_estimation import BUILTIN_POSE_NAMES, PoseEstimation
from arduino.app_bricks.web_ui import WebUI

# ---- /IOTCONNECT brick (bricks/iotconnect, see bricks/iotconnect/README.md) ----
from iotconnect import IoTConnect

UNOQ_DEMO_NAME = "pose-detection"
IOTC_INTERVAL_SEC = 1.0  # minimum time between two pose-event telemetry messages (0 = every event)
IOTC_LAST_SEND = 0.0

iotc = IoTConnect()  # mode and credentials come from the brick's variables (direct mode on the VENTUNO Q)


@iotc.command("set-interval")
def on_set_interval(args: list[str]) -> str:
    """set-interval <seconds>: minimum time between two pose-event telemetry messages (0 = every event)."""
    global IOTC_INTERVAL_SEC
    print(f"IOTCONNECT command: set-interval {args}")
    try:
        value = float(args[0].strip())
        if value < 0:
            raise ValueError("seconds must be >= 0")
        IOTC_INTERVAL_SEC = value
    except Exception as e:
        print(f"IOTCONNECT interval update failed: {e}")
        raise  # failed ack, with the error as the message
    print(f"IOTCONNECT interval set to {IOTC_INTERVAL_SEC}s")
    return f"interval {IOTC_INTERVAL_SEC}s"


ui = WebUI()
pose_estimation = PoseEstimation(
    confidence=0.45,
    draw_bboxes=True,
    bbox_padding=(0.15, 0.20, 0.15, 0.20),
    draw_low_confidence_points=False,
    count_debounce_sec=1.0,
    out_of_frame_tolerance=0.05
)


def send_pose_telemetry(pose):
    """One message per pose enter/exit event, at most one per IOTC_INTERVAL_SEC (a dropped event is fine)."""
    global IOTC_LAST_SEND
    now = time.time()
    if now - IOTC_LAST_SEND < IOTC_INTERVAL_SEC:
        return
    IOTC_LAST_SEND = now
    payload = {
        "UnoQdemo": UNOQ_DEMO_NAME,
        "pose": pose.name,
        "pose_event": pose.event,
        "people_count": int(pose_estimation.people_count),
        "status": "ok",
    }
    print("IOTCONNECT send:", payload)
    ok = iotc.send_telemetry(payload)
    print("IOTCONNECT send result:", ok)


def send_people_telemetry(count):
    """One message whenever the people count changes (not rate-limited)."""
    payload = {
        "UnoQdemo": UNOQ_DEMO_NAME,
        "people_count": int(count),
        "status": "ok",
    }
    print("IOTCONNECT send:", payload)
    ok = iotc.send_telemetry(payload)
    print("IOTCONNECT send result:", ok)


def on_pose(pose):
    ui.send_message("pose", {"name": pose.name, "event": pose.event})
    send_pose_telemetry(pose)


def on_count_change(count):
    ui.send_message("people", {"count": count})
    send_people_telemetry(count)


for pose_name in BUILTIN_POSE_NAMES:
    pose_estimation.on_pose(pose_name, on_pose)

pose_estimation.on_count_change(on_count_change)
pose_estimation.on_readable_change(lambda readable: ui.send_message("readable", {"value": readable}))

def sync_state(client):
    ui.send_message("people", {"count": pose_estimation.people_count}, room=client)
    ui.send_message("readable", {"value": pose_estimation.readable}, room=client)


ui.on_connect(sync_state)

App.run()
