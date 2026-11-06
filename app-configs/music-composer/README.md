# /IOTCONNECT-Enabled: music-composer

This is the /IOTCONNECT-enabled version of the Arduino example.

Original Arduino README:
- https://github.com/arduino/app-bricks-examples/blob/main/inspirational/common/music-composer/README.md

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
- `music-composer-dashboard-template.json` (exported /IOTCONNECT dashboard, see below)
- `dashboard-images/` (the title panel and status images the dashboard shows)

## Additional Hardware Required

This app plays audio, so the UNO Q needs a speaker.

**Speaker:**
- USB speaker, or a 3.5 mm speaker through the [Arduino UNO Media Carrier](https://store.arduino.cc/products/uno-media-carrier)

**USB-C hub with external power (when using a USB audio device):**
- [Arduino USB-C hub](https://store.arduino.cc/products/usb-c-hub-8-in-1) plus a 5 V / 3 A power supply, because the UNO Q's single USB-C port must feed both power and the audio device. Run the app in Network Mode or SBC Mode in that case.

## Device Template
Quickstart: use the shared master template at `app-configs/arduino-app-lab-template.json`. It is imported once during onboarding and contains the telemetry fields and commands of every example, so a single device can run all of them.
- Template code: `arduino`
- Template name: `arduino`

Optional: `device-template.json` in this folder is a per-example template containing only this app's fields. Import it and bind a separate device to it if you prefer one template per example.
- Template code: `UnoQMC`
- Template name: `UnoQMusicComposer`

## /IOTCONNECT Dynamic Dashboard

Dashboard template file: [music-composer-dashboard-template.json](music-composer-dashboard-template.json)

What it shows: a status image driven by `state` (`playing`, `stopped`), a gauge of `bpm`, the latest `status` and `waveform`, a bar chart of recent `note_count`, 4 one-click command buttons and a panel for sending any command by hand.

The widgets load their images from `https://avnetpublicaccess.s3.us-east-1.amazonaws.com/images/arduino/`, so upload the 3 files in [dashboard-images/](dashboard-images/) to that bucket path before importing (the file names must stay the same).

Import into /IOTCONNECT:
1. Open /IOTCONNECT and go to **Dashboard**.
2. Click **Import Dashboard** and upload the JSON file linked above.
3. Save it and map it to your device. The file is bound to the UNO Q device `unoQ0` on the `arduino`
   master template; on import, remap it to whichever device on that template runs this example.
4. Open the dashboard in live mode and run the app: the widgets populate from telemetry.

## Telemetry Fields
| Field | Type |
| --- | --- |
| `UnoQdemo` | `STRING` |
| `state` | `STRING` |
| `bpm` | `INTEGER` |
| `waveform` | `STRING` |
| `volume` | `INTEGER` |
| `step_count` | `INTEGER` |
| `note_count` | `INTEGER` |
| `effects_json` | `STRING` |
| `status` | `STRING` |

`state` is `playing` or `stopped`. `volume` is 0-100. `step_count` is the length of the sequence built from the grid and `note_count` the number of active notes in it. `status` names the event that triggered the message: `play`, `stop`, `playback_ended`, `grid_updated`, `bpm_set`, `volume_set`, `waveform_set`, `effects_set`, or `error:*`. Grid edits are rate-limited to one message every 2 seconds.

## Commands
| Command | Parameters |
| --- | --- |
| `play` | `(none)` |
| `stop` | `(none)` |
| `set-bpm` | `bpm` |
| `set-volume` | `volume` |
| `set-waveform` | `waveform` |

`set-volume` takes 0-100. `set-waveform` accepts `sine`, `square`, `triangle` or `sawtooth`. Parameters can be plain values (`140`) or JSON (`{"bpm":140}`). As in the original app, BPM cannot be changed while a sequence is playing.

## How to Use in App Lab
1) Copy the example into your App Lab workspace.
2) Copy the /IOTCONNECT-enabled python files into the app:
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/music-composer/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/

   cp /opt/demo/iotc_relay_client.py /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   ```
   **Or, with the /IOTCONNECT brick** (same telemetry and commands, no code changes; the brick replaces the relay client copy):
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/music-composer/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER>
   ```
   Either way, `bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER> --remove` goes back to the classic relay client.
3) Run the app and verify telemetry in /IOTCONNECT.

## Notes
- If the example sends telemetry only on user action, you will not see data until that action occurs.
- If you change the device template in /IOTCONNECT, re-create the device or update it to match these fields.
