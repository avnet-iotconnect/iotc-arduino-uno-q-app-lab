# /IOTCONNECT-Enabled: unoq-pin-toggle

This is the /IOTCONNECT-enabled version of the Arduino example.

Original Arduino README:
- https://github.com/arduino/app-bricks-examples/blob/main/examples/unoq-pin-toggle/README.md

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
- `device-template.json` (/IOTCONNECT device template)
- `config.json` (telemetry/command definitions)

## Device Template
This app uses its own device template at `app-configs/unoq-pin-toggle/device-template.json`.
- Template code: `UnoQUPT`
- Template name: `UnoQUnoqPinToggle`

## Telemetry Fields
| Field | Type |
| --- | --- |
| `UnoQdemo` | `STRING` |
| `sw_version` | `STRING` |
| `pin_name` | `STRING` |
| `pin_state` | `OBJECT` |
| `status` | `STRING` |

## Commands
| Command | Parameters |
| --- | --- |
| `set-pin` | `name, state` |

Example payloads accepted by the app:
- JSON object: `{"name":"D12","state":"on"}`
- Space-delimited: `D12 on`
- Key/value text: `name:D12 state:on`

LED group targets and values:
- Targets: `LED3`, `LED4`, or `LED` (both groups)
- Colors: `off`, `red`, `green`, `blue`, `yellow`, `cyan`, `magenta`, `white`
- Patterns: `rainbow`, `blink`, `police`

Examples:
- `set-pin LED3 magenta`
- `set-pin LED4 cyan`
- `set-pin LED rainbow`
- `set-pin LED police`
- `set-pin LED3 rainbow` and `set-pin LED4 blink` can run at the same time

Status values:
- `pin_set`: command applied and full `pin_state` object snapshot published
- `error:*`: command parse/apply failed

## Pin State Object Map
`pin_state` is an object with packed bitfields and LED annotations:

| Field | Bit/Value Mapping |
| --- | --- |
| `D0_D3` | bit0=`D0`, bit1=`D1`, bit2=`D2`, bit3=`D3` |
| `D4_D7` | bit0=`D4`, bit1=`D5`, bit2=`D6`, bit3=`D7` |
| `D8_D11` | bit0=`D8`, bit1=`D9`, bit2=`D10`, bit3=`D11` |
| `D12_D21` | bit0=`D12`, bit1=`D13`, bit2=`D20`, bit3=`D21` |
| `A0_A2` | bit0=`A0`, bit1=`A1`, bit2=`A2` |
| `A3_A5` | bit0=`A3`, bit1=`A4`, bit2=`A5` |
| `LED3` | bit0=`LED3_R`, bit1=`LED3_G`, bit2=`LED3_B` |
| `LED4` | bit0=`LED4_R`, bit1=`LED4_G`, bit2=`LED4_B` |
| `LED3_color` | color name (`off`, `red`, `green`, `blue`, `yellow`, `cyan`, `magenta`, `white`) or `pattern:<name>` |
| `LED4_color` | color name (`off`, `red`, `green`, `blue`, `yellow`, `cyan`, `magenta`, `white`) or `pattern:<name>` |

## How to Use in App Lab
1) Copy the example into your App Lab workspace.
2) Copy the /IOTCONNECT-enabled python files into the app:
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/unoq-pin-toggle/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/

   cp /opt/demo/iotc_relay_client.py /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   ```
3) Run the app and verify telemetry in /IOTCONNECT.

## Notes
- If the example sends telemetry only on user action, you will not see data until that action occurs.
- If you change the device template in /IOTCONNECT, re-create the device or update it to match these fields.
