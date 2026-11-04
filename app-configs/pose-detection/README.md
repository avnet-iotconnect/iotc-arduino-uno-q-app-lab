# /IOTCONNECT-Enabled: pose-detection

This is the /IOTCONNECT-enabled version of the Arduino example (an Arduino VENTUNO Q example).

Original Arduino README (VENTUNO Q example):
- https://github.com/arduino/app-bricks-examples/blob/main/inspirational/platform_ventunoq/pose-detection/README.md

## Overview
This version adds the /IOTCONNECT brick, a device template and a command so the pose game can publish telemetry and receive commands from /IOTCONNECT. The app code is written directly against the brick's API (`bricks/iotconnect`, see [its README](../../bricks/iotconnect/README.md)) in direct mode: the app is the /IOTCONNECT device itself, and there is no relay client on this path.

Arduino VENTUNO Q only (the `pose_estimation` brick runs on its NPU). A USB camera is needed.

## What This Adds
- /IOTCONNECT brick wiring (`from iotconnect import IoTConnect`, direct mode)
- Device template for telemetry + commands
- `set-interval` command
- Debug logs for telemetry send

The game itself is unchanged: pose, people-count and readability events still reach the web UI, and a browser that connects still receives the current state.

App Lab folder: `/home/arduino/ArduinoApps/<APP_LAB_FOLDER>`

## Files
- `python/main.py` (/IOTCONNECT-enabled app code, written against the brick API)
- `config.json` (telemetry/command definitions)
- `device-template.json` (per-example device template)

The upstream `app.yaml` and `assets/` (web page, sounds, images) are used unchanged from your App Lab copy of the example; `scripts/add_iotconnect_brick.sh` adds the brick to `app.yaml`.

## Device Template
Quickstart: use the shared master template at `app-configs/arduino-app-lab-template.json`. It is imported once during onboarding and contains the telemetry fields and commands of every example, so a single device can run all of them.
- Template code: `arduino`
- Template name: `arduino`

Optional: `device-template.json` in this folder is a per-example template containing only this app's fields. Import it and bind a separate device to it if you prefer one template per example.
- Template code: `VQPD`
- Template name: `VentunoQPoseDetection`

## Telemetry Fields
| Field | Type |
| --- | --- |
| `UnoQdemo` | `STRING` |
| `pose` | `STRING` |
| `pose_event` | `STRING` |
| `people_count` | `INTEGER` |
| `status` | `STRING` |

Two kinds of message are sent:
- One per pose event, with `pose` (one of the brick's built-in poses: `standing`, `sitting`, `right_arm_raised`, `left_arm_raised`), `pose_event` (`enter` when the tracked person starts holding the pose, `exit` when they leave it) and the current `people_count`. These are rate-limited to one message per interval (default 1 s, see `set-interval`); an event that falls inside the interval is dropped, not queued.
- One whenever the number of people in view changes, with `people_count` only. These are not rate-limited.

`UnoQdemo` is always `pose-detection` and `status` is `ok`. The brick's readability signal ("Get in the picture") only goes to the web UI.

## Commands
| Command | Parameters |
| --- | --- |
| `set-interval` | `seconds` |

`set-interval` sets the minimum time between two pose-event messages. `seconds` is a number >= 0 (`0` sends every event); the ack message is `interval <seconds>s`. A negative or non-numeric value is acknowledged as failed.

## How to Use in App Lab
1) In App Lab, open **Examples**, pick **Pose Detection** and choose **Copy and edit app**. Note the folder name App Lab gives the copy (`<APP_LAB_FOLDER>` below, under `/home/arduino/ArduinoApps`).
2) Copy the /IOTCONNECT-enabled python file into the app:
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/pose-detection/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   ```
3) Add the /IOTCONNECT brick to the app in direct mode:
   ```bash
   bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER> --direct
   ```
   This copies the brick into the app, lists it in `app.yaml` and copies the device credentials into `<APP_LAB_FOLDER>/data/iotconnect`. The credentials come from `scripts/credentials.sh` (workshop README, section 3); on the VENTUNO Q they live in `$HOME/.iotconnect`, which the script finds on its own.
4) Run the app from App Lab, open the web interface at `<board-ip>:7000`, play the game and verify the telemetry in /IOTCONNECT.

## Notes
- Arduino VENTUNO Q only: the `pose_estimation` brick runs on the board's NPU and is not available on the UNO Q.
- Connect the camera before starting the app. Telemetry is sent only on pose events and people-count changes, so you will not see data until someone is in the picture.
- Direct mode puts the device's private key inside the app folder (`data/iotconnect`). Delete that folder before exporting or sharing the app.
- The board needs internet access the first time the app starts, so App Lab can install the brick's `requirements.txt` (the /IOTCONNECT Python Lite SDK).
- If you change the device template in /IOTCONNECT, re-create the device or update it to match these fields.
