# SPDX-FileCopyrightText: Copyright (C) ARDUINO SRL (http://www.arduino.cc)
#
# SPDX-License-Identifier: MPL-2.0

from arduino.app_utils import App
from arduino.app_bricks.web_ui import WebUI
from arduino.app_bricks.image_classification import ImageClassification
from PIL import Image
import io
import base64
import time
import json
import requests
import shlex
import traceback

# ---- /IOTCONNECT brick ----
# Brick variant of ../python/main.py: same telemetry fields and commands, written against the brick's API
# (bricks/iotconnect/README.md) instead of the relay client. The app must have the brick installed:
#   bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER>
from iotconnect import IoTConnect

UNOQ_DEMO_NAME = "image-classification"
DEFAULT_CONFIDENCE = 0.25
CURRENT_CONFIDENCE = DEFAULT_CONFIDENCE

image_classification = ImageClassification()
iotc = IoTConnect()  # mode, credentials and relay endpoint come from the brick's variables


@iotc.command("set-confidence")
def on_set_confidence(args: list[str]) -> str:
    """set-confidence <0..1>: minimum confidence for classification results."""
    global CURRENT_CONFIDENCE
    CURRENT_CONFIDENCE = max(0.0, min(1.0, float(args[0])))  # a bad value raises -> failed ack
    print(f"IOTCONNECT confidence set to {CURRENT_CONFIDENCE}")
    return f"confidence {CURRENT_CONFIDENCE}"


@iotc.command("classify-image")
def on_classify_command(args: list[str]):
    """classify-image <image_url> [image_type] [confidence], or one JSON object with those keys."""
    raw = " ".join(args).strip()
    if raw.startswith("{"):
        payload = json.loads(raw)
    else:
        try:
            tokens = shlex.split(raw)  # quoted URLs work, as with the classic client
        except ValueError:
            tokens = args
        payload = {}
        if len(tokens) >= 1:
            payload["image_url"] = tokens[0]
        if len(tokens) >= 2:
            payload["image_type"] = tokens[1]
        if len(tokens) >= 3:
            payload["confidence"] = float(tokens[2])
    print(f"IOTCONNECT classify-image payload: {payload!r}")
    sent = on_classify_image("iotc", payload)
    if not sent or sent.get("status") != "ok":
        return False  # failed ack
    return f"{sent.get('top_class_name') or 'no class'} ({sent.get('top_confidence', 0.0):.2f})"


def send_telemetry(payload):
    payload.setdefault("UnoQdemo", UNOQ_DEMO_NAME)
    print("IOTCONNECT send:", payload)
    ok = iotc.send_telemetry(payload)
    print("IOTCONNECT send result:", ok)
    return payload


def parse_data(data):
    if isinstance(data, str):
        try:
            return json.loads(data)
        except Exception:
            return {}
    return data if isinstance(data, dict) else {}


def pick_top_result(results):
    if isinstance(results, dict) and isinstance(results.get("classification"), list):
        first = results.get("classification")[0] if results.get("classification") else None
        if isinstance(first, dict):
            return first.get("class_name") or first.get("label"), first.get("confidence") or first.get("score")
    if isinstance(results, dict):
        if 'class_name' in results and 'confidence' in results:
            return results.get('class_name'), results.get('confidence')
    if isinstance(results, list) and results:
        first = results[0]
        if isinstance(first, dict):
            return first.get('class_name') or first.get('label'), first.get('confidence') or first.get('score')
    return None, None


def on_classify_image(client_id, data):
    """Classifies one image (from the web UI or a cloud command) and reports it. Returns the telemetry sent."""
    try:
        parsed = parse_data(data)
        image_data = parsed.get('image')
        image_url = parsed.get('image_url')
        image_type_raw = parsed.get('image_type')
        if image_type_raw:
            image_type = image_type_raw.split('/')[-1]
        else:
            image_type = 'jpeg'
        confidence = parsed.get('confidence', CURRENT_CONFIDENCE)

        if not image_data and not image_url:
            ui.send_message('classification_error', {'error': 'No image data'})
            return send_telemetry({
                "status": "error",
                "class_name": "",
                "confidence": float(confidence) if confidence is not None else 0.0,
                "processing_time_ms": 0,
                "input_type": "none",
                "image_type": image_type,
                "results_json": "[]",
            })

        input_type = "upload"
        if image_url and not image_data:
            input_type = "url"
            try:
                resp = requests.get(image_url, timeout=10)
                resp.raise_for_status()
                image_bytes = resp.content
            except Exception as e:
                ui.send_message('classification_error', {'error': f'Failed to fetch image_url: {e}'})
                return send_telemetry({
                    "status": "error",
                    "class_name": "",
                    "confidence": float(confidence) if confidence is not None else 0.0,
                    "processing_time_ms": 0,
                    "input_type": input_type,
                    "image_type": image_type,
                    "results_json": "[]",
                })
        else:
            image_bytes = base64.b64decode(image_data)

        pil_image = Image.open(io.BytesIO(image_bytes))

        start_time = time.time() * 1000
        results = image_classification.classify(pil_image, image_type=image_type, confidence=confidence)
        print("RAW RESULTS:", results)
        diff = time.time() * 1000 - start_time

        if results is None:
            ui.send_message('classification_error', {'error': 'No results returned'})
            return send_telemetry({
                "status": "error",
                "class_name": "",
                "confidence": float(confidence) if confidence is not None else 0.0,
                "processing_time_ms": int(diff),
                "input_type": input_type,
                "image_type": image_type,
                "results_json": "[]",
            })

        response = {
            'success': True,
            'results': results,
            'processing_time': f"{diff:.2f} ms"
        }
        ui.send_message('classification_result', response)

        class_name, top_conf = pick_top_result(results)
        return send_telemetry({
            "status": "ok",
            "class_name": class_name or "",
            "confidence": float(top_conf) if top_conf is not None else float(confidence),
            "processing_time_ms": int(diff),
            "input_type": input_type,
            "image_type": image_type,
            "results_json": json.dumps(results),
            "top_class_name": class_name or "",
            "top_confidence": float(top_conf) if top_conf is not None else float(confidence),
        })

    except Exception as e:
        print(f"on_classify_image error: {e}")
        print(traceback.format_exc())
        ui.send_message('classification_error', {'error': str(e)})
        return send_telemetry({
            "status": "error",
            "class_name": "",
            "confidence": float(CURRENT_CONFIDENCE),
            "processing_time_ms": 0,
            "input_type": "error",
            "image_type": "",
            "results_json": "[]",
        })


ui = WebUI()
ui.on_message('classify_image', on_classify_image)

App.run()
