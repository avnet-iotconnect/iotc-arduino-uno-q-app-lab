# /IOTCONNECT-Enabled: edge-speech-assistant

This is the /IOTCONNECT-enabled version of the Arduino VENTUNO Q example.

Original Arduino README (VENTUNO Q example):
- https://github.com/arduino/app-bricks-examples/blob/main/inspirational/platform_ventunoq/edge-speech-assistant/README.md

## Overview
This version adds the /IOTCONNECT brick, a device template, telemetry for every speech request and two cloud commands, so the app can publish telemetry and receive commands from /IOTCONNECT. The app code is written directly against the brick's API (`bricks/iotconnect/README.md`) in direct mode: the app itself is the /IOTCONNECT device, no relay client or relay service is involved.

**Arduino VENTUNO Q only**: uses the `arduino:tts` brick, which needs the VENTUNO Q's NPU. The upstream web UI (text box, Play/Stop toggle, elapsed-time counter) works exactly as before, and a speech started from /IOTCONNECT shows up in the web UI too.

## What This Adds
- /IOTCONNECT brick wiring (`from iotconnect import IoTConnect`), direct mode
- Device template for telemetry + commands
- Telemetry when a speech starts and when it finishes or is stopped
- `speak` and `stop` commands from the cloud, going through the same code as the web UI's Play and Stop
- Debug logs for every telemetry send and command

App Lab folder: `/home/arduino/ArduinoApps/<APP_LAB_FOLDER>`

## Files
- `python/main.py` (/IOTCONNECT-enabled app code; the upstream example has no other python module)
- `config.json` (telemetry/command definitions)
- `edge-speech-assistant-dashboard-template.json` (exported /IOTCONNECT dashboard, see below)
- `dashboard-images/` (the title panel and status images the dashboard shows)
- `device-template.json` (per-example /IOTCONNECT device template)

The upstream web UI under `assets/` is used unchanged from your App Lab copy of the example.

## Additional Hardware Required
- Arduino VENTUNO Q: the `arduino:tts` brick runs the text-to-speech model on its NPU.
- A USB speaker (or USB headset): the `tts` brick plays through the first USB speaker it finds and fails to start if none is plugged in, so connect it before running the app. The upstream README also lists the 3.5 mm jack of the Arduino UNO Media Carrier as an alternative.

## Device Template
Quickstart: use the shared master template at `app-configs/arduino-app-lab-template.json`. It is imported once during onboarding and contains the telemetry fields and commands of every example, so a single device can run all of them.
- Template code: `arduino`
- Template name: `arduino`

Optional: `device-template.json` in this folder is a per-example template containing only this app's fields. Import it and bind a separate device to it if you prefer one template per example.
- Template code: `VQESA`
- Template name: `VentunoQSpeechAssistant`

## /IOTCONNECT Dynamic Dashboard

Dashboard template file: [edge-speech-assistant-dashboard-template.json](edge-speech-assistant-dashboard-template.json)

What it shows: a status image driven by `status` (`started`, `finished`, `stopped`), a gauge of `processing_time_ms`, the latest `prompt_preview` and `status`, a bar chart of recent `prompt_chars`, a latest-values panel, 2 one-click command buttons and a panel for sending any command by hand.

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
| `prompt_preview` | `STRING` |
| `prompt_chars` | `INTEGER` |
| `processing_time_ms` | `INTEGER` |
| `status` | `STRING` |

Each speech request produces two messages: `status` = `started` when the text is handed to the `tts` brick (`processing_time_ms` = 0), and `finished` when playback ends, with `processing_time_ms` the elapsed synthesis + playback time (`stopped` when it was interrupted, `error:<message>` when synthesis failed). A speech that a `stop` discards while it is still waiting for the speaker sends a single `stopped` message with `processing_time_ms` = 0. `source` is `web_ui` or `iotconnect` depending on where the text came from, `message_count` counts the speak requests since the app started, and `prompt_preview` is the spoken text trimmed to 200 characters (`prompt_chars` is its full length).

## Commands
| Command | Parameters |
| --- | --- |
| `speak` | `text` |
| `stop` | `(none)` |

`speak` says the text through the speaker, e.g. `speak Hello from the cloud`. The whole parameter is the text (the words are joined with spaces); the ack is `speaking <n> chars`, playback runs in the background and the telemetry above reports when it finishes. Empty text is acknowledged as failed. `stop` interrupts the current speech and discards any speech still waiting for the speaker (ack `stopped`): like the web UI's Stop button, it means silence. Both commands need "Acknowledgement Required" in the template (the templates in this repo have it).

## How to Use in App Lab
1) In App Lab open **Examples**, pick **Edge Speech Assistant** and click **Copy and edit app**; give the copy a name (its folder is `<APP_LAB_FOLDER>` below).
2) Copy the /IOTCONNECT-enabled python files into the app:
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/edge-speech-assistant/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   ```
3) Add the /IOTCONNECT brick to the app, in direct mode:
   ```bash
   bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER> --direct
   ```
   The device credentials come from `scripts/credentials.sh` (README section 3); on the VENTUNO Q they live in `$HOME/.iotconnect`, and the script copies them into the app's `data/iotconnect/`. The script finds them there on its own; pass `--creds-from <dir>` only if you keep the credentials somewhere else.
4) The **Text-to-Speech (TTS)** brick runs **Piper TTS (English)** (79 MB, CLI id `pipertts_en`). The first time
   you run the app on a board without it, App Lab sees that the model is missing and asks you to download it
   (see Notes); to do it ahead, open your copy of the app, select the brick in the **Bricks** section of the
   editor sidebar, open **AI Models** and click **Download** on its card.
5) Run the app and verify telemetry in /IOTCONNECT: type a text in the web UI (`http://<VENTUNO-Q-IP>:7000`) and press Play, or send `speak <text>` from the device's command page.

## Notes
- Everything runs on the VENTUNO Q: the first launch downloads the audio container and the text-to-speech model, so it can take a few minutes, and the brick installs the /IOTCONNECT Python SDK on the first start (the board needs internet access then).
- Telemetry is sent only on speak requests; you will not see data until a text is spoken.
- One speech plays at a time: a `speak` command received while a text is being spoken waits and starts when the current one ends. A `stop` (web UI or cloud) silences everything: it interrupts the current speech and discards the ones waiting behind it, each reporting `status` = `stopped`.
- The app connects to /IOTCONNECT on its own (direct mode) with the credentials in `data/iotconnect/`: delete that folder before sharing or exporting the app.
- If you change the device template in /IOTCONNECT, re-create the device or update it to match these fields.
- No audio, or "Speaker is busy" at start: see the Troubleshooting section of the upstream README (`aplay -l` lists the speakers the `tts` brick can use).
- Without a USB speaker the upstream example exits at start. This version keeps running and connected: `speak` is acked as failed with the reason and the telemetry reports `status` = `error:no speaker ...`, so the device stays visible in /IOTCONNECT until a speaker is plugged in and the app restarted.
