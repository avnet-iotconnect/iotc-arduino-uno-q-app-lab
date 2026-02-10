# Arduino UNO Q App Lab Examples on /IOTCONNECT

This README describes the automated path for the customer lab. The scripts run on the UNO Q host OS. 
Participants will use their host machine for account creation, certificates, and shell access.

What is automated on the UNO Q:
- IOTCONNECT Python Lite SDK install
- Relay server and client download (the relay server has a built-in TCP listener for container access)
- systemd service for the relay server
- App Lab project patch (copy relay client + insert init block)
- Health checks

What is still manual:
- IOTCONNECT account/device creation
- Downloading device certs and config from IOTCONNECT
- Arduino App Lab installation
- Android tools (ADB) installation on the laptop

---

## Prerequisites

### Install Arduino App Lab on Host Machine

a) Install Arduino App Lab on your PC:
   - https://www.arduino.cc/en/software/#app-lab-section

   <img src="images/app-lab-download.png" alt="App Lab download page" width="700">

b) Connect the UNO Q to your PC with a USB cable.

   <img src="images/app-lab-connect.png" alt="Connect to board" width="300">

c) Enter your Wi-Fi credentials and set up connectivity.

   <img src="images/app-lab-2-network.png" alt="Enter network credentials" width="300">

d) Update the board when prompted.

   <img src="images/app-lab-4-install-updates.png" alt="Install updates" width="300">

e) Restart the board.
 
f) In App Lab, open Examples to view all available apps.

g) Open the App Lab terminal (used to access the Uno Q terminal).

   <img src="images/app-lab-8-openterminal.png" alt="Open terminal" width="400">

### Create IOTCONNECT Device and Gather Device Credentials

a) Create the IOTCONNECT device.
b) Download the device configuration files to the host machine:
   - `iotcDeviceConfig.json`
   - `device-cert.pem`
   - `device-pkey.pem`
   Note: the downloaded cert files will include the device name (for example, `cert_unoQ.crt` and `key_unoQ2.key`).
   The setup script will copy them to `device-cert.pem` and `device-pkey.pem` automatically.
c) Use the SCP commands below to push the files to the UNO Q.

---

## Step 1: Clone this repo on the UNO Q

```bash
cd /home/arduino

git clone https://github.com/avnet-iotconnect/iotc-arduino-uno-q-workshop.git
cd iotc-arduino-uno-q-workshop

chmod +x scripts/*.sh
```

---

## Step 2: Transfer Device Credentials to the UNO Q 

### a) Get the UNO Q IP address

On the UNO Q terminal:

```bash
hostname -I
```

If you see more than one IP, use the last one listed (example: `10.50.0.199`). Ignore `172.17.0.1` (that is the App Lab container bridge).

### b) Copy certs from Windows to the UNO Q

Run these commands on the Windows laptop after you download the IOTCONNECT files.

```powershell
# 1) Send the config JSON from Downloads
cd Downloads
scp iotcDeviceConfig.json arduino@<UNOQ_IP>:/tmp/

# 2) Send all files from the extracted certs folder
# (folder name varies by device, so use the extracted *certificates* folder)
cd Downloads\*certificates*
scp * arduino@<UNOQ_IP>:/tmp/
```

---

## Step 3: Run the automated host setup (if you have not already)

This installs the IOTCONNECT Python Lite SDK, downloads the relay server + client, and sets up the systemd service.

```bash
cd /home/arduino/iotc-arduino-uno-q-workshop
sudo ./scripts/unoq_setup.sh --demo-dir /home/arduino/demo
```
Optional flags:
- `--no-systemd` (skip service install/start)
- `--skip-apt` (skip apt install step)
- `--skip-sdk` (skip IOTCONNECT Python Lite SDK install)
- `--no-rename-certs` (skip renaming cert/key files in the demo dir)
- `--pip-break-system-packages` (default; allow pip to install system-wide packages on Debian)

---

## Step 4: Verify the host setup

```bash
./scripts/unoq_verify.sh --demo-dir /home/arduino/demo
```

You should see:
- IOTCONNECT Lite SDK import check ok
- Relay socket present: `/tmp/iotconnect-relay.sock`
- Relay TCP listener on port 8899

---

## Step 5: Choose and clone a lab example in App Lab

In Arduino App Lab:
1) Browse examples from `app-bricks-examples`.
2) Copy the selected app into your workspace.
3) Note the app folder path (example: `/home/arduino/ArduinoApps/air-quality-on-led-matrix`).
4) Open the matching guide in `app-configs/<example>/README.md`.
5) Use the placeholder template in `app-configs/<example>/device-template.json` and fill in telemetry + commands for your lab. If you want a single all-in-one template, start from `app-configs/superset/device-template.json` and delete the fields you do not need.

### Examples Index

Use these IOTCONNECT-specific guides:

- [air-quality-monitoring](app-configs/air-quality-monitoring/README.md)
- [anomaly-detection](app-configs/anomaly-detection/README.md)
- [audio-classification](app-configs/audio-classification/README.md)
- [bedtime-story-teller](app-configs/bedtime-story-teller/README.md)
- [blink](app-configs/blink/README.md)
- [blink-with-ui](app-configs/blink-with-ui/README.md)
- [cloud-blink](app-configs/cloud-blink/README.md)
- [code-detector](app-configs/code-detector/README.md)
- [home-climate-monitoring-and-storage](app-configs/home-climate-monitoring-and-storage/README.md)
- [image-classification](app-configs/image-classification/README.md)
- [keyword-spotting](app-configs/keyword-spotting/README.md)
- [led-matrix-painter](app-configs/led-matrix-painter/README.md)
- [mascot-jump-game](app-configs/mascot-jump-game/README.md)
- [object-detection](app-configs/object-detection/README.md)
- [object-hunting](app-configs/object-hunting/README.md)
- [real-time-accelerometer](app-configs/real-time-accelerometer/README.md)
- [system-resources-logger](app-configs/system-resources-logger/README.md)
- [theremin](app-configs/theremin/README.md)
- [unoq-pin-toggle](app-configs/unoq-pin-toggle/README.md)
- [vibration-anomaly-detection](app-configs/vibration-anomaly-detection/README.md)
- [video-face-detection](app-configs/video-face-detection/README.md)
- [video-generic-object-detection](app-configs/video-generic-object-detection/README.md)
- [video-person-classification](app-configs/video-person-classification/README.md)
- [weather-forecast](app-configs/weather-forecast/README.md)

---

## Step 6: Patch the App Lab project for IOTCONNECT

This copies the patched relay client into the app. If a pre-patched `main.py` exists in
`app-configs/<example>/python/main.py`, it will overwrite your app’s `python/main.py`.

```bash
./scripts/unoq_patch_app.sh /home/arduino/ArduinoApps/air-quality-on-led-matrix air-quality-monitoring
```

If your App Lab folder name differs from the example name, pass it explicitly:

```bash
./scripts/unoq_patch_app.sh /home/arduino/ArduinoApps/my-air-quality air-quality-monitoring
```

After patching, open `python/main.py` and add telemetry calls where your app produces data:

```python
# Example
IOTC_SEND({"temp_c": temp_c, "humidity": humidity})
```

---

## Step 7: Run the app and confirm telemetry

1) Run the app in App Lab.
2) Confirm telemetry appears in IOTCONNECT.
3) If you enabled commands, test a command from IOTCONNECT and verify the app receives it.

Expected result: the selected App Lab example runs on the UNO Q and publishes telemetry to IOTCONNECT.

---

## Scripts

- `scripts/unoq_setup.sh`
  - Downloads relay server and client into `/home/arduino/demo`
  - Configures and starts the systemd service

- `scripts/unoq_patch_app.sh <app_dir>`
  - Copies `app-lab/iotc_relay_client.py` into `<app_dir>/python/`
  - Inserts a minimal IOTCONNECT init block into `<app_dir>/python/main.py`
  - Reads `app-configs/<example>/config.json` if present and prints telemetry/command hints

- `scripts/unoq_verify.sh`
  - Verifies SDK import, relay socket, and TCP port

---

## Troubleshooting

- If App Lab cannot connect, confirm the relay server is listening on port 8899:
  `ss -ltnp | grep 8899`
- If the relay socket is missing, restart the relay service:
  `sudo systemctl restart iotc-relay`
- If systemd is not available, run manually:
  - `python3 /home/arduino/demo/iotc-relay-server.py`

---

## Service control (manual start/stop)

To disconnect your device from IOTCONNECT, stop the relay service:

```bash
sudo systemctl stop iotc-relay
```

To start it again:

```bash
sudo systemctl start iotc-relay
```

To restart:

```bash
sudo systemctl restart iotc-relay
```