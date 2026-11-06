# /IOTCONNECT-Enabled: mobile-remote-sensor

This is the /IOTCONNECT-enabled version of the Arduino example.

Original Arduino README:
- https://github.com/arduino/app-bricks-examples/blob/main/inspirational/common/mobile-remote-sensor/README.md

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
- `mobile-remote-sensor-dashboard-template.json` (exported /IOTCONNECT dashboard, see below)
- `dashboard-images/` (the title panel and status images the dashboard shows)

## Additional Hardware Required

This app streams sensor data from a smartphone to the Arduino UNO Q. The UNO Q itself needs no extra hardware, but you need:

**Smartphone (iOS or Android):**
- With the **Arduino IoT Remote** app installed
- On the same network as the UNO Q (the app pairs by scanning the QR code shown in the web UI)

## Device Template
Quickstart: use the shared master template at `app-configs/arduino-app-lab-template.json`. It is imported once during onboarding and contains the telemetry fields and commands of every example, so a single device can run all of them.
- Template code: `arduino`
- Template name: `arduino`

Optional: `device-template.json` in this folder is a per-example template containing only this app's fields. Import it and bind a separate device to it if you prefer one template per example.
- Template code: `UnoQMRS`
- Template name: `UnoQMobileRemoteSensor`

## /IOTCONNECT Dynamic Dashboard

Dashboard template file: [mobile-remote-sensor-dashboard-template.json](mobile-remote-sensor-dashboard-template.json)

What it shows: a status image driven by `state` (`connected`, `disconnected`), a gauge of `compass`, the latest `status` and `state`, a bar chart of recent `x`, a latest-values panel, 2 one-click command buttons and a panel for sending any command by hand.

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
| `interval_sec` | `INTEGER` |
| `state` | `STRING` |
| `x` | `DECIMAL` |
| `y` | `DECIMAL` |
| `z` | `DECIMAL` |
| `gyro_x` | `DECIMAL` |
| `gyro_y` | `DECIMAL` |
| `gyro_z` | `DECIMAL` |
| `mag_x` | `DECIMAL` |
| `mag_y` | `DECIMAL` |
| `mag_z` | `DECIMAL` |
| `compass` | `DECIMAL` |
| `barometer` | `DECIMAL` |
| `brightness` | `DECIMAL` |
| `battery` | `DECIMAL` |
| `sound_level` | `DECIMAL` |
| `sound_pitch` | `DECIMAL` |
| `lat` | `DECIMAL` |
| `lon` | `DECIMAL` |
| `sensor_json` | `STRING` |
| `status` | `STRING` |

`x`, `y`, `z` are the phone accelerometer. `state` is the phone link (`connected` / `disconnected`); a telemetry message is sent immediately on each link change with `status` set to `sensor_connected` or `sensor_disconnected`. `sensor_json` carries the raw datapoint from the phone. Sensors the phone does not report arrive as `0`.

## Commands
| Command | Parameters |
| --- | --- |
| `set-interval` | `seconds` |

The phone streams many datapoints per second; telemetry is rate-limited to one message every `interval_sec` seconds (default 2).

## How to Use in App Lab
1) Copy the example into your App Lab workspace.
2) Copy the /IOTCONNECT-enabled python files into the app:
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/mobile-remote-sensor/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/

   cp /opt/demo/iotc_relay_client.py /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   ```
   **Or, with the /IOTCONNECT brick** (same telemetry and commands, no code changes; the brick replaces the relay client copy):
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/mobile-remote-sensor/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER>
   ```
   Either way, `bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER> --remove` goes back to the classic relay client.
3) Run the app, pair the phone from the web UI, and verify telemetry in /IOTCONNECT.

## Notes
- If the example sends telemetry only on user action, you will not see data until that action occurs.
- If you change the device template in /IOTCONNECT, re-create the device or update it to match these fields.
