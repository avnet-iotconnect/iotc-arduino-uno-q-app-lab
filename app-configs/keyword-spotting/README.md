# /IOTCONNECT-Enabled: keyword-spotting

This is the /IOTCONNECT-enabled version of the Arduino example.

Original Arduino README:
- https://github.com/arduino/app-bricks-examples/blob/main/inspirational/common/keyword-spotting/README.md

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

This app requires a USB microphone and a powered USB hub (since the Arduino Uno Q has a single USB-C port used for power).

**USB Microphone:**
- Any generic USB Microphone

**Powered USB Hub Recommendations:**
- [Sabrent 4-Port USB Hub](https://www.amazon.com/dp/B07H2ZS1B5?ref=cm_sw_r_cp_ud_dp_700AHY8JWV8DF6AR7V2Q&ref_=cm_sw_r_cp_ud_dp_700AHY8JWV8DF6AR7V2Q&social_share=cm_sw_r_cp_ud_dp_700AHY8JWV8DF6AR7V2Q&th=1)

> [!IMPORTANT]
> When using a powered USB hub, Arduino App Lab will no longer recognize the board via USB. You will need to connect to the board using the **Network** option instead.

## Device Template
Quickstart: use the shared master template at `app-configs/arduino-app-lab-template.json`. It is imported once during onboarding and contains the telemetry fields and commands of every example, so a single device can run all of them.
- Template code: `arduino`
- Template name: `arduino`

Optional: `device-template.json` in this folder is a per-example template containing only this app's fields. Import it and bind a separate device to it if you prefer one template per example.
- Template code: `UnoQKS`
- Template name: `UnoQKeywordSpotting`

## Telemetry Fields
| Field | Type |
| --- | --- |
| `UnoQdemo` | `STRING` |
| `device_name` | `STRING` |
| `keyword` | `STRING` |
| `state` | `STRING` |
| `status` | `STRING` |
| `confidence` | `DECIMAL` |
| `last_detected_ts` | `INTEGER` |

## Commands
(none)

## How to Use in App Lab
1) Copy the example into your App Lab workspace.
2) Copy the /IOTCONNECT-enabled python files into the app:
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/keyword-spotting/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/

   cp /opt/demo/iotc_relay_client.py /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   ```
3) Run the app and verify telemetry in /IOTCONNECT.

## Notes
- If the example sends telemetry only on user action, you will not see data until that action occurs.
- If you change the device template in /IOTCONNECT, re-create the device or update it to match these fields.


