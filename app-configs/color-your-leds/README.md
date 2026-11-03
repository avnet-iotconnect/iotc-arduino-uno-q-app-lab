# /IOTCONNECT-Enabled: color-your-leds

This is the /IOTCONNECT-enabled version of the Arduino example.

Original Arduino README:
- https://github.com/arduino/app-bricks-examples/blob/main/inspirational/platform_unoq/color-your-leds/README.md

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

## Device Template
This app uses the shared device template at `app-configs/arduino-app-lab-template.json`.
- Template code: `arduino`
- Template name: `arduino`

## Telemetry Fields
| Field | Type |
| --- | --- |
| `UnoQdemo` | `STRING` |
| `led_id` | `INTEGER` |
| `led_color` | `STRING` |
| `led_state` | `STRING` |
| `led1_color` | `STRING` |
| `led2_color` | `STRING` |
| `led3_color` | `STRING` |
| `led4_color` | `STRING` |
| `status` | `STRING` |

Telemetry is sent each time an LED changes, from the web UI or from an /IOTCONNECT command. `led_id`, `led_color` and `led_state` describe the LED that just changed; `led1_color` to `led4_color` are a `#rrggbb` snapshot of all four built-in LEDs.

## Commands
| Command | Parameters |
| --- | --- |
| `set-led` | `led, color` |

`led` is `1` to `4`. `color` can be a name (`off`, `red`, `green`, `blue`, `yellow`, `cyan`, `magenta`, `white`), a hex value (`#ff8800`), or `r,g,b` values (0-255). LED 3 supports full PWM color; LEDs 1, 2 and 4 treat any non-zero channel as on.

Example payloads accepted by the app:
- JSON object: `{"led":3,"color":"#ff8800"}` or `{"led":3,"color":{"r":255,"g":136,"b":0}}`
- Space-delimited: `3 magenta`, `4 255,0,0`
- Key/value text: `led:2 color:cyan`

## How to Use in App Lab
1) Copy the example into your App Lab workspace.
2) Copy the /IOTCONNECT-enabled python files into the app:
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/color-your-leds/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/

   cp /opt/demo/iotc_relay_client.py /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   ```
3) Run the app and verify telemetry in /IOTCONNECT.

## Notes
- If the example sends telemetry only on user action, you will not see data until that action occurs.
- If you change the device template in /IOTCONNECT, re-create the device or update it to match these fields.
