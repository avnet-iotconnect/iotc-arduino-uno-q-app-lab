# /IOTCONNECT-Enabled: music-composer

This is the /IOTCONNECT-enabled version of the Arduino example.

Original Arduino README:
- https://github.com/arduino/app-bricks-examples/blob/main/inspirational/common/music-composer/README.md

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

This app plays audio, so the UNO Q needs a speaker.

**Speaker:**
- USB speaker, or a 3.5 mm speaker through the [Arduino UNO Media Carrier](https://store.arduino.cc/products/uno-media-carrier)

**USB-C hub with external power (when using a USB audio device):**
- [Arduino USB-C hub](https://store.arduino.cc/products/usb-c-hub-8-in-1) plus a 5 V / 3 A power supply, because the UNO Q's single USB-C port must feed both power and the audio device. Run the app in Network Mode or SBC Mode in that case.

## Device Template
This app uses the shared device template at `app-configs/arduino-app-lab-template.json`.
- Template code: `arduino`
- Template name: `arduino`

## Telemetry Fields
| Field | Type |
| --- | --- |
| `UnoQdemo` | `STRING` |
| `state` | `STRING` |
| `bpm` | `INTEGER` |
| `waveform` | `STRING` |
| `volume` | `INTEGER` |
| `step_count` | `INTEGER` |
| `note_count` | `INTEGER` |
| `effects_json` | `STRING` |
| `status` | `STRING` |

`state` is `playing` or `stopped`. `volume` is 0-100. `step_count` is the length of the sequence built from the grid and `note_count` the number of active notes in it. `status` names the event that triggered the message: `play`, `stop`, `playback_ended`, `grid_updated`, `bpm_set`, `volume_set`, `waveform_set`, `effects_set`, or `error:*`. Grid edits are rate-limited to one message every 2 seconds.

## Commands
| Command | Parameters |
| --- | --- |
| `play` | `(none)` |
| `stop` | `(none)` |
| `set-bpm` | `bpm` |
| `set-volume` | `volume` |
| `set-waveform` | `waveform` |

`set-volume` takes 0-100. `set-waveform` accepts `sine`, `square`, `triangle` or `sawtooth`. Parameters can be plain values (`140`) or JSON (`{"bpm":140}`). As in the original app, BPM cannot be changed while a sequence is playing.

## How to Use in App Lab
1) Copy the example into your App Lab workspace.
2) Copy the /IOTCONNECT-enabled python files into the app:
   ```bash
   cp /home/arduino/iotc-arduino-uno-q-workshop/app-configs/music-composer/python/* /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/

   cp /opt/demo/iotc_relay_client.py /home/arduino/ArduinoApps/<APP_LAB_FOLDER>/python/
   ```
3) Run the app and verify telemetry in /IOTCONNECT.

## Notes
- If the example sends telemetry only on user action, you will not see data until that action occurs.
- If you change the device template in /IOTCONNECT, re-create the device or update it to match these fields.
