# SPDX-FileCopyrightText: Copyright (C) Arduino s.r.l. and/or its affiliated companies
#
# SPDX-License-Identifier: MPL-2.0

# /IOTCONNECT-enabled version of the Arduino VENTUNO Q "Gesture Booth" example, written against the
# /IOTCONNECT brick (bricks/iotconnect, see bricks/iotconnect/README.md) in direct mode. The camera,
# gesture recognition and web UI code is the upstream example's; the brick adds one telemetry message
# each time the recognised gesture changes, plus a set-interval command. The app must have the brick:
#   bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER> --direct

from arduino.app_bricks.web_ui import WebUI
from arduino.app_bricks.gesture_recognition import GestureRecognition
from arduino.app_peripherals.camera import Camera
from arduino.app_utils.image.adjustments import cropped_to_aspect_ratio
from arduino.app_utils.app import App
import threading
import time

# ---- /IOTCONNECT brick ----
from iotconnect import IoTConnect

UNOQ_DEMO_NAME = "gesture-booth"
IOTC_INTERVAL_SEC = 1.0  # minimum time between two telemetry messages; set-interval changes it
IOTC_LAST_SEND = 0.0
LAST_GESTURE = None  # UI label of the last gesture successfully sent to /IOTCONNECT
GESTURE_COUNT = 0  # telemetry messages successfully sent since start, "None" not counted
IOTC_LOCK = threading.Lock()  # gesture callbacks and command handlers run on different threads

iotc = IoTConnect()  # mode and credentials come from the brick's variables (direct mode on the VENTUNO Q)


@iotc.command("set-interval")
def on_set_interval(args: list[str]) -> str:
    """set-interval <seconds>: minimum time between two telemetry messages (0 = report every change)."""
    global IOTC_INTERVAL_SEC
    print(f"IOTCONNECT command: set-interval {args}")
    try:
        seconds = float(args[0].strip())
        if seconds < 0:
            raise ValueError(f"interval must be >= 0, got {seconds}")
    except Exception as e:
        print(f"IOTCONNECT interval update failed: {e}")
        raise  # failed ack, with the error as the message
    with IOTC_LOCK:
        IOTC_INTERVAL_SEC = seconds
    print(f"IOTCONNECT interval set to {IOTC_INTERVAL_SEC}s")
    return f"interval {IOTC_INTERVAL_SEC}s"


def report_gesture(label: str):
    """Sends one telemetry message when the recognised gesture changes, at most one per IOTC_INTERVAL_SEC.

    The brick calls the gesture callbacks for every frame, so a change that falls inside the interval is
    reported by the next callback once the interval has passed. "None" (hand visible, no gesture) is
    reported as a change so a dashboard clears, but it is not counted in gesture_count. The last gesture
    and the count are committed only once the send has succeeded, so a gesture that could not be sent
    (send_telemetry returns False until the brick is connected) is retried once per interval until it
    goes through, and gesture_count only counts messages that were actually sent.
    """
    global IOTC_LAST_SEND, LAST_GESTURE, GESTURE_COUNT
    with IOTC_LOCK:
        if label == LAST_GESTURE:
            return
        now = time.time()
        if now - IOTC_LAST_SEND < IOTC_INTERVAL_SEC:
            return
        IOTC_LAST_SEND = now
        count = GESTURE_COUNT + (0 if label == "None" else 1)
        payload = {
            "UnoQdemo": UNOQ_DEMO_NAME,
            "gesture": label,
            "gesture_count": count,
            "status": "ok",
        }
    print("IOTCONNECT send:", payload)
    ok = iotc.send_telemetry(payload)
    print("IOTCONNECT send result:", ok)
    if ok:
        with IOTC_LOCK:
            LAST_GESTURE = label
            GESTURE_COUNT = count


def gesture_detected(label: str):
    """Callback for one gesture: the upstream web UI message, then the /IOTCONNECT report."""
    def handler(meta):
        ui.send_message('gesture_detected', {'gesture': label})
        report_gesture(label)
    return handler


ui = WebUI()

camera = Camera(resolution=(1280, 960), fps=30, codec="MJPG", adjustments=cropped_to_aspect_ratio((4, 3)))
camera.start()

pd = GestureRecognition(camera)
pd.on_gesture("None", gesture_detected('None'))
pd.on_gesture("Closed_Fist", gesture_detected('Closed Fist'))
pd.on_gesture("Open_Palm", gesture_detected('Open Palm'))
pd.on_gesture("Pointing_Up", gesture_detected('Pointing Up'))
pd.on_gesture("Thumb_Down", gesture_detected('Thumb Down'))
pd.on_gesture("Thumb_Up", gesture_detected('Thumb Up'))
pd.on_gesture("Victory", gesture_detected('Victory'))
pd.on_gesture("ILoveYou", gesture_detected('Rock'))

App.run()
