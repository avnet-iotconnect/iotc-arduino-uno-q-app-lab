# SPDX-FileCopyrightText: Copyright (C) Arduino s.r.l. and/or its affiliated companies
#
# SPDX-License-Identifier: MPL-2.0

# /IOTCONNECT-enabled version of the Arduino VENTUNO Q "Edge Dictation Assistant" example.
# Written against the /IOTCONNECT brick (bricks/iotconnect, see bricks/iotconnect/README.md) in
# direct mode, with no relay client. Install the brick into the App Lab copy of the example with:
#   bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER> --direct
# App Lab puts /app/bricks on PYTHONPATH, which is what makes `from iotconnect import IoTConnect` work.
# The upstream web UI handlers keep their behaviour; this file adds telemetry (one message per final
# transcription chunk, plus "listening" / "stopped" status messages) and the start-dictation,
# stop-dictation and set-language commands around them.

import threading

from arduino.app_bricks.asr import ASRBusyError, AutomaticSpeechRecognition
from arduino.app_bricks.web_ui import WebUI
from arduino.app_utils import App

# ---- /IOTCONNECT brick ----
from iotconnect import IoTConnect

UNOQ_DEMO_NAME = "edge-dictation-assistant"
PREVIEW_CHARS = 200
DEFAULT_DICTATION_SECONDS = 15.0

asr = AutomaticSpeechRecognition()
ui = WebUI()
iotc = IoTConnect()  # mode, credentials and relay endpoint come from the brick's variables

message_count = 0  # final transcription chunks since the app started
dictation_lock = threading.Lock()
dictation_running = False  # True while a transcribe_stream() session is open (web UI or command)
dictation_timer = None  # ends a command-started dictation after its timeout


def _preview(text) -> str:
    return " ".join(str(text or "").split())[:PREVIEW_CHARS]


def current_language() -> str:
    return str(getattr(asr, "language", None) or "auto")


def send_telemetry(status: str, source: str = "web_ui", transcript=None) -> bool:
    """status "ok" with a transcript = one final chunk; "listening" / "stopped" = a dictation started / ended."""
    payload = {"UnoQdemo": UNOQ_DEMO_NAME, "source": source}
    if transcript is not None:
        payload["message_count"] = int(message_count)
        payload["transcript"] = _preview(transcript)
    payload["language"] = current_language()
    payload["status"] = status
    print("IOTCONNECT send:", payload)
    ok = iotc.send_telemetry(payload)
    print("IOTCONNECT send result:", ok)
    return ok


def claim_dictation() -> None:
    """Marks a dictation as running, or raises ASRBusyError when one already is (as the asr brick itself would)."""
    global dictation_running
    with dictation_lock:
        if dictation_running:
            raise ASRBusyError("a dictation is already running")
        dictation_running = True


def cancel_dictation_timer() -> None:
    global dictation_timer
    with dictation_lock:
        timer, dictation_timer = dictation_timer, None
    if timer is not None:
        timer.cancel()


def run_dictation(source: str = "web_ui", claimed: bool = False) -> None:
    """One transcription session: every chunk goes to the web UI exactly as upstream, final chunks also to /IOTCONNECT."""
    global message_count, dictation_running
    if not claimed:
        claim_dictation()
    send_telemetry("listening", source)
    try:
        with asr.transcribe_stream() as stream:
            for chunk in stream:
                ui.send_message("transcription", {"type": chunk.type, "text": chunk.data})
                # Only final text is published; empty final chunks are skipped, as the web UI skips them too.
                if chunk.type == "full_text" and str(chunk.data or "").strip():
                    message_count += 1
                    send_telemetry("ok", source, transcript=chunk.data)
    finally:
        cancel_dictation_timer()
        with dictation_lock:
            dictation_running = False
        send_telemetry("stopped", source)


def command_dictation(timer: threading.Timer) -> None:
    """Runs a dictation started from /IOTCONNECT; the timer calls asr.cancel() when the time is up."""
    timer.start()
    try:
        run_dictation("iotconnect", claimed=True)
    except Exception as e:
        print(f"IOTCONNECT dictation ended with an error: {e}")


# ---- /IOTCONNECT commands ----
@iotc.command("start-dictation")
def on_start_dictation(args: list[str]) -> str:
    """start-dictation [seconds]: transcribe from the microphone for that long (default 15 s), like the mic button."""
    global dictation_timer
    print(f"IOTCONNECT command: start-dictation {args}")
    seconds = float(args[0]) if args and args[0].strip() else DEFAULT_DICTATION_SECONDS  # a bad value raises -> failed ack
    if seconds <= 0:
        raise ValueError(f"seconds must be greater than 0, got {seconds:g}")  # failed ack
    claim_dictation()  # raises ASRBusyError -> failed ack while a dictation is already running
    timer = threading.Timer(seconds, asr.cancel)
    timer.daemon = True
    with dictation_lock:
        dictation_timer = timer
    # Run off the command thread so the ack is not held up for the whole dictation
    threading.Thread(target=command_dictation, args=(timer,), daemon=True).start()
    print(f"IOTCONNECT dictation started for {seconds:g}s")
    return f"listening for {seconds:g}s"


@iotc.command("stop-dictation")
def on_stop_dictation(args: list[str]) -> str:
    """stop-dictation: end the running dictation (web UI or command started), like the pause button."""
    print(f"IOTCONNECT command: stop-dictation {args}")
    asr.cancel()
    return "stopped"


@iotc.command("set-language")
def on_set_language(args: list[str]) -> str:
    """set-language <code>: language for the next dictation (en, it, es, de, fr, pt, nl, ja, pl, ...), like the UI picker."""
    print(f"IOTCONNECT command: set-language {args}")
    code = args[0].strip() if args else ""
    if not code:
        raise ValueError("language code required")  # failed ack
    asr.language = code
    print(f"IOTCONNECT language set to {code}")
    return f"language {code}"


# ---- web UI handlers (upstream behaviour) ----
def set_language(session_id, data):
    asr.language = data["language"]


def start_dictation(session_id, data):
    run_dictation("web_ui")  # the same chunk forwarding as upstream, plus telemetry


def stop_dictation(session_id, data):
    asr.cancel()


def new_recording(session_id, data):
    stop_dictation(session_id, data)


ui.on_message("start_dictation", start_dictation)
ui.on_message("stop_dictation", stop_dictation)
ui.on_message("new_recording", new_recording)
ui.on_message("set_language", set_language)

App.run()
