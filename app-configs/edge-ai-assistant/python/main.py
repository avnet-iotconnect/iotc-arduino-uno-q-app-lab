# SPDX-FileCopyrightText: Copyright (C) Arduino s.r.l. and/or its affiliated companies
#
# SPDX-License-Identifier: MPL-2.0

# AI USAGE DISCLAIMER
# This application is meant to demonstrate the capabilities of different LLM models
# as they are, hence your prompt and the LLM answer are unfiltered. Use AI responsibly.
# Applications meant for final usage are recommended to include guardrails to filter
# unwanted prompts and answers.

import json
import threading
import time
from arduino.app_bricks.llm import LargeLanguageModel
from arduino.app_bricks.web_ui import WebUI
from arduino.app_utils import App
from prompts import load_system_prompt

# ---- IOTCONNECT Relay ----
from iotc_relay_client import IoTConnectRelayClient

RELAY_ENDPOINT = "tcp://172.17.0.1:8899"
RELAY_CLIENT_ID = "edge_ai_assistant"
UNOQ_DEMO_NAME = "edge-ai-assistant"
MODEL_NAME = "edge-llm"
PREVIEW_CHARS = 200

message_count = 0
chat_lock = threading.Lock()

relay = IoTConnectRelayClient(
    RELAY_ENDPOINT,
    client_id=RELAY_CLIENT_ID,
)
relay.start()


def _preview(text) -> str:
    return " ".join(str(text or "").split())[:PREVIEW_CHARS]


def send_telemetry(prompt="", response="", elapsed_ms=0, source="web_ui", status="ok"):
    payload = {
        "UnoQdemo": UNOQ_DEMO_NAME,
        "model": MODEL_NAME,
        "source": source,
        "message_count": int(message_count),
        "prompt_preview": _preview(prompt),
        "prompt_chars": len(str(prompt or "")),
        "response_preview": _preview(response),
        "response_chars": len(str(response or "")),
        "processing_time_ms": int(elapsed_ms),
        "status": status,
    }
    print("IOTCONNECT send:", payload)
    relay.send_telemetry(payload)


def run_prompt(prompt: str, source: str = "web_ui"):
    """Stream one prompt through the local LLM to the web UI and publish telemetry."""
    global message_count
    with chat_lock:
        message_count += 1
        send_telemetry(prompt, source=source, status="requested")
        started = time.time()
        chunks = []
        try:
            # Use the plain text prompt for the LLM and stream the response
            for resp in llm.chat_stream(prompt):
                chunks.append(str(resp))
                ui.send_message("response", resp)

            # Signal the end of the stream
            ui.send_message("stream_end", {})
            send_telemetry(prompt, "".join(chunks), (time.time() - started) * 1000, source, "complete")
        except Exception as e:
            ui.send_message("llm_error", {"error": str(e)})
            send_telemetry(prompt, "".join(chunks), (time.time() - started) * 1000, source, f"error:{e}")


def generate_prompt(_, data):
    run_prompt(data.get("prompt", ""), "web_ui")


def clear_chat():
    global message_count
    llm.stop_stream()
    llm.clear_memory()
    message_count = 0


def commands_handler(_, data):
    command = data.get("command", "")
    try:
        if command == "clear_chat":
            clear_chat()
            ui.send_message("command_ok", {"command": command})
            send_telemetry(status="cleared")
        elif command == "stop_stream":
            llm.stop_stream()
            ui.send_message("command_ok", {"command": command})
            send_telemetry(status="stopped")
        else:
            ui.send_message(
                "command_error", {"command": command, "error": "Unknown command"}
            )
    except Exception as e:
        ui.send_message("command_error", {"command": command, "error": str(e)})


# ---- IOTCONNECT command handling ----
def _param_text(parameters, key="prompt") -> str:
    """Accept {"prompt": "..."} or a plain text parameter."""
    data = parameters
    if isinstance(data, (list, tuple)) and len(data) == 1:
        data = data[0]
    if isinstance(data, (bytes, bytearray)):
        data = data.decode("utf-8", errors="strict")
    if isinstance(data, str):
        s = data.strip()
        try:
            parsed = json.loads(s)
        except Exception:
            return s
        if not isinstance(parsed, dict):
            return s
        data = parsed
    if isinstance(data, dict):
        return str(data.get(key, next(iter(data.values()), "")))
    return str(data if data is not None else "")


def on_relay_command(command_name, parameters):
    print(f"IOTCONNECT command: {command_name} {parameters}")
    if command_name in ("ask", "prompt"):
        prompt = _param_text(parameters, "prompt").strip()
        if not prompt:
            send_telemetry(source="iotconnect", status="error:empty prompt")
            return
        # Run off the relay thread so streaming does not block command delivery
        threading.Thread(target=run_prompt, args=(prompt, "iotconnect"), daemon=True).start()
    elif command_name in ("clear-chat", "clear_chat"):
        try:
            clear_chat()
            ui.send_message("command_ok", {"command": "clear_chat"})
            send_telemetry(source="iotconnect", status="cleared")
        except Exception as e:
            send_telemetry(source="iotconnect", status=f"error:{e}")


relay.command_callback = on_relay_command

llm = LargeLanguageModel(system_prompt=load_system_prompt())

llm.with_memory(10)

ui = WebUI()

ui.on_message("prompt", generate_prompt)
ui.on_message("commands", commands_handler)

App.run()
