# /IOTCONNECT-Enabled: led-matrix-painter

This is the /IOTCONNECT-enabled version of the Arduino example.

Original Arduino README:
- https://github.com/arduino/app-bricks-examples/blob/main/inspirational/common/led-matrix-painter/README.md

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
- `led-matrix-painter-dashboard-template.json` (exported /IOTCONNECT dashboard, see below)
- `dashboard-images/` (the title panel and status images the dashboard shows)

## Device Template
Quickstart: use the shared master template at `app-configs/arduino-app-lab-template.json`. It is imported once during onboarding and contains the telemetry fields and commands of every example, so a single device can run all of them.
- Template code: `arduino`
- Template name: `arduino`

Optional: `device-template.json` in this folder is a per-example template containing only this app's fields. Import it and bind a separate device to it if you prefer one template per example.
- Template code: `UnoQLMP`
- Template name: `UnoQLedMatrixPainter`

## /IOTCONNECT Dynamic Dashboard

Dashboard template file: [led-matrix-painter-dashboard-template.json](led-matrix-painter-dashboard-template.json)

What it shows: a status image driven by `action` (`update_board`, `persist_frame`, `play_animation`, `stop_animation`), a gauge of `frame_count`, the latest `action` and `frame_name`, a bar chart of recent `frame_id` and a latest-values panel.

The widgets load their images from `https://avnetpublicaccess.s3.us-east-1.amazonaws.com/images/arduino/`, so upload the 5 files in [dashboard-images/](dashboard-images/) to that bucket path before importing (the file names must stay the same).

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
| `action` | `STRING` |
| `frame_id` | `INTEGER` |
| `frame_name` | `STRING` |
| `frame_count` | `INTEGER` |
| `status` | `STRING` |

## Commands
(none)

## How to Use in App Lab
1) Copy the example into your App Lab workspace.
2) Copy the /IOTCONNECT-enabled python files into the app:
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/led-matrix-painter/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/

   cp /opt/demo/iotc_relay_client.py /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   ```
   **Or, with the /IOTCONNECT brick** (same telemetry and commands, no code changes; the brick replaces the relay client copy):
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/led-matrix-painter/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER>
   ```
   Either way, `bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER> --remove` goes back to the classic relay client.
3) Run the app and verify telemetry in /IOTCONNECT.

## Notes
- If the example sends telemetry only on user action, you will not see data until that action occurs.
- If you change the device template in /IOTCONNECT, re-create the device or update it to match these fields.

