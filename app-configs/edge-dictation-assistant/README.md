# /IOTCONNECT-Enabled: edge-dictation-assistant

This is the /IOTCONNECT-enabled version of the Arduino VENTUNO Q example "Edge Dictation Assistant".

Original Arduino README (VENTUNO Q example):
- https://github.com/arduino/app-bricks-examples

**Board:** Arduino VENTUNO Q only: uses the `arduino:asr` brick, which needs the VENTUNO Q's NPU.

## Overview
This version adds the /IOTCONNECT brick (direct mode), a device template, telemetry and command handling so the app can publish every final transcription chunk to /IOTCONNECT and start, stop and configure dictations from the cloud. It is written directly against the brick's API (`bricks/iotconnect/README.md`): there is no relay client and no `iotc_relay_client` import.

## What This Adds
- /IOTCONNECT brick wiring (`from iotconnect import IoTConnect`, direct mode)
- Device template for telemetry + commands
- Telemetry per final transcription chunk, plus `listening` / `stopped` status messages
- Commands `start-dictation`, `stop-dictation` and `set-language`
- Debug logs for telemetry sends and command handling

App Lab folder: `/home/arduino/ArduinoApps/<APP_LAB_FOLDER>`

## Files
- `python/main.py` (/IOTCONNECT-enabled app code, written against the brick API)
- `config.json` (telemetry/command definitions)
- `edge-dictation-assistant-dashboard-template.json` (exported /IOTCONNECT dashboard, see below)
- `dashboard-images/` (the title panel and status images the dashboard shows)
- `device-template.json` (per-example /IOTCONNECT device template)

The upstream example has no other Python module. The web UI (`assets/`) is used unchanged from your App Lab copy of the example.

## Additional Hardware Required
As listed in the upstream README:
- Microphone or headset: USB, or 3.5 mm jack through the [Arduino UNO Media Carrier](https://store.arduino.cc/products/uno-media-carrier).

## Device Template
Quickstart: use the shared master template at `app-configs/arduino-app-lab-template.json`. It is imported once during onboarding and contains the telemetry fields and commands of every example, so a single device can run all of them.
- Template code: `arduino`
- Template name: `arduino`

Optional: `device-template.json` in this folder is a per-example template containing only this app's fields. Import it and bind a separate device to it if you prefer one template per example.
- Template code: `VQEDA`
- Template name: `VentunoQDictation`

## /IOTCONNECT Dynamic Dashboard

Dashboard template file: [edge-dictation-assistant-dashboard-template.json](edge-dictation-assistant-dashboard-template.json)

What it shows: a status image driven by `status` (`listening`, `ok`, `stopped`), a gauge of `message_count`, the latest `transcript` and `status`, a bar chart of recent `message_count`, a latest-values panel, 3 one-click command buttons and a panel for sending any command by hand.

The widgets load their images from `https://avnetpublicaccess.s3.us-east-1.amazonaws.com/images/arduino/`, so upload the 4 files in [dashboard-images/](dashboard-images/) to that bucket path before importing (the file names must stay the same).

Import into /IOTCONNECT:
1. Open /IOTCONNECT and go to **Dashboard**.
2. Click **Import Dashboard** and upload the JSON file linked above.
3. Save it and map it to your device. The file is bound to the VENTUNO Q device `ventunoQ0` on the `arduino`
   master template; on import, remap it to whichever device on that template runs this example.
4. Open the dashboard in live mode and run the app: the widgets populate from telemetry.

## Telemetry Fields
| Field | Type |
| --- | --- |
| `UnoQdemo` | `STRING` |
| `source` | `STRING` |
| `message_count` | `INTEGER` |
| `transcript` | `STRING` |
| `language` | `STRING` |
| `status` | `STRING` |

Every final transcription chunk (the `full_text` events the web UI appends to the dictation; partial text is not sent) produces one message with `status` = `ok`, the chunk's text in `transcript` (trimmed to 200 characters) and `message_count` = the number of final chunks since the app started. A dictation also sends `status` = `listening` when it starts and `stopped` when it ends; those two carry only `UnoQdemo`, `source`, `language` and `status`. `source` is `web_ui` for dictations started with the microphone button and `iotconnect` for ones started with the `start-dictation` command. `language` is the code chosen in the UI or with `set-language`, or `auto` while the model detects it on its own. Final chunks with no text (the web UI ignores those as well) are not sent.

## Commands
| Command | Parameters |
| --- | --- |
| `start-dictation` | `seconds` |
| `stop-dictation` | `(none)` |
| `set-language` | `language` |

`start-dictation` does what the microphone button does: it transcribes from the microphone, forwards the text to the web UI and publishes telemetry, and stops itself after `seconds` (`15` when the parameter is empty; any number greater than 0). The ack fails while a dictation is already running, from the UI or from an earlier command. `stop-dictation` ends the running dictation, whichever side started it (ack `stopped`). `set-language <code>` selects the transcription language for the next dictation (`en`, `it`, `es`, `de`, `fr`, `pt`, `nl`, `ja`, `pl`, ...; ack `language <code>`), the same thing the UI's language picker does.

## How to Use in App Lab
1) In App Lab, go to **Examples** -> **Edge Dictation Assistant** -> **Copy and edit app** and give the copy a name (that is `<APP_LAB_FOLDER>` below).
2) Copy the /IOTCONNECT-enabled python files into the app:
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/edge-dictation-assistant/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   ```
3) Add the /IOTCONNECT brick to the app in direct mode:
   ```bash
   bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER> --direct
   ```
   The device credentials come from `scripts/credentials.sh` (section 3 of the main README); on the VENTUNO Q they live in `$HOME/.iotconnect`. If the script reports missing credential files, tell it where they are: `bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER> --direct --creds-from $HOME/.iotconnect`.
4) Get the model onto the board, once: the `asr` brick runs **Whisper Small (quantized)** (343 MB). The first time
   you run the app on a board without it, App Lab sees that the model is missing and asks you to download it;
   accept and wait. To download ahead of time, or to check, open your copy of the app, select the **Automatic
   Speech Recognition (ASR)** brick in the **Bricks** section of the editor sidebar and open **AI Models**: the
   model's card shows **Download** or **Installed**. From the board's terminal instead:
   `arduino-app-cli model install whisper-small-quantized`.
5) Run the app, open its web UI (`<VENTUNO-IP-ADDRESS>:7000`), start a dictation with the microphone button (or send `start-dictation` from /IOTCONNECT) and verify the telemetry in /IOTCONNECT.

## Notes
- The ASR model runs entirely on the VENTUNO Q; the first dictation after startup can take a moment while the model loads.
- Telemetry is sent only while someone dictates: nothing shows up in /IOTCONNECT until a dictation starts.
- The web UI stops a dictation on its own after 20 s without any transcription. Text from a dictation started with `start-dictation` appears in the web UI only while its microphone button is active, because the UI ignores transcription events while it is not recording; the telemetry is sent either way.
- `set-language` (and the UI picker) takes effect on the next dictation, not on one that is already running.
- Direct mode copies the device credentials into the app folder (`data/iotconnect`); delete that folder before exporting or sharing the app.
- If you change the device template in /IOTCONNECT, re-create the device or update it to match these fields.
