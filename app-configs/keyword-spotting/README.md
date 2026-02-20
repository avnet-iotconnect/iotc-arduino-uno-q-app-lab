# /IOTCONNECT-Enabled: keyword-spotting

This is the /IOTCONNECT-enabled version of the Arduino example.

Original Arduino README:
- https://github.com/arduino/app-bricks-examples/blob/main/examples/keyword-spotting/README.md

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
This app uses the shared device template at `app-configs/arduino-app-lab-template.json`.
- Template code: `arduino`
- Template name: `arduino`

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


