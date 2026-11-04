# SPDX-FileCopyrightText: Copyright (C) Arduino s.r.l. and/or its affiliated companies
#
# SPDX-License-Identifier: MPL-2.0

# /IOTCONNECT-enabled version of the Edge Speech Assistant (Arduino VENTUNO Q example).
# The upstream app is kept as it is: the web UI's "speak" and "stop" messages drive the tts brick
# and the UI gets the same "speaking" status events. Around that, this version publishes one
# /IOTCONNECT telemetry message when a speech starts and one when it finishes (or is stopped),
# and takes the "speak" and "stop" commands from the cloud. As upstream, stop means silence: it
# interrupts the current speech and discards the ones still waiting for the speaker. It is written against the
# /IOTCONNECT brick (bricks/iotconnect, see bricks/iotconnect/README.md) in direct mode:
#   bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER> --direct
# App Lab puts /app/bricks on PYTHONPATH, which is what makes `from iotconnect import IoTConnect` work.

import threading
import time

from arduino.app_bricks.tts import TextToSpeech
from arduino.app_peripherals.speaker import SpeakerOpenError
from arduino.app_bricks.web_ui import WebUI
from arduino.app_utils import App

# ---- /IOTCONNECT brick ----
from iotconnect import IoTConnect

UNOQ_DEMO_NAME = "edge-speech-assistant"
PREVIEW_CHARS = 200

message_count = 0  # speak requests since the app started, from the web UI and from /IOTCONNECT
speech_lock = threading.Lock()  # one speech at a time: the tts brick plays through a single speaker
stop_requested = threading.Event()  # set by stop (web UI or cloud) while a speech is playing
stop_generation = 0  # bumped by every stop: a speech requested before a stop is discarded, not played after it

TTS_UNAVAILABLE = "no speaker: plug a USB speaker into the VENTUNO Q and restart the app"
try:
    tts = TextToSpeech()  # the tts brick opens the first USB speaker
except SpeakerOpenError as e:
    # Without a speaker the upstream example exits here, which also takes the device offline. Keep the app and
    # its cloud connection up instead: speak requests get a failed ack and an error status in the telemetry.
    print(f"TextToSpeech unavailable: {e}")
    tts = None
ui = WebUI()
iotc = IoTConnect()  # mode, credentials folder and relay endpoint come from the brick's variables


def _preview(text) -> str:
    return " ".join(str(text or "").split())[:PREVIEW_CHARS]


def send_telemetry(text="", source="web_ui", elapsed_ms=0, status="started") -> bool:
    payload = {
        "UnoQdemo": UNOQ_DEMO_NAME,
        "source": source,
        "message_count": int(message_count),
        "prompt_preview": _preview(text),
        "prompt_chars": len(str(text or "")),
        "processing_time_ms": int(elapsed_ms),
        "status": status,
    }
    print("IOTCONNECT send:", payload)
    ok = iotc.send_telemetry(payload)
    print("IOTCONNECT send result:", ok)
    return ok


# ---- shared helpers: the web UI handlers and the /IOTCONNECT commands both go through these ----
def speak_text(text: str, source: str = "web_ui", requested_gen: int | None = None) -> None:
    """Speak one text: the upstream "speaking" UI messages around tts.speak(), plus telemetry.

    requested_gen is the stop_generation seen when the speech was requested (now, when omitted): a stop
    that arrives before the speech gets the speaker discards it, so that Stop means silence, as upstream.
    """
    global message_count
    gen = stop_generation if requested_gen is None else requested_gen
    with speech_lock:
        message_count += 1
        if stop_generation != gen:
            print(f"speech discarded ({source}): a stop arrived before it could start")
            send_telemetry(text, source, 0, "stopped")
            return
        stop_requested.clear()
        ui.send_message("speaking", {"status": "started"})
        send_telemetry(text, source, 0, "started")
        started = time.time()
        try:
            if tts is None:
                raise SpeakerOpenError(TTS_UNAVAILABLE)
            tts.speak(text)  # blocks until synthesis and playback are done (or cancelled)
            status = "stopped" if stop_requested.is_set() else "finished"
        except Exception as e:
            print(f"tts.speak failed: {e}")
            status = f"error:{e}"
        ui.send_message("speaking", {"status": "finished"})
        send_telemetry(text, source, (time.time() - started) * 1000, status)


def stop_speech(source: str = "web_ui") -> None:
    """Interrupt the current speech, as the upstream stop handler does, and drop the ones waiting behind it."""
    global stop_generation
    print(f"speech stop requested ({source})")
    stop_generation += 1
    stop_requested.set()
    if tts is not None:
        tts.cancel()
    ui.send_message("speaking", {"status": "finished"})


# ---- /IOTCONNECT commands ----
@iotc.command("speak")
def on_speak(args: list[str]) -> str | bool:
    """speak <text...>: say the text through the speaker.

    The cloud splits the parameter on whitespace, so the words are joined back with single spaces.
    """
    text = " ".join(args).strip()
    print(f"IOTCONNECT command: speak {text!r}")
    if not text:
        print("IOTCONNECT speak: empty text")
        return False  # failed ack
    # tts.speak() blocks for the whole playback: run it on its own thread so the ack goes out now
    if tts is None:
        print(f"IOTCONNECT speak: {TTS_UNAVAILABLE}")
        send_telemetry(text, "iotconnect", 0, f"error:{TTS_UNAVAILABLE}")
        raise RuntimeError(TTS_UNAVAILABLE)  # failed ack, so the cloud sees why
    gen = stop_generation  # a stop that comes in after this request must silence this speech too
    threading.Thread(target=speak_text, args=(text, "iotconnect", gen), daemon=True).start()
    return f"speaking {len(text)} chars"


@iotc.command("stop")
def on_stop(args: list[str]) -> str:
    """stop: interrupt the current speech."""
    print("IOTCONNECT command: stop")
    stop_speech("iotconnect")
    return "stopped"


# ---- web UI handlers (upstream behaviour) ----
def speak(session_id, data):
    text = data.get("text", "").strip()
    if not text:
        return

    speak_text(text, "web_ui")


def stop(session_id, data):
    stop_speech("web_ui")


ui.on_message("speak", speak)
ui.on_message("stop", stop)

App.run()
