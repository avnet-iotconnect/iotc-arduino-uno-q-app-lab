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

## Additional Hardware Required

This app streams sensor data from a smartphone to the Arduino UNO Q. The UNO Q itself needs no extra hardware, but you need:

**Smartphone (iOS or Android):**
- With the **Arduino IoT Remote** app installed
- On the same network as the UNO Q (the app pairs by scanning the QR code shown in the web UI)

## Device Template
This app uses the shared device template at `app-configs/arduino-app-lab-template.json`.
- Template code: `arduino`
- Template name: `arduino`

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
3) Run the app, pair the phone from the web UI, and verify telemetry in /IOTCONNECT.

## Notes
- If the example sends telemetry only on user action, you will not see data until that action occurs.
- If you change the device template in /IOTCONNECT, re-create the device or update it to match these fields.
