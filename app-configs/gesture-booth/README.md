# /IOTCONNECT-Enabled: gesture-booth

This is the /IOTCONNECT-enabled version of the Arduino VENTUNO Q example.

Original Arduino README (VENTUNO Q example):
- https://github.com/arduino/app-bricks-examples/blob/main/inspirational/platform_ventunoq/gesture-booth/README.md

## Overview
This version adds the /IOTCONNECT brick (`bricks/iotconnect`) in direct mode, a device template and command handling so the app can publish telemetry and receive commands from /IOTCONNECT. The camera, the gesture recognition and the web UI behave exactly as in the upstream example; the brick reports every change of the recognised gesture.

**Arduino VENTUNO Q only**: uses the `arduino:gesture_recognition` brick, which needs the VENTUNO Q's NPU.

**Additional hardware**: a USB camera (the upstream README also lists a CSI camera).

## What This Adds
- /IOTCONNECT brick wiring (`from iotconnect import IoTConnect`, direct mode, no relay client)
- Device template for telemetry + commands
- `set-interval` command
- Debug logs for telemetry send

App Lab folder: `/home/arduino/ArduinoApps/<APP_LAB_FOLDER>`

## Files
- `python/main.py` (/IOTCONNECT-enabled app code)
- `config.json` (telemetry/command definitions)
- `device-template.json` (optional per-example device template)

The upstream `assets/` web UI is used unchanged from your App Lab copy of the example.

## Device Template
Quickstart: use the shared master template at `app-configs/arduino-app-lab-template.json`. It is imported once during onboarding and contains the telemetry fields and commands of every example, so a single device can run all of them.
- Template code: `arduino`
- Template name: `arduino`

Optional: `device-template.json` in this folder is a per-example template containing only this app's fields. Import it and bind a separate device to it if you prefer one template per example.
- Template code: `VQGB`
- Template name: `VentunoQGestureBooth`

## Telemetry Fields
| Field | Type |
| --- | --- |
| `UnoQdemo` | `STRING` |
| `gesture` | `STRING` |
| `gesture_count` | `INTEGER` |
| `status` | `STRING` |

One message is sent each time the recognised gesture changes, at most one per interval (default 1 s, see `set-interval`). `gesture` is the label the web UI shows: `Closed Fist`, `Open Palm`, `Pointing Up`, `Thumb Down`, `Thumb Up`, `Victory`, `Rock` (the model's `ILoveYou`), or `None` when a hand is visible but no gesture is recognised. `None` is reported so a dashboard clears, but it does not count: `gesture_count` is the number of gesture messages sent since the app started.

## Commands
| Command | Parameters |
| --- | --- |
| `set-interval` | `seconds` |

`set-interval` sets the minimum time between two telemetry messages, in seconds (a number >= 0, decimals allowed; `0` reports every change). The ack message is `interval <seconds>s`.

## How to Use in App Lab
1) In App Lab open **Examples**, select **"Gesture Booth"** and click **"Copy and edit app"**; give the copy a name (its folder name is `<APP_LAB_FOLDER>` below).
2) Copy the /IOTCONNECT-enabled python files into the app:
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/gesture-booth/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   ```
3) Add the /IOTCONNECT brick to the app in direct mode:
   ```bash
   bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER> --direct
   ```
   The device credentials come from `scripts/credentials.sh` (README section 3); on the VENTUNO Q they live in `$HOME/.iotconnect`, where the script picks them up.
4) Run the app, show a gesture to the camera and verify telemetry in /IOTCONNECT.

## Notes
- The brick connects once `App.run()` has started, and the first start needs internet access to install the /IOTCONNECT Python SDK. A gesture shown while the connection is down is not sent (`send result: False` in the console) and is retried every interval until the connection is up, so the current gesture arrives as soon as the brick is connected; `gesture_count` only counts messages that were actually sent.
- The gesture callbacks fire for every frame, so a change that falls inside the interval is reported as soon as the interval has passed; a held gesture is never lost.
- With two hands showing different gestures, the report alternates between them, one message per interval.
- Direct mode copies the device credentials into `data/iotconnect` inside the app folder; delete that folder before exporting or sharing the app.
- If you change the device template in /IOTCONNECT, re-create the device or update it to match these fields.
