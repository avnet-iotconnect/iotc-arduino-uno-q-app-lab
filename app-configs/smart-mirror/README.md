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
- `smart-mirror-dashboard-template.json` (exported /IOTCONNECT dashboard, see below)
- `dashboard-images/` (the title panel and status images the dashboard shows)
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

## /IOTCONNECT Dynamic Dashboard

Dashboard template file: [smart-mirror-dashboard-template.json](smart-mirror-dashboard-template.json)

What it shows: a status image driven by `source` (`web_ui`, `iotconnect`), a gauge of `processing_time_ms`, the latest `response_preview` and `status`, a bar chart of recent `response_chars`, a latest-values panel, a one-click command button and a panel for sending any command by hand.

The widgets load their images from `https://avnetpublicaccess.s3.us-east-1.amazonaws.com/images/arduino/`, so upload the 3 files in [dashboard-images/](dashboard-images/) to that bucket path before importing (the file names must stay the same).

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
4) Get the model onto the board, once: the `vlm` brick runs **Qwen 3-VL-4B VLM** (4.1 GB). The first time you run
   the app on a board without it, App Lab sees that the model is missing and asks you to download it; accept
   and wait. To download ahead of time, or to check, open your copy of the app, select the **Vision Language
   Model (VLM)** brick in the **Bricks** section of the editor sidebar and open **AI Models**: the model's card
   shows **Download** or **Installed**. From the board's terminal instead:
   `arduino-app-cli model install genie:qwen3_vl_4b_instruct`.
5) Run the app, open `<board-name>.local:7000`, tap **Scan your look** and verify the telemetry in /IOTCONNECT.

## Live video (KVS brick)

With the [KVS brick](../../bricks/kvs/README.md) installed, this example also streams the mirror camera to /IOTCONNECT
Video Streaming (Kinesis Video Streams) and to the App Lab Cloud Console. The app owns the camera (there is no video
detection runner here), so `main.py` hands every third captured frame to the brick itself (`KvsStream(source="push")`,
about 10 frames per second); without the brick it runs unchanged.

The workshop's VENTUNO Q device `ventunoQ0` was created before video streaming was enabled on the template, so the
video goes out through a companion device `ventunoQ0cam` (same template, video streaming on), whose credentials live in
`~/.iotconnect-cam` on the board:

```bash
bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_kvs_brick.sh <APP_LAB_FOLDER> --creds-from ~/.iotconnect-cam
```

The brick keeps `ventunoQ0cam` connected while the app runs (the portal only plays streams of connected devices). Watch
it on that device's **Video Streaming** tab or in the console's **Live video** panel of the `ventunoQ0` card, which
falls back to `ventunoQ0cam` by itself. Expect 3 to 4 seconds of delay in the console (HLS).

## Notes
- The VLM runs entirely on the VENTUNO Q; the first scan after startup can take a while as the model loads.
- Telemetry is sent only when a scan completes, so you will not see data until someone scans (from the page or with `scan-look`).
- A scan started from the web UI shows its result only in the browser that asked for it; a `scan-look` command shows "The mirror says:" on every open mirror page.
- Direct mode copies the device credentials into the app folder (`data/iotconnect`). Delete that folder before sharing or exporting the app.
- If you change the device template in /IOTCONNECT, re-create the device or update it to match these fields.
