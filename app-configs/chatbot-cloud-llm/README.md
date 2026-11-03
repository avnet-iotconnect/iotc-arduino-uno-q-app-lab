# /IOTCONNECT-Enabled: chatbot-cloud-llm

This is the /IOTCONNECT-enabled version of the Arduino example.

Original Arduino README:
- https://github.com/arduino/app-bricks-examples/blob/main/inspirational/common/chatbot-cloud-llm/README.md

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

The upstream `python/system_prompt.txt` is used unchanged from your App Lab copy of the example.

## Device Template
Quickstart: use the shared master template at `app-configs/arduino-app-lab-template.json`. It is imported once during onboarding and contains the telemetry fields and commands of every example, so a single device can run all of them.
- Template code: `arduino`
- Template name: `arduino`

Optional: `device-template.json` in this folder is a per-example template containing only this app's fields. Import it and bind a separate device to it if you prefer one template per example.
- Template code: `UnoQCCL`
- Template name: `UnoQChatbotCloudLlm`

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

Each prompt produces two messages: `status` = `requested` when it is sent to the model, and `complete` (with the response preview and timing) when streaming ends. `source` is `web_ui` or `iotconnect` depending on where the prompt came from. Previews are trimmed to 200 characters.

## Commands
| Command | Parameters |
| --- | --- |
| `ask` | `prompt` |
| `clear-chat` | `(none)` |

`ask` sends a prompt to the model from /IOTCONNECT; the answer streams to the web UI and its preview is returned in telemetry. The parameter can be plain text (`What is an Arduino?`) or JSON (`{"prompt":"What is an Arduino?"}`).

## How to Use in App Lab
1) Copy the example into your App Lab workspace.
2) Copy the /IOTCONNECT-enabled python files into the app:
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/chatbot-cloud-llm/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/

   cp /opt/demo/iotc_relay_client.py /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   ```
   **Or, with the /IOTCONNECT brick** (same telemetry and commands, no code changes; the brick replaces the relay client copy):
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/chatbot-cloud-llm/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER>
   ```
   Either way, `bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER> --remove` goes back to the classic relay client.
3) Run the app and verify telemetry in /IOTCONNECT.

## Notes
- This example needs an internet connection and a valid API key for the cloud LLM provider, configured in the Cloud LLM brick settings in App Lab (see the original Arduino README).
- If the example sends telemetry only on user action, you will not see data until that action occurs.
- If you change the device template in /IOTCONNECT, re-create the device or update it to match these fields.
