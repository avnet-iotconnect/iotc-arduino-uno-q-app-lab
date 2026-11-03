# /IOTCONNECT-Enabled: telegram-bot

This is the /IOTCONNECT-enabled version of the Arduino example.

Original Arduino README:
- https://github.com/arduino/app-bricks-examples/blob/main/inspirational/common/telegram-bot/README.md

## Overview
This version adds an /IOTCONNECT relay client, a device template, and optional command handling so the app can publish telemetry and receive commands from /IOTCONNECT.

## What This Adds
- /IOTCONNECT relay client wiring
- Device template for telemetry + commands
- Optional commands (if defined below)
- Optional debug logs for telemetry send

App Lab folder: `/home/arduino/ArduinoApps/<APP_LAB_FOLDER>`

## Files
- `python/main.py` (/IOTCONNECT-enabled app code)
- `config.json` (telemetry/command definitions)

## Device Template
This app uses the shared device template at `app-configs/arduino-app-lab-template.json`.
- Template code: `arduino`
- Template name: `arduino`

## Telemetry Fields
| Field | Type |
| --- | --- |
| `UnoQdemo` | `STRING` |
| `action` | `STRING` |
| `sender_name` | `STRING` |
| `message_count` | `INTEGER` |
| `mood` | `STRING` |
| `detection_count` | `INTEGER` |
| `detections_json` | `STRING` |
| `status` | `STRING` |

One message is sent per handled chat event. `action` is `hello`, `help`, `text` (mood detection, result in `mood`), `photo` (object detection, results in `detection_count` / `detections_json`) or `send-message`. `message_count` counts chat events since the app started.

## Commands
| Command | Parameters |
| --- | --- |
| `send-message` | `text` |

`send-message` replies to the most recent Telegram chat that messaged the bot. The parameter can be plain text (`Hello from the cloud`) or JSON (`{"text":"Hello from the cloud"}`). If nobody has messaged the bot since startup, the command is rejected with `status` = `error:no chat yet, message the bot first`.

## How to Use in App Lab
1) Copy the example into your App Lab workspace.
2) Copy the /IOTCONNECT-enabled python files into the app:
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/telegram-bot/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/

   cp /opt/demo/iotc_relay_client.py /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   ```
3) Run the app, message the bot from Telegram, and verify telemetry in /IOTCONNECT.

## Notes
- This example needs an internet connection, a Telegram account, and a bot token from BotFather configured in the Telegram Bot brick settings in App Lab (see the original Arduino README).
- If the example sends telemetry only on user action, you will not see data until that action occurs.
- If you change the device template in /IOTCONNECT, re-create the device or update it to match these fields.
