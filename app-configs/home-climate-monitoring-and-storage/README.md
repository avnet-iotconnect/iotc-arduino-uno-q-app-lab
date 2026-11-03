# /IOTCONNECT-Enabled: home-climate-monitoring-and-storage

This is the /IOTCONNECT-enabled version of the Arduino example.

Original Arduino README:
- https://github.com/arduino/app-bricks-examples/blob/main/inspirational/common/home-climate-monitoring-and-storage/README.md

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

This app requires a Modulino Thermo sensor and a Qwiic cable to connect it to the Arduino Uno Q.

**Modulino Thermo Sensor:**
- [Arduino Modulino Thermo](https://store-usa.arduino.cc/products/modulino-thermo?srsltid=AfmBOooBjqt7UCtENS440MK_8stLHrxES2SVECgwXTJdztwZsh08Md51)

**Qwiic Cable:**
- [elechawk Qwiic Cable](https://www.amazon.com/elechawk-SparkFun-Development-Breadboard-Connector/dp/B08HQ1VSVL)

## Device Template
Quickstart: use the shared master template at `app-configs/arduino-app-lab-template.json`. It is imported once during onboarding and contains the telemetry fields and commands of every example, so a single device can run all of them.
- Template code: `arduino`
- Template name: `arduino`

Optional: `device-template.json` in this folder is a per-example template containing only this app's fields. Import it and bind a separate device to it if you prefer one template per example.
- Template code: `UnoQHC`
- Template name: `UnoQHomeClimate`

## /IOTCONNECT Dynamic Dashboard

![home-climate-monitoring-and-storage dashboard](home-climate-dashboard.jpg)

Dashboard template file: [Home_Climate_dashboard_export.json](Home_Climate_dashboard_export.json)

Import into /IOTCONNECT:
1. Open /IOTCONNECT and go to **Dashboard**.
2. Click **Import Dashboard** and upload the JSON file linked above.
3. Save the imported dashboard and map it to the correct device/template.
4. Open the dashboard in live mode and verify widgets populate from telemetry.

## Telemetry Fields
| Field | Type |
| --- | --- |
| `temperature_c` | `DECIMAL` |
| `humidity` | `DECIMAL` |
| `dew_point` | `DECIMAL` |
| `heat_index` | `DECIMAL` |
| `absolute_humidity` | `DECIMAL` |
| `ts` | `INTEGER` |
| `UnoQdemo` | `STRING` |
| `interval_sec` | `INTEGER` |

## Commands
| Command | Parameters |
| --- | --- |
| `set-interval` | `seconds` |

## How to Use in App Lab
1) Copy the example into your App Lab workspace.
2) Copy the /IOTCONNECT-enabled python files into the app:
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/home-climate-monitoring-and-storage/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   cp /opt/demo/iotc_relay_client.py /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   ```
3) Run the app and verify telemetry in /IOTCONNECT.

## Notes
- If the example sends telemetry only on user action, you will not see data until that action occurs.
- If you change the device template in /IOTCONNECT, re-create the device or update it to match these fields.



