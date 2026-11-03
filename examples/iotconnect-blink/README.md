# /IOTCONNECT Blink (brick example)

The upstream *Blink LED from Python* example with the [/IOTCONNECT brick](../../bricks/iotconnect/README.md) added:
the LED blinks once a second, the app publishes the LED state to /IOTCONNECT every few seconds, and the cloud can change
the LED and the telemetry interval.

| Direction | Name | Details |
| --- | --- | --- |
| Telemetry | `UnoQdemo` (STRING), `interval_sec` (INTEGER), `led_state` (STRING), `status` (STRING) | sent every `interval_sec` seconds |
| Command | `set-interval <seconds>` | telemetry period, at least 1 s |
| Command | `set-led <0\|1>` | force the LED state |

Both are in the workshop's master template (`app-configs/arduino-app-lab-template.json`) and in
[`app-configs/blink/device-template.json`](../../app-configs/blink/device-template.json).

## Run it

In the UNO Q terminal (after sections 2 and 3 of the [main README](../../README.md)):

```bash
arduino-app-cli app new iotconnect-blink --from-app /home/arduino/iotc-arduino-uno-q-workshop/examples/iotconnect-blink
bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh iotconnect-blink
```

The second command copies the brick into the app and, depending on your setup, either copies the device credentials into
the app (direct mode) or points the app at the board's relay service (relay mode). Then open the app in App Lab and run it.
The app logs show `IoTConnect: Connected ...` followed by `IOTCONNECT send: {...}` lines, and the device page in
/IOTCONNECT shows the telemetry.
