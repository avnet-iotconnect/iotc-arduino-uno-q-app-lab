# SPDX-FileCopyrightText: Copyright (C) Arduino s.r.l. and/or its affiliated companies
#
# SPDX-License-Identifier: MPL-2.0

# /IOTCONNECT-enabled version of the Smart Mirror example (Arduino VENTUNO Q, arduino:vlm brick).
# The camera loop, the MJPEG /stream API, prompt.py and the web UI messages are the upstream example's.
# Around them, the /IOTCONNECT brick (bricks/iotconnect, see bricks/iotconnect/README.md) publishes one
# telemetry message per completed scan and handles the "scan-look" cloud command, which runs the same
# analysis as the web UI's "Scan your look" button on the latest camera frame.
# The app needs the brick installed in direct mode:
#   bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER> --direct

import time
from threading import Lock
from fastapi.responses import StreamingResponse
import prompt
from arduino.app_bricks.vlm import VisionLanguageModel
from arduino.app_bricks.web_ui import WebUI
from arduino.app_peripherals.camera import Camera
from arduino.app_utils import App, Logger
from arduino.app_utils.image import compressed_to_jpeg

# ---- /IOTCONNECT brick ----
from iotconnect import IoTConnect

UNOQ_DEMO_NAME = "smart-mirror"
MODEL_NAME = "vlm"
PREVIEW_CHARS = 200

logger = Logger("SmartMirror")

SYSTEM_PROMPT, USER_PROMPT_TEMPLATE = prompt.load_prompts()

frame_lock = Lock()
current_frame: bytes | None = None

scan_lock = Lock()  # one analysis at a time, whether the web UI or the cloud asked for it
scan_count = 0

ui = WebUI()
vlm = VisionLanguageModel(
    system_prompt=SYSTEM_PROMPT,
    temperature=0.4,
    max_tokens=120,
)
iotc = IoTConnect()  # mode and credentials come from the brick's variables (direct mode on the VENTUNO Q)


def send_telemetry(payload: dict) -> bool:
    print("IOTCONNECT send:", payload)
    ok = iotc.send_telemetry(payload)
    print("IOTCONNECT send result:", ok)
    return ok


def generate_frames():
    while True:
        with frame_lock:
            frame = current_frame

        if frame is None:
            time.sleep(0.1)
            continue

        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        time.sleep(0.05)


def video_stream():
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


def analyse_look(source: str) -> tuple[str, str]:
    """One scan of the latest camera frame (the upstream scan_look), plus one telemetry message.

    Returns (text for the mirror overlay, status); status is "ok" or "error:<msg>".
    """
    global scan_count

    with scan_lock:
        with frame_lock:
            frame = current_frame

        status = "ok"
        started = time.monotonic()
        try:
            if frame is None:
                raise RuntimeError("No camera frame available")

            result = vlm.chat(
                message=prompt.build_user_prompt(USER_PROMPT_TEMPLATE),
                images=[frame],
            ).strip()
            if not result:
                status = "error:empty response"
                result = "I can't scan the look yet. Step into view and try again."
        except Exception as exc:
            logger.exception(f"Smart mirror scan failed: {exc}")
            status = f"error:{exc}"
            result = "I can't scan the look right now. Please try again in a moment."
        elapsed_ms = int((time.monotonic() - started) * 1000)

        scan_count += 1
        send_telemetry({
            "UnoQdemo": UNOQ_DEMO_NAME,
            "source": source,
            "message_count": scan_count,
            "model": MODEL_NAME,
            "response_preview": result[:PREVIEW_CHARS],
            "response_chars": len(result),
            "processing_time_ms": elapsed_ms,
            "status": status,
        })

    return result, status


def scan_look(sid, _data):
    """Web UI "start_scan": the result goes back to the browser that asked, as upstream."""
    result, _status = analyse_look("web_ui")
    ui.send_message("analysis_result", result, room=sid)


@iotc.command("scan-look")
def on_scan_look(args: list[str]) -> str:
    """scan-look: analyse the latest camera frame, like the web UI's "Scan your look" button."""
    print(f"IOTCONNECT command: scan-look {args}")
    result, status = analyse_look("iotconnect")
    ui.send_message("analysis_result", result, room=None)  # every open mirror page shows it
    if status != "ok":
        raise RuntimeError(status[len("error:"):])  # failed ack with the reason, e.g. no camera frame
    return result[:PREVIEW_CHARS]


camera = Camera(fps=30, adjustments=compressed_to_jpeg())


def loop():
    global current_frame

    frame = camera.capture()
    if frame is None:
        return

    frame_bytes = frame.tobytes()
    with frame_lock:
        current_frame = frame_bytes


ui.expose_api("GET", "/stream", video_stream)
ui.on_message("start_scan", scan_look)

with camera:
    App.run(user_loop=loop)
