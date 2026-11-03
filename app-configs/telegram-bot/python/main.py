# SPDX-FileCopyrightText: Copyright (C) Arduino s.r.l. and/or its affiliated companies
#
# SPDX-License-Identifier: MPL-2.0

#

# EXAMPLE_NAME = "Telegram bot"

import json
from arduino.app_bricks.telegram_bot import TelegramBot, Sender, Message
from arduino.app_bricks.object_detection import ObjectDetection
from arduino.app_bricks.mood_detector import MoodDetector
from arduino.app_utils import App
from PIL import Image
from io import BytesIO

# ---- IOTCONNECT Relay ----
from iotc_relay_client import IoTConnectRelayClient

RELAY_ENDPOINT = "tcp://172.17.0.1:8899"
RELAY_CLIENT_ID = "telegram_bot"
UNOQ_DEMO_NAME = "telegram-bot"

message_count = 0
last_sender = None

# Initialize bricks
bot = TelegramBot()
obj_detection = ObjectDetection()
mood = MoodDetector()

relay = IoTConnectRelayClient(
    RELAY_ENDPOINT,
    client_id=RELAY_CLIENT_ID,
)
relay.start()


def _sender_name(sender) -> str:
    if sender is None:
        return ""
    return str(getattr(sender, "first_name", None) or getattr(sender, "username", None) or "")


def _remember(sender):
    global last_sender, message_count
    last_sender = sender
    message_count += 1


def send_telemetry(action, sender=None, mood_result="", detections=None, status="ok"):
    det_list = detections or []
    payload = {
        "UnoQdemo": UNOQ_DEMO_NAME,
        "action": str(action),
        "sender_name": _sender_name(sender),
        "message_count": int(message_count),
        "mood": str(mood_result or ""),
        "detection_count": len(det_list),
        "detections_json": json.dumps(det_list),
        "status": status,
    }
    print("IOTCONNECT send:", payload)
    relay.send_telemetry(payload)


def _detection_summary(results) -> list:
    """Reduce ObjectDetection results to [{"class_name", "confidence"}, ...]."""
    items = []
    entries = results.get("detection", []) if isinstance(results, dict) else []
    for d in entries:
        if isinstance(d, dict):
            name = d.get("class_name", d.get("label", d.get("name", d.get("class", ""))))
            conf = d.get("confidence", d.get("score", 0.0))
            try:
                conf = float(conf)
            except (TypeError, ValueError):
                conf = 0.0
            items.append({"class_name": str(name), "confidence": conf})
        else:
            items.append({"class_name": str(d), "confidence": 0.0})
    return items


def greet(sender: Sender, message: Message):
    """Handle /hello command - super simple API with reply helper!"""
    _remember(sender)
    sender.reply(f"👋 Hi {sender.first_name}! This is Arduino UNO Q!")
    send_telemetry("hello", sender)


def help_cmd(sender: Sender, message: Message):
    """Handle /help command"""
    _remember(sender)
    help_text = (
        "🤖 *Arduino Bot Commands:*\n\n"
        "/hello - Get a greeting\n"
        "/help - Show this help\n\n"
        "Send me:\n"
        "📝 Text for mood detection\n"
        "📷 Photo for object detection\n"
    )
    sender.reply(help_text)
    send_telemetry("help", sender)


def sentiment(sender: Sender, message: Message):
    """Reply sentiment analysis for text messages - using convenient reply helper!"""
    if message.text is None:
        return  # on_text only delivers text messages, but text is optional in the Message contract
    _remember(sender)
    try:
        result = mood.get_sentiment(message.text)
        sender.reply(f"Your mood is: {result}")
        send_telemetry("text", sender, mood_result=result)
    except Exception as e:
        send_telemetry("text", sender, status=f"error:{e}")


def detect_objects(
    sender: Sender,
    message: Message,
    photo: bytes,
    filename: str,
    size: int,
):
    """Detect objects in photos - photo data passed as parameter!"""
    _remember(sender)
    # Notify user we're processing
    sender.reply("📷 Detecting objects...")

    try:
        # Process image
        image = Image.open(BytesIO(photo))
        results = obj_detection.detect(image, confidence=0.1)
        img_with_boxes = obj_detection.draw_bounding_boxes(image, results)
        if results is None or img_with_boxes is None:
            sender.reply("No objects detected")
            send_telemetry("photo", sender, status="no_objects")
            return

        # Send result using reply_photo helper
        output = BytesIO()
        img_with_boxes.save(output, format="PNG")
        output.seek(0)

        det_list = _detection_summary(results)
        caption = f"✅ Found {len(results['detection'])} object(s)!"

        if not sender.reply_photo(output.getvalue(), caption):
            sender.reply("❌ Failed to send processed image")
            send_telemetry("photo", sender, detections=det_list, status="error:reply_photo failed")
            return
        send_telemetry("photo", sender, detections=det_list)
    except Exception as e:
        send_telemetry("photo", sender, status=f"error:{e}")


# ---- IOTCONNECT command handling ----
def _param_text(parameters, key="text") -> str:
    """Accept {"text": "..."} or a plain text parameter."""
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
    if command_name in ("send-message", "send_message"):
        text = _param_text(parameters, "text").strip()
        if not text:
            send_telemetry("send-message", last_sender, status="error:empty text")
            return
        if last_sender is None:
            send_telemetry("send-message", status="error:no chat yet, message the bot first")
            return
        try:
            last_sender.reply(text)
            send_telemetry("send-message", last_sender)
        except Exception as e:
            send_telemetry("send-message", last_sender, status=f"error:{e}")


relay.command_callback = on_relay_command

# Register handlers
bot.add_command("hello", greet, "Get a personalized greeting")
bot.add_command("help", help_cmd, "Show available commands")
bot.on_text(sentiment)
bot.on_photo(detect_objects)

# Start the Arduino App framework
App.run()
