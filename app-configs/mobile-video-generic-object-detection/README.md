# /IOTCONNECT-Enabled: mobile-video-generic-object-detection

This is the /IOTCONNECT-enabled version of the Arduino example.

Original Arduino README:
- https://github.com/arduino/app-bricks-examples/blob/main/inspirational/common/mobile-video-generic-object-detection/README.md

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

## Additional Hardware Required

This app runs object detection on a live feed from a smartphone camera instead of a USB camera. The UNO Q itself needs no extra hardware, but you need:

**Smartphone (iOS or Android):**
- With the **Arduino IoT Remote** app installed
- On the same network as the UNO Q (the app pairs by scanning the QR code shown in the web UI)

## Device Template
Quickstart: use the shared master template at `app-configs/arduino-app-lab-template.json`. It is imported once during onboarding and contains the telemetry fields and commands of every example, so a single device can run all of them.
- Template code: `arduino`
- Template name: `arduino`

Optional: `device-template.json` in this folder is a per-example template containing only this app's fields. Import it and bind a separate device to it if you prefer one template per example.
- Template code: `UnoQMVGOD`
- Template name: `UnoQMobileVideoGenericOb`

## Telemetry Fields
| Field | Type |
| --- | --- |
| `UnoQdemo` | `STRING` |
| `source` | `STRING` |
| `state` | `STRING` |
| `auto_mode` | `STRING` |
| `interval_sec` | `INTEGER` |
| `detection_count` | `INTEGER` |
| `max_confidence` | `DECIMAL` |
| `avg_confidence` | `DECIMAL` |
| `detections_json` | `STRING` |
| `status` | `STRING` |
| `class_name_1` | `STRING` |
| `confidence_1` | `DECIMAL` |
| `class_name_2` | `STRING` |
| `confidence_2` | `DECIMAL` |
| `class_name_3` | `STRING` |
| `confidence_3` | `DECIMAL` |
| `class_name_4` | `STRING` |
| `confidence_4` | `DECIMAL` |

`source` is always `smartphone`. `state` is the phone camera link status; a message is sent immediately on each link change with `status` set to `camera_<status>`. The remaining fields match the `video-generic-object-detection` app so the same dashboard widgets can be reused.

## Commands
| Command | Parameters |
| --- | --- |
| `set-interval` | `seconds` |
| `set-confidence` | `confidence` |
| `set-auto` | `enabled` |
| `run-detect` | `(none)` |

In auto mode (default) telemetry is sent every `interval_sec` seconds while detections arrive. With `set-auto` off, telemetry is sent only when `run-detect` is received.

## How to Use in App Lab
1) Copy the example into your App Lab workspace.
2) Copy the /IOTCONNECT-enabled python files into the app:
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/mobile-video-generic-object-detection/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/

   cp /opt/demo/iotc_relay_client.py /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   ```
   **Or, with the /IOTCONNECT brick** (same telemetry and commands, no code changes; the brick replaces the relay client copy):
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/mobile-video-generic-object-detection/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER>
   ```
   Either way, `bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER> --remove` goes back to the classic relay client.
3) Run the app, pair the phone from the web UI, and verify telemetry in /IOTCONNECT.

## Notes
- If the example sends telemetry only on user action, you will not see data until that action occurs.
- If you change the device template in /IOTCONNECT, re-create the device or update it to match these fields.
