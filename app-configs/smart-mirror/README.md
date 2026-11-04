# /IOTCONNECT-Enabled: smart-mirror

This is the /IOTCONNECT-enabled version of the Arduino VENTUNO Q example.

Original Arduino README (VENTUNO Q example):
- https://github.com/arduino/app-bricks-examples/blob/main/inspirational/platform_ventunoq/smart-mirror/README.md

## Overview
Smart Mirror shows the live camera feed as a mirror and, on **Scan your look**, sends one frame to the Vision Language Model running on the board (`arduino:vlm` brick) for a two-sentence outfit description and style tip. This version adds the /IOTCONNECT brick (`bricks/iotconnect`) in direct mode, a device template, one telemetry message per scan and a command that triggers a scan from the cloud.

**Arduino VENTUNO Q only**: uses the `arduino:vlm` brick, which needs the VENTUNO Q's NPU. The app talks to /IOTCONNECT through the brick; there is no relay client on this path.

## What This Adds
- /IOTCONNECT brick wiring (`from iotconnect import IoTConnect`, direct mode)
- Device template for telemetry + commands
- One telemetry message per completed scan, whether the web UI or the cloud asked for it
- `scan-look` command: the same scan as the web UI button, started from /IOTCONNECT
- Debug logs for telemetry send and command handling

App Lab folder: `/home/arduino/ArduinoApps/<APP_LAB_FOLDER>`

## Files
- `python/main.py` (/IOTCONNECT-enabled app code)
- `python/prompt.py` (upstream prompt helper, unchanged)
- `config.json` (telemetry/command definitions)
- `device-template.json` (per-example device template)

The upstream `python/prompt.yaml` and the `assets/` web UI are used unchanged from your App Lab copy of the example.

## Additional Hardware Required
- Arduino VENTUNO Q
- USB camera (the upstream example also accepts a CSI camera)

## Device Template
Quickstart: use the shared master template at `app-configs/arduino-app-lab-template.json`. It is imported once during onboarding and contains the telemetry fields and commands of every example, so a single device can run all of them.
- Template code: `arduino`
- Template name: `arduino`

Optional: `device-template.json` in this folder is a per-example template containing only this app's fields. Import it and bind a separate device to it if you prefer one template per example.
- Template code: `VQSM`
- Template name: `VentunoQSmartMirror`

## Telemetry Fields
| Field | Type |
| --- | --- |
| `UnoQdemo` | `STRING` |
| `source` | `STRING` |
| `message_count` | `INTEGER` |
| `model` | `STRING` |
| `response_preview` | `STRING` |
| `response_chars` | `INTEGER` |
| `processing_time_ms` | `INTEGER` |
| `status` | `STRING` |

Each completed scan produces one message. `source` is `web_ui` (the **Scan your look** button) or `iotconnect` (the `scan-look` command), `message_count` counts the scans since the app started, `model` is `vlm`, and `response_preview` holds the first 200 characters of what the mirror said. `status` is `ok`, or `error:<msg>` when the scan failed (for example `error:No camera frame available`). `processing_time_ms` is the time of the VLM call, a useful gauge of on-device inference speed.

## Commands
| Command | Parameters |
| --- | --- |
| `scan-look` | `(none)` |

`scan-look` analyses the latest camera frame exactly like the web UI button does, shows the result on every open mirror page and returns the response preview as the acknowledgement. When no camera frame is available the command is acknowledged as failed.

## How to Use in App Lab
1) In App Lab go to **Examples**, open **Smart Mirror** and choose **Copy and edit app**; the name you give the copy is `<APP_LAB_FOLDER>` below.
2) Copy the /IOTCONNECT-enabled python files into the app:
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/smart-mirror/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   ```
3) Add the /IOTCONNECT brick in direct mode:
   ```bash
   bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <APP_LAB_FOLDER> --direct
   ```
   The device credentials come from `scripts/credentials.sh` (README section 3). On the VENTUNO Q they live in `$HOME/.iotconnect`, where the script finds them and copies them into the app's `data/iotconnect` folder.
4) Run the app, open `<board-name>.local:7000`, tap **Scan your look** and verify the telemetry in /IOTCONNECT.

## Notes
- The VLM runs entirely on the VENTUNO Q; the first scan after startup can take a while as the model loads.
- Telemetry is sent only when a scan completes, so you will not see data until someone scans (from the page or with `scan-look`).
- A scan started from the web UI shows its result only in the browser that asked for it; a `scan-look` command shows "The mirror says:" on every open mirror page.
- Direct mode copies the device credentials into the app folder (`data/iotconnect`). Delete that folder before sharing or exporting the app.
- If you change the device template in /IOTCONNECT, re-create the device or update it to match these fields.
