# /IOTCONNECT-Enabled: edge-ai-assistant

This is the /IOTCONNECT-enabled version of the Arduino example.

Original Arduino README:
- https://github.com/arduino/app-bricks-examples/blob/main/inspirational/platform_unoq/edge-ai-assistant/README.md
- VENTUNO Q variant (same `app.yaml`; the `llm` brick runs Qwen 3-4B Instruct on that board's NPU, and the copy has
  a longer system prompt):
  https://github.com/arduino/app-bricks-examples/blob/main/inspirational/platform_ventunoq/edge-ai-assistant/README.md

**Boards:** UNO Q and VENTUNO Q. On the VENTUNO Q use the "with the /IOTCONNECT brick" lines below (no relay service there,
see the main README's section 7).

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
Quickstart: use the shared master template at `app-configs/arduino-app-lab-template.json`. It is imported once during onboarding and contains the telemetry fields and commands of every example, so a single device can run all of them.
- Template code: `arduino`
- Template name: `arduino`

Optional: `device-template.json` in this folder is a per-example template containing only this app's fields. Import it and bind a separate device to it if you prefer one template per example.
- Template code: `UnoQEAA`
- Template name: `UnoQEdgeAiAssistant`

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
   **Or, with the /IOTCONNECT brick** (same telemetry and commands, no code changes; the brick replaces the relay client copy):
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/edge-ai-assistant/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER>
   ```
   Either way, `bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER> --remove` goes back to the classic relay client.
3) Get the model onto the board, once: the `llm` brick's default is **Qwen 3.5 0.8B** (507 MB) on the UNO Q and
   **Qwen 3-4B Instruct** (3.0 GB) on the VENTUNO Q. The first time you run the app on a board without it, App
   Lab sees that the model is missing and asks you to download it; accept and wait (the 3 GB one takes a while).
   To download ahead of time, or to check, open your copy of the app, select the **Large Language Model (LLM)**
   brick in the **Bricks** section of the editor sidebar and open **AI Models**: the model's card under
   **Suggested models** shows **Download** or **Installed**. From the board's terminal instead:
   `arduino-app-cli model install llamacpp:Qwen3.5-0.8B-Q4_0` (UNO Q) or
   `arduino-app-cli model install genie:qwen3_4b_instruct_2507` (VENTUNO Q).
4) Run the app and verify telemetry in /IOTCONNECT.

## Notes
- The model runs entirely on the board; the first response after startup can take a while as the model loads. The
  upstream VENTUNO Q copy keeps 20 chat messages in memory instead of 10; this version keeps the UNO Q value
  (`llm.with_memory(10)`), change it if you want the longer memory.
- If the example sends telemetry only on user action, you will not see data until that action occurs.
- If you change the device template in /IOTCONNECT, re-create the device or update it to match these fields.
