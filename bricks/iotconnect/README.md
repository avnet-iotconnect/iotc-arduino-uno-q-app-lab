# /IOTCONNECT Brick for Arduino App Lab

A [custom brick](https://docs.arduino.cc/software/app-lab/bricks/about-bricks/) that connects any App Lab app to
Avnet's /IOTCONNECT platform. Drop the `bricks/iotconnect` folder into an app, list it in `app.yaml`, and the app can
publish telemetry and react to cloud-to-device commands with a handful of lines of Python. It runs on the Arduino UNO Q
and the Arduino VENTUNO Q (verified with App Lab 0.14); on the VENTUNO Q it is the only way onto /IOTCONNECT, since that
board has no relay service.

```python
import time

from arduino.app_utils import App, Bridge
from iotconnect import IoTConnect

iotc = IoTConnect()


@iotc.command("set-led")
def set_led(args: list[str]) -> None:
    Bridge.call("set_led_state", args[0] == "1")


def loop() -> None:
    iotc.send_telemetry({"temperature": 21.5, "status": "ok"})
    time.sleep(5)


App.run(user_loop=loop)
```

## Contents

- [What it does](#what-it-does)
- [Add the brick to an app](#add-the-brick-to-an-app)
- [Direct mode or relay mode](#direct-mode-or-relay-mode)
- [Python API](#python-api)
- [Drop-in for the workshop relay client](#drop-in-for-the-workshop-relay-client)
- [Brick variables](#brick-variables)
- [Device template](#device-template)
- [Troubleshooting](#troubleshooting)

## What it does

- **Telemetry**: `send_telemetry({...})` publishes a record; values can be numbers, strings, booleans, nested objects,
  lists and dates. An optional send interval merges high-rate samples into one message per interval.
- **Commands**: handlers per command name or one catch-all. In direct mode the outcome is acknowledged to the cloud
  (success, failure, or success with a message).
- **OTA** (direct mode): an `on_ota` handler receives the file list and reports progress and the result.
- **Connection management**: connects in the background, reconnects with backoff, never blocks `App.run()`, and never
  raises into the app because the cloud is unreachable. The app keeps working offline and `send_telemetry` returns
  `False` until the link is back.
- **Two transports**, see [below](#direct-mode-or-relay-mode): the app can be the /IOTCONNECT device itself, or go
  through the board's `iotc-relay` service from the workshop setup.

The brick runs inside the app container like every other brick: `App.run()` starts and stops it, its work happens on its
own threads, and its logs show up in the App Lab console under `IoTConnect`.

## Add the brick to an app

Prerequisite: the device is onboarded (sections 2 and 3 of the [workshop README](../../README.md)), so
`/opt/demo` on the board holds `iotcDeviceConfig.json`, `device-cert.pem` and `device-pkey.pem`.

### With the script (recommended)

In the UNO Q terminal, with `<app>` being the app's folder name under `/home/arduino/ArduinoApps`:

```bash
bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <app>
```

The script copies the brick into `<app>/bricks/iotconnect`, adds `- iotconnect` to `app.yaml`, and picks a mode:
relay if the `iotc-relay` service is running, otherwise direct (it then copies the credentials into
`<app>/data/iotconnect`). Force one with `--relay` or `--direct`. Run it again to update the brick copy: an app
already set up for direct mode stays in direct mode, otherwise the mode is chosen again from the relay service's
state (pass the flag to be explicit).

### By hand

1. Copy this folder to `<app>/bricks/iotconnect`.
2. Add the brick to `app.yaml`:
   ```yaml
   bricks:
     - iotconnect
   ```
3. Direct mode only: copy `iotcDeviceConfig.json`, `device-cert.pem` and `device-pkey.pem` into `<app>/data/iotconnect/`.
4. In `python/main.py`: `from iotconnect import IoTConnect`, create `iotc = IoTConnect()` before `App.run()`.

App Lab installs the brick's `requirements.txt` (the [/IOTCONNECT Python Lite SDK](https://github.com/avnet-iotconnect/iotc-python-lite-sdk))
into the app's environment the first time the app starts, so the board needs internet access at that point.

## Direct mode or relay mode

| | `direct` | `relay` |
| --- | --- | --- |
| Who connects to the cloud | the app, through the SDK inside the container | the board's `iotc-relay` systemd service ([workshop section 4](../../README.md#4-set-up-iotconnect-sdk-and-relay-service)) |
| Credentials | copied into the app (`data/iotconnect/`) | stay in `/opt/demo` on the board |
| Telemetry | sent as called (or per `send_interval`) | the relay keeps the last message per app and sends the combined set every 5 s (the brick re-sends the values of the last 5 s with each call, so nothing is lost) |
| Command acks | from the handler's outcome | the relay acks "broadcast" immediately (the current relay also delivers each command twice; the brick collapses the duplicate) |
| Timestamps on telemetry | yes | no |
| OTA requests | delivered to `on_ota` | handled by the relay (`file-download` command) |
| Several apps on one device | no, one MQTT session per device | yes, each app registers with its own client id |

`IOTC_MODE=auto` (the default) picks `direct` when the three credential files exist, otherwise `relay`.

One device identity must have one cloud session. If the relay service is running, either use relay mode or stop it
(`sudo systemctl disable --now iotc-relay`) before running the app in direct mode. Otherwise the two sessions keep
disconnecting each other.

Direct mode puts the private key inside the app folder, which App Lab exports and shares. Remove `data/iotconnect`
before sharing the app. `.gitignore` in this repository already excludes it.

## Python API

### `IoTConnect(mode=None, credentials_dir=None, relay_endpoint=None, client_id=None, send_interval=None)`

All arguments are optional and default to the [brick variables](#brick-variables). Create the instance once, before
`App.run()`. Streamlit apps (`arduino:streamlit_ui`) re-run `main.py` on every interaction while `App.run()` only
starts bricks on the first run, so build the instance in a cached factory there:

```python
@st.cache_resource
def get_iotc() -> IoTConnect:
    iotc = IoTConnect()
    iotc.on_command("set-led", ...)
    return iotc
```

- `mode`: `"auto"`, `"direct"` or `"relay"`.
- `credentials_dir`: folder with the three credential files (direct mode).
- `relay_endpoint`: `tcp://host:port` or a unix socket path (relay mode).
- `client_id`: the name the app registers with the relay (relay mode).
- `send_interval`: seconds between transmissions. `0` sends every call at once. A positive value merges the values of
  all calls made during the interval and sends one message with the latest value of each field, which keeps high-rate
  sensors within the template's data frequency.

### `iotc.send_telemetry(values, timestamp=None) -> bool`

Publishes one record. `values` is a dict whose keys match the device template's attributes (unknown attributes are
dropped by /IOTCONNECT without an error). Returns `True` when the record was handed to the cloud or relay (or queued
when a send interval is set) and `False` while offline. `timestamp` (a timezone-aware `datetime`) is honoured in direct
mode only.

### `iotc.on_command(name, handler)` / `@iotc.command(name)`

Registers a handler for one command. The handler receives the command arguments as a list of strings, e.g. the cloud
command `set-led 1` calls `handler(["1"])`. Handlers run one at a time on a worker thread, so they may call
`Bridge.call(...)` and take their time.

In direct mode the outcome becomes the command ack (the template's "Acknowledgement Required" must be on):

| Handler | Ack |
| --- | --- |
| returns `None`, `True` or any other value | success |
| returns a string | success, with that string as the message |
| returns `False` | failed |
| raises | failed, with the exception as the message |

### `iotc.on_command(handler)`

Registers a catch-all `handler(name, args)` for commands that have no named handler. Without any handler, unknown
commands are acknowledged as failed in direct mode and ignored in relay mode (the relay forwards every command to every
app, so unknown ones are normal there).

### `iotc.on_ota(handler)`

Direct mode. `handler(request)` receives an `OtaRequest` with `version`, `hardware_version` and `files`, each file an
`OtaFile` with `url` and `file_name`. The brick acks *downloading* before calling the handler, then *done* when the
handler returns (a returned string becomes the ack message) or *failed* when it returns `False` or raises. Without a
handler, OTA requests are rejected with a failure ack so the operator sees it in the console.

### `iotc.on_connect(fn)` / `iotc.on_disconnect(fn)`

`fn()` runs each time the connection is (re)established; `fn(reason)` each time it is lost. Useful to resend state
after a reconnect.

### `iotc.is_connected() -> bool`, `iotc.mode -> str`

The current link state and the effective mode (`"direct"` or `"relay"`).

## Drop-in for the workshop relay client

Apps written for the workshop's `iotc_relay_client.py` (every folder under `app-configs/`) run on the brick without
code changes. When `scripts/add_iotconnect_brick.sh` finds `from iotc_relay_client import ...` under `python/`, it
replaces the relay client copy in the app with a shim:

```python
from iotconnect.compat import IoTConnectRelayClient
```

`IoTConnectRelayClient(socket_path, client_id, command_callback=None, reconnect_delay=5)` keeps the classic
methods: `start()`, `stop()`, `send_telemetry(dict) -> bool`, `is_connected()`, and `command_callback` can still be
assigned after construction. What changes underneath:

| Classic client | On the brick |
| --- | --- |
| `start()` connects at import time | the app framework connects the brick when `App.run()` starts; `send_telemetry` before that returns False, as it did while the classic client was disconnected |
| relay service only | relay or direct mode, from the brick's variables (`socket_path` overrides `IOTC_RELAY_ENDPOINT`, `client_id` overrides `IOTC_CLIENT_ID`) |
| every command arrives twice, telemetry inside 5 s is lost | the brick's relay fixes apply (see "Direct mode or relay mode") |
| `command_callback(name, parameters)` with the raw string | same signature and string; in direct mode the cloud's parameter list is re-joined with single spaces |

`bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_iotconnect_brick.sh <app> --remove` takes the brick out again: it deletes `bricks/iotconnect`, drops
the entry from `app.yaml`, removes any copied credentials and restores the classic relay client from `/opt/demo`.

## Brick variables

Set them in App Lab (the brick's settings in the app) or with
`arduino-app-cli app brick config <app> iotconnect NAME=value`. Constructor arguments win over variables.

| Variable | Default | Meaning |
| --- | --- | --- |
| `IOTC_MODE` | `auto` | `auto`, `direct` or `relay` |
| `IOTC_CREDENTIALS_DIR` | `/app/data/iotconnect` (`data/iotconnect` in the app folder) | folder with `iotcDeviceConfig.json`, `device-cert.pem`, `device-pkey.pem` |
| `IOTC_RELAY_ENDPOINT` | `tcp://172.17.0.1:8899` | the relay service as seen from the app container (a unix socket path only works if that socket is mounted into the container) |
| `IOTC_CLIENT_ID` | `auto` (the app folder name) | relay client id |
| `IOTC_SEND_INTERVAL` | `0` | seconds between transmissions, `0` = immediate |
| `IOTC_SERVER_CA_CERT` | `system` | CA certificate path for the broker, `system` = the system trust store (hidden) |

`IOTC_DEVICE_CONFIG`, `IOTC_DEVICE_CERT` and `IOTC_DEVICE_KEY` override the individual file paths when set in the
environment.

## Device template

The brick is template-agnostic: whatever keys you put in `send_telemetry()` must exist as attributes in the device's
template, and every command the app handles must be defined there (with "Acknowledgement Required" for acks). The
workshop's master template `app-configs/arduino-app-lab-template.json` covers all the examples in this repository; for
your own app, import a template with your attributes or add them to an existing one.

## Troubleshooting

| Log line | What to do |
| --- | --- |
| `Direct mode needs these files: ...` | copy the credentials into `data/iotconnect` (`add_iotconnect_brick.sh <app> --direct`) or set `IOTC_MODE=relay` |
| `Relay tcp://172.17.0.1:8899 not reachable` | start the relay (`sudo systemctl start iotc-relay`) or switch to direct mode |
| `Disconnected: connection lost (...)` followed by `Connected to /IOTCONNECT`, repeating every few seconds | another session uses the same device identity: stop `iotc-relay` or the other app |
| `Could not connect to /IOTCONNECT: ...` | check the board's internet access and that the device exists in /IOTCONNECT with the pasted certificate |
| `Not connected to /IOTCONNECT, next attempt in ...` without a `Connected` line | the broker rejects the device (wrong or revoked certificate, device disabled); re-check the device in /IOTCONNECT |
| telemetry sent but not visible in the cloud | the attribute names are not in the device template |
| commands arrive but no ack in the console | the command in the template needs "Acknowledgement Required" |
| `Could not connect to /IOTCONNECT: No module named 'avnet'` | the SDK did not get installed; restart the app with the board online so App Lab installs `requirements.txt` again |
| App Lab reports `App preparation failed` after `Installing requirements for brick: iotconnect` | the board had no internet during the first start; connect it and start the app again |

The sources are `__init__.py` (the brick) and `compat.py` (the relay-client drop-in), with the relay wire protocol compatible with
`iotc-relay-server.py` from [iotc-relay-service](https://github.com/avnet-iotconnect/iotc-relay-service).
