# KVS Video Stream brick (/IOTCONNECT)

Streams the camera of an Arduino App Lab app to **/IOTCONNECT Video Streaming** (AWS Kinesis Video Streams).
The stream shows up on the device's **Video Streaming** tab in /IOTCONNECT and on the
[App Lab Cloud Console](https://avnet-qpet-leaderboard.s3.us-east-1.amazonaws.com/console/index.html) while the
app runs. Verified on the Arduino UNO Q with the Detect Objects on Camera, Face Detector on Camera, Person
classifier on camera and Object Hunting examples, and on the Arduino VENTUNO Q with Smart Mirror.

## How it works

- **Frames.** The video detection bricks (`video_object_detection`, `video_image_classification`) own the USB camera
  through their model runner. The brick connects to that runner's websocket, switches its camera preview on and
  receives the decoded JPEG frames (about 10 per second at 640x480). Detection keeps working and no second camera
  reader is needed. Apps that own the camera themselves hand frames over with `kvs.push_frame(jpeg_bytes)`
  (`KVS_SOURCE=push`).
- **Encoding and upload.** A GStreamer pipeline decodes the JPEGs, encodes them with the board's hardware H.264 encoder
  (`v4l2h264enc`, the Qualcomm Venus codec on the UNO Q; `x264enc`/`openh264enc` are used when present instead) and
  uploads with the AWS KVS producer plugin `kvssink`. One key frame per second, 600 kbit/s by default.
- **Credentials.** `kvssink` fetches and refreshes temporary AWS credentials itself from the /IOTCONNECT credentials
  endpoint of the device, authenticating with the device certificate, exactly as the /IOTCONNECT Python SDK does.
  Nothing but the device identity files is stored in the app.
- **Stream name.** The device's /IOTCONNECT client id (`unoQ0` for the workshop device): that is the stream the
  portal and the console play. The stream is created on first use.

## Install

1. Enable video streaming on the device template in /IOTCONNECT: **Devices -> Templates -> `arduino` -> Settings**,
   Video Streaming = **Kinesis Video Stream**, auto start on. Existing devices of that template then get the stream
   resource through **Device -> Edit** (Video stream resource: Kinesis Video Stream). Through the REST API this is
   `PUT /api/v2.1/device-template/{templateGuid}/property` with `videoStreamResource: 1, videoStreamType: 1,
   autoStartVideoStream: true` and `PUT /api/v2.1/Device/{deviceGuid}` with `videoStreamResource: 1`.
2. On the board (the workshop repo cloned as in README section 2, device credentials in `/opt/demo` as in section 3):
   ```bash
   bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_kvs_brick.sh <APP_LAB_FOLDER>
   ```
   The script copies the brick into the app, lists it in `app.yaml`, copies the device credentials to `data/kvs` and
   downloads the KVS producer plugin plus the few Debian libraries it needs into `data/kvs/libs` (once, then cached in
   `~/.cache/kvs-brick`). `--remove` takes everything out again.
3. Make sure `python/main.py` creates the brick before `App.run()`. The workshop camera examples already do:
   ```python
   try:
       from kvs import KvsStream
       kvs_stream = KvsStream()
   except ImportError:
       kvs_stream = None
   ```
4. Start (or restart) the app. `App logs` shows `Receiving camera frames from ei-video-obj-detection-runner` and
   `Streaming to Kinesis Video: started`.

## Variables (app.yaml or the brick panel in App Lab)

| Variable | Default | Meaning |
|---|---|---|
| `KVS_SOURCE` | `auto` | `auto` = the app's video runner; `push` = frames from `push_frame()` |
| `KVS_FPS` | `10` | frames per second sent to the stream |
| `KVS_BITRATE` | `600000` | H.264 bitrate, bit/s |
| `KVS_AUTOSTART` | `true` | stream as soon as the app runs; `false` = wait for `start_stream()` |
| `KVS_STREAM_NAME` | `auto` | the device's client id; anything else names another Kinesis stream |
| `KVS_REGION` | `us-east-1` | region of the stream |
| `KVS_RETENTION_HOURS` | `2` | how long Kinesis keeps the video |
| `KVS_KEYFRAME_SEC` | `1` | key-frame interval = fragment length (1 for lowest latency, 2 for robustness) |
| `KVS_OVERLAY` | `true` | draw the runner's detections on the uploaded frames |
| `KVS_KEEP_ONLINE` | `auto` | hold an MQTT session for a companion camera device (see below); `true`/`false` force it |
| `KVS_CREDENTIALS_DIR` | `/app/data/kvs` | device identity files (falls back to `/app/data/iotconnect`) |
| `KVS_LIBS_DIR` | `/app/data/kvs/libs` | `kvssink` and its libraries |

## API

```python
kvs.is_streaming()        # True while frames are being uploaded
kvs.start_stream()        # when KVS_AUTOSTART=false, or after stop_stream()
kvs.stop_stream()
kvs.push_frame(jpeg)      # KVS_SOURCE=push: hand a JPEG-encoded frame over
kvs.on_state(fn)          # fn(True/False) when the upload starts or stops
kvs.status()              # dict for logs or telemetry
```

## Overlays

With `KVS_OVERLAY=true` (default) the brick draws the video runner's results on the uploaded frames: a box with
label and confidence per detected object (object detection, face detection, object hunting) or the top label for
image classification. The runner reports boxes in preview-frame pixels, so they line up with the picture. Apps that
feed frames with `push_frame()` can pass their own results with `kvs.set_overlay([...])` (items with `label`,
optional `confidence` and optional `box=(x1, y1, x2, y2)`); results older than 1.5 s are not drawn.

## Latency

HLS playback is a few fragment lengths behind the camera: with the default 1-second fragments expect about 3 to 4
seconds in the App Lab Cloud Console (its player keeps 2 s of buffer and catches up at 1.3x when it falls behind) and
a bit more in the /IOTCONNECT portal, whose player buffers on its own. `KVS_KEYFRAME_SEC=2` trades latency for
robustness on a weak network. Sub-second latency would need the WebRTC flavour of /IOTCONNECT video streaming, which
is a different device pipeline.

## Devices created before video streaming was enabled (companion camera device)

/IOTCONNECT gives a device its Kinesis stream resource when the device is created. Enabling Video Streaming on the
template later and editing the device did not give an existing device the resource in our account (the device
identity never gets the `vs` credentials block and `client-streaming-url` stays empty), so for such a device create
a **second device on the same template with video streaming on**, named `<device>cam` (`ventunoQ0cam` for the
workshop's VENTUNO Q), download its certificate and point the brick at it:

```bash
mkdir -p ~/.iotconnect-cam   # iotcDeviceConfig.json, device-cert.pem, device-pkey.pem of <device>cam
bash /home/arduino/iotc-arduino-uno-q-workshop/scripts/add_kvs_brick.sh <APP_LAB_FOLDER> --creds-from ~/.iotconnect-cam
```

The app keeps talking to /IOTCONNECT as itself; only the video goes out as `<device>cam`. The portal serves playback
only for devices it sees connected, so when the brick's credentials belong to a different device than the app's own
(`data/kvs` and `data/iotconnect` name different devices) it also holds an MQTT session for the camera device
(`KVS_KEEP_ONLINE=auto`). The App Lab Cloud Console looks for `<device>cam` automatically when `<device>` has no
stream; in the portal, open the camera device's **Video Streaming** tab.

## Watching the stream

- /IOTCONNECT: the device's **Video Streaming** tab.
- App Lab Cloud Console: the **Live video** panel of the running camera app (it reads
  `GET /api/v2.1/Device/client-streaming-url?uniqueId=<device>` and plays the returned HLS session).

## Notes and limits

- The portal's Start/Stop buttons send cloud-to-device messages 112/113 to the device's MQTT session. With the
  workshop's relay service that session belongs to the relay, which does not forward them yet, so the brick streams
  whenever the app runs (`KVS_AUTOSTART`). Apps on the /IOTCONNECT brick in direct mode can wire `start_stream()` /
  `stop_stream()` to those messages themselves.
- The prebuilt `kvssink` comes from Avnet's
  [Tria Vision AI-KIT 6490 PutMedia demo](https://github.com/avnet-iotconnect/iotc-python-lite-sdk-demos/tree/main/tria-vision-ai-kit-6490/kvs-putmedia)
  (aarch64). `h264parse` and the LDAP libraries come from Debian's arm64 packages; App Lab's container image is Debian 13
  with GStreamer 1.26, so the plugin versions pinned in `scripts/add_kvs_brick.sh` match it.
- `x264enc` is not in the App Lab image; on boards without a V4L2 hardware encoder install a software encoder first.
- The brick asks the Venus encoder for `constrained-baseline` level 4 explicitly. Left to its defaults the encoder writes
  Level 1.0 into the SPS, which ffmpeg tolerates but browser hardware decoders do not: the player's clock runs and the
  picture stays black. The key-frame interval is set with the driver's `video_gop_size` control (`h264_i_frame_period`
  has no effect on this driver).
- The hardware encoder and the model runner share the board: expect about 10 fps at 640x480 next to YOLOX detection.
