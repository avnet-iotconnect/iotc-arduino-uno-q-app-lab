# /IOTCONNECT-Enabled: edge-ai-assistant

This is the /IOTCONNECT-enabled version of the Arduino example.

Original Arduino README:
- https://github.com/arduino/app-bricks-examples/blob/main/inspirational/platform_unoq/edge-ai-assistant/README.md

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

The upstream `python/prompts.py` and `python/system_prompt.txt` are used unchanged from your App Lab copy of the example.

## Device Template
This app uses the shared device template at `app-configs/arduino-app-lab-template.json`.
- Template code: `arduino`
- Template name: `arduino`

## Telemetry Fields
| Field | Type |
| --- | --- |
| `UnoQdemo` | `STRING` |
| `model` | `STRING` |
| `source` | `STRING` |
| `message_count` | `INTEGER` |
| `prompt_preview` | `STRING` |
| `prompt_chars` | `INTEGER` |
| `response_preview` | `STRING` |
| `response_chars` | `INTEGER` |
| `processing_time_ms` | `INTEGER` |
| `status` | `STRING` |

Each prompt produces two messages: `status` = `requested` when it is sent to the model, and `complete` (with the response preview and timing) when streaming ends. `source` is `web_ui` or `iotconnect` depending on where the prompt came from. Previews are trimmed to 200 characters. `processing_time_ms` is a useful gauge of on-device inference speed.

## Commands
| Command | Parameters |
| --- | --- |
| `ask` | `prompt` |
| `clear-chat` | `(none)` |

`ask` sends a prompt to the local model from /IOTCONNECT; the answer streams to the web UI and its preview is returned in telemetry. The parameter can be plain text (`What is an Arduino?`) or JSON (`{"prompt":"What is an Arduino?"}`).

## How to Use in App Lab
1) Copy the example into your App Lab workspace.
2) Copy the /IOTCONNECT-enabled python files into the app:
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/edge-ai-assistant/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/

   cp /opt/demo/iotc_relay_client.py /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   ```
3) Run the app and verify telemetry in /IOTCONNECT.

## Notes
- The model runs entirely on the UNO Q; the first response after startup can take a while as the model loads.
- If the example sends telemetry only on user action, you will not see data until that action occurs.
- If you change the device template in /IOTCONNECT, re-create the device or update it to match these fields.
