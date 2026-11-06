# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Avnet
"""KVS Video Stream brick for Arduino App Lab.

Streams the app's camera to /IOTCONNECT Video Streaming (AWS Kinesis Video Streams, PutMedia).

Where the frames come from
    ``KVS_SOURCE=auto`` (default): the brick connects to the websocket of the app's Edge Impulse video
    runner (the ``video_object_detection`` and ``video_image_classification`` bricks), switches its camera
    preview on and receives the JPEG frames the runner already decodes. The camera stays owned by the runner,
    so detection keeps working and no second camera reader is needed.
    ``KVS_SOURCE=push``: the app hands JPEG frames over with ``push_frame(jpeg_bytes)`` (apps that own the
    camera themselves, e.g. with ``arduino.app_peripherals.camera.Camera``).

How they get to the cloud
    A GStreamer pipeline decodes the JPEGs, re-encodes them with the board's hardware H.264 encoder
    (``v4l2h264enc``, the Qualcomm Venus codec on the UNO Q) and uploads with the AWS KVS producer plugin
    ``kvssink``. The plugin and its libraries live in ``data/kvs/libs`` (``scripts/add_kvs_brick.sh`` puts
    them there), the device identity in ``data/kvs``. ``kvssink`` obtains and refreshes AWS credentials itself
    from the /IOTCONNECT credentials endpoint with the device certificate; the stream name is the device's
    client id, which is what the portal's Video Streaming tab and the App Lab Cloud Console play.

Usage
    from kvs import KvsStream
    kvs = KvsStream()          # before App.run(); streams as soon as the app runs (KVS_AUTOSTART)
    kvs.is_streaming()         # True while frames are being uploaded
    kvs.stop_stream() / kvs.start_stream()
    kvs.push_frame(jpeg)       # KVS_SOURCE=push
"""

from __future__ import annotations

import base64
import json
import os
import queue
import shutil
import socket
import subprocess
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from arduino.app_utils import Logger, brick

logger = Logger("KvsStream")

CONFIG_FILE = "iotcDeviceConfig.json"
CERT_FILE = "device-cert.pem"
KEY_FILE = "device-pkey.pem"
RUNNER_HOSTS = ("ei-video-obj-detection-runner", "ei-video-classification-runner")
RUNNER_PORT = 4912
CA_CANDIDATES = ("/etc/ssl/certs/Amazon_Root_CA_1.pem", "/etc/ssl/certs/ca-certificates.crt")
_TICK_S = 0.5
_RETRY_S = 5.0
_QUEUE_FRAMES = 4
_TOKEN_REFRESH_MARGIN_S = 300


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return default if value is None or value == "" else value


def _env_bool(name: str, default: bool) -> bool:
    value = _env(name).strip().lower()
    if not value:
        return default
    return value in ("1", "true", "yes", "on")


def _resolvable(host: str) -> bool:
    try:
        socket.gethostbyname(host)
        return True
    except OSError:
        return False


@brick
class KvsStream:
    """Streams the app's camera to /IOTCONNECT Video Streaming (AWS Kinesis Video Streams).

    Instantiate it before ``App.run()``; the app framework starts and stops it. Everything is configurable
    through the brick's variables or the constructor arguments below.

    Args:
        credentials_dir: Folder with ``iotcDeviceConfig.json``, ``device-cert.pem`` and ``device-pkey.pem``.
            Default ``KVS_CREDENTIALS_DIR`` or ``/app/data/kvs`` (falls back to ``/app/data/iotconnect``).
        libs_dir: Folder with ``libgstkvssink.so`` and its libraries. Default ``KVS_LIBS_DIR``.
        source: ``"auto"`` (video runner frames) or ``"push"`` (frames from ``push_frame``). Default ``KVS_SOURCE``.
        fps: Frames per second sent to the stream. Default ``KVS_FPS`` or 10.
        bitrate: H.264 bitrate in bit/s. Default ``KVS_BITRATE`` or 600000.
        autostart: Stream as soon as the app runs. Default ``KVS_AUTOSTART`` or true.
        stream_name: Kinesis stream name; ``"auto"`` = the device's client id. Default ``KVS_STREAM_NAME``.
        region: AWS region. Default ``KVS_REGION`` or ``us-east-1``.
    """

    def __init__(
        self,
        credentials_dir: str | os.PathLike[str] | None = None,
        libs_dir: str | os.PathLike[str] | None = None,
        source: str | None = None,
        fps: float | None = None,
        bitrate: int | None = None,
        autostart: bool | None = None,
        stream_name: str | None = None,
        region: str | None = None,
    ) -> None:
        base = Path(credentials_dir) if credentials_dir is not None else Path(_env("KVS_CREDENTIALS_DIR", "/app/data/kvs"))
        if not (base / CONFIG_FILE).is_file() and (base.parent / "iotconnect" / CONFIG_FILE).is_file():
            base = base.parent / "iotconnect"
        self._creds_dir = base
        self._config_path = base / CONFIG_FILE
        self._cert_path = base / CERT_FILE
        self._key_path = base / KEY_FILE
        self._libs_dir = Path(libs_dir) if libs_dir is not None else Path(_env("KVS_LIBS_DIR", "/app/data/kvs/libs"))
        self._source = (source or _env("KVS_SOURCE", "auto")).strip().lower()
        if self._source not in ("auto", "push"):
            raise ValueError(f"KvsStream source must be 'auto' or 'push', got '{self._source}'")
        try:
            self._fps = float(fps if fps is not None else _env("KVS_FPS", "10"))
        except ValueError:
            self._fps = 10.0
        self._fps = min(30.0, max(1.0, self._fps))
        try:
            self._bitrate = int(bitrate if bitrate is not None else _env("KVS_BITRATE", "600000"))
        except ValueError:
            self._bitrate = 600000
        self._want_stream = autostart if autostart is not None else _env_bool("KVS_AUTOSTART", True)
        name = (stream_name or _env("KVS_STREAM_NAME", "auto")).strip()
        self._stream_name_override = "" if name.lower() == "auto" else name
        self._region = region or _env("KVS_REGION", "us-east-1")
        try:
            self._retention_hours = max(0, int(_env("KVS_RETENTION_HOURS", "2")))
        except ValueError:
            self._retention_hours = 2
        self._auth = _env("KVS_AUTH", "iot").strip().lower()
        if self._auth not in ("iot", "token"):
            self._auth = "iot"
        self._log_config = Path(__file__).with_name("kvs_log_configuration")

        self._running = False
        self._proc: subprocess.Popen[bytes] | None = None
        self._frames: queue.Queue[bytes] = queue.Queue(maxsize=_QUEUE_FRAMES)
        self._session_alive = threading.Event()
        self._last_frame_ts = 0.0
        self._frames_sent = 0
        self._identity: dict[str, Any] | None = None
        self._token_expiry: float = 0.0
        self._last_error = ""
        self._gst_tail: list[str] = []
        self._state_callbacks: list[Callable[[bool], Any]] = []
        self._was_streaming = False
        self._runner_host = ""

    # --- public API ---

    @property
    def stream_name(self) -> str:
        """The Kinesis stream name (known once the device identity has been read)."""
        if self._stream_name_override:
            return self._stream_name_override
        return (self._identity or {}).get("client_id", "")

    def is_streaming(self) -> bool:
        """True while the upload pipeline runs and frames arrived in the last 5 seconds."""
        proc = self._proc
        return proc is not None and proc.poll() is None and (time.time() - self._last_frame_ts) < 5.0

    def start_stream(self) -> None:
        """Starts (or resumes) streaming. Not needed when KVS_AUTOSTART is true."""
        self._want_stream = True

    def stop_stream(self) -> None:
        """Stops streaming; the app keeps running."""
        self._want_stream = False

    def push_frame(self, jpeg: bytes) -> bool:
        """Hands a JPEG-encoded frame to the stream (``KVS_SOURCE=push``). Drops the oldest frame when the
        pipeline is behind. Returns False when no stream session is active."""
        if not self._session_alive.is_set():
            return False
        self._enqueue(jpeg)
        return True

    def on_state(self, fn: Callable[[bool], Any]) -> None:
        """Calls ``fn(streaming)`` when the stream starts delivering frames or stops."""
        self._state_callbacks.append(fn)

    def status(self) -> dict[str, Any]:
        """A summary for logs or telemetry."""
        return {
            "streaming": self.is_streaming(),
            "wanted": self._want_stream,
            "stream_name": self.stream_name,
            "source": self._source,
            "runner": self._runner_host,
            "frames_sent": self._frames_sent,
            "last_error": self._last_error,
        }

    # --- lifecycle, driven by the app framework ---

    def start(self) -> None:
        self._running = True
        logger.info(f"Source: {self._source}, {self._fps:g} fps, {self._bitrate} bit/s, auth: {self._auth}, autostart: {self._want_stream}")
        missing = [p for p in (self._config_path, self._cert_path, self._key_path) if not p.is_file()]
        if missing:
            logger.error("Missing device credentials: " + ", ".join(str(p) for p in missing)
                         + ". Run scripts/add_kvs_brick.sh <app> on the board to copy them.")
        if not (self._libs_dir / "libgstkvssink.so").is_file():
            logger.error(f"KVS producer plugin not found in {self._libs_dir}. Run scripts/add_kvs_brick.sh <app> on the board.")

    def stop(self) -> None:
        self._running = False
        self._want_stream = False
        self._end_session()

    def loop(self) -> None:
        """One streaming session per iteration; waits while streaming is not wanted."""
        if not self._running or not self._want_stream:
            time.sleep(_TICK_S)
            return
        if not self._ready():
            time.sleep(_RETRY_S)
            return
        try:
            self._run_session()
        except Exception as exc:  # noqa: BLE001 - keep the app alive whatever the stream does
            self._last_error = str(exc)
            logger.error(f"Stream session failed: {exc}")
        self._set_streaming(False)
        if self._running and self._want_stream:
            time.sleep(_RETRY_S)

    @brick.loop
    def _watch_state(self) -> None:
        streaming = self.is_streaming()
        if streaming != self._was_streaming:
            self._set_streaming(streaming)
        time.sleep(1.0)

    # --- internals ---

    def _set_streaming(self, streaming: bool) -> None:
        if streaming == self._was_streaming:
            return
        self._was_streaming = streaming
        logger.info("Streaming to Kinesis Video: " + ("started" if streaming else "stopped"))
        for fn in list(self._state_callbacks):
            try:
                fn(streaming)
            except Exception as exc:  # noqa: BLE001
                logger.error(f"on_state callback failed: {exc}")

    def _ready(self) -> bool:
        ok = all(p.is_file() for p in (self._config_path, self._cert_path, self._key_path)) and (self._libs_dir / "libgstkvssink.so").is_file()
        if not ok:
            return False
        if self._identity is None:
            try:
                self._identity = self._read_identity()
            except Exception as exc:  # noqa: BLE001
                self._last_error = str(exc)
                logger.error(f"Could not read the device identity from /IOTCONNECT: {exc}")
                return False
            logger.info(f"Device {self._identity['client_id']}: video streaming "
                        + ("enabled" if self._identity.get("vs_url") else "NOT enabled in the device template"))
        if not self._identity.get("vs_url"):
            self._last_error = "Video streaming is not enabled for this device's template in /IOTCONNECT"
            return False
        return True

    def _read_identity(self) -> dict[str, Any]:
        from avnet.iotconnect.sdk.lite import DeviceConfig
        from avnet.iotconnect.sdk.sdklib.dra import DeviceRestApi

        cfg = DeviceConfig.from_iotc_device_config_json_file(
            device_config_json_path=str(self._config_path), device_cert_path=str(self._cert_path), device_pkey_path=str(self._key_path)
        )
        dra = DeviceRestApi(cfg.to_properties())
        identity = dra.get_identity_data()
        vs = getattr(identity, "vs", None)
        return {
            "client_id": identity.client_id,
            "vs_url": getattr(vs, "url", "") or "",
            "auto_start": bool(getattr(vs, "as_", True)),
            "dra": dra,
        }

    def _fetch_token(self) -> dict[str, str]:
        """Temporary AWS credentials through the /IOTCONNECT SDK (KVS_AUTH=token)."""
        dra = self._identity["dra"]  # type: ignore[index]
        creds = dra.get_aws_credentials_kvs(device_cert_path=str(self._cert_path), device_pkey_path=str(self._key_path))
        expiry = getattr(creds, "expiration", None)
        if isinstance(expiry, datetime):
            self._token_expiry = expiry.replace(tzinfo=expiry.tzinfo or timezone.utc).timestamp()
        else:
            self._token_expiry = time.time() + 3000
        return {"ak": creds.access_key_id, "sk": creds.secret_access_key, "st": creds.session_token}

    def _encoder(self) -> str:
        env = self._gst_env()
        for name in ("v4l2h264enc", "x264enc", "openh264enc"):
            if subprocess.run(["gst-inspect-1.0", name], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                return name
        raise RuntimeError("no H.264 encoder found in this container (v4l2h264enc, x264enc or openh264enc)")

    def _gst_env(self) -> dict[str, str]:
        libs = str(self._libs_dir)
        env = dict(os.environ)
        env["GST_PLUGIN_PATH"] = libs + (":" + env["GST_PLUGIN_PATH"] if env.get("GST_PLUGIN_PATH") else "")
        env["LD_LIBRARY_PATH"] = libs + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
        env["GST_REGISTRY"] = str(self._libs_dir / ".gst-registry.bin")
        env.setdefault("GST_DEBUG", "1")
        return env

    def _build_command(self, encoder: str) -> list[str]:
        fps = int(round(self._fps))
        keyframe_period = max(1, fps)  # one key frame per second: kvssink cuts fragments at key frames
        if encoder == "v4l2h264enc":
            # Ask for constrained-baseline level 4 explicitly: left alone, the Venus encoder stamps Level 1.0 into
            # the SPS (invalid for 640x480), and browser hardware decoders then show a black picture. The V4L2
            # controls are the ones the Venus driver exposes (video_gop_size sets the key-frame interval; CBR keeps
            # the upload near the requested bitrate instead of the driver's 1 Mbit/s VBR default).
            enc = ["videoconvert", "!", "video/x-raw,format=NV12", "!", "videorate", "!", f"video/x-raw,framerate={fps}/1", "!",
                   "v4l2h264enc", ("extra-controls=controls,video_bitrate_mode=1,"
                                   f"video_bitrate={self._bitrate},video_peak_bitrate={self._bitrate * 4 // 3},"
                                   f"video_gop_size={keyframe_period},h264_i_frame_period={keyframe_period}"),
                   "!", "video/x-h264,profile=constrained-baseline,level=(string)4"]
        elif encoder == "x264enc":
            enc = ["videoconvert", "!", "videorate", "!", f"video/x-raw,framerate={fps}/1", "!",
                   "x264enc", "tune=zerolatency", "speed-preset=ultrafast", f"bitrate={max(100, self._bitrate // 1000)}", f"key-int-max={keyframe_period}"]
        else:
            enc = ["videoconvert", "!", "videorate", "!", f"video/x-raw,framerate={fps}/1", "!",
                   "openh264enc", f"bitrate={self._bitrate}", f"gop-size={keyframe_period}"]
        sink = ["kvssink", f"stream-name={self.stream_name}", f"aws-region={self._region}", "storage-size=128",
                f"retention-period={self._retention_hours}", f"framerate={fps}", "allow-create-stream=true"]
        if self._log_config.is_file():
            sink.append(f"log-config={self._log_config}")
        if self._auth == "iot":
            # The endpoint is https://<prefix>.credentials.iot.<region>.amazonaws.com/role-aliases/<alias>/credentials;
            # kvssink wants the host and the alias and builds the path itself.
            vs = urlparse(self._identity["vs_url"])  # type: ignore[index]
            path = vs.path.rstrip("/")
            if path.endswith("/credentials"):
                path = path[: -len("/credentials")]
            alias = path.rsplit("/", 1)[-1]
            ca = next((c for c in CA_CANDIDATES if Path(c).is_file()), "")
            parts = [f"endpoint={vs.netloc}", f"cert-path={self._cert_path}", f"key-path={self._key_path}", f"role-aliases={alias}",
                     f"iot-thing-name={self._identity['client_id']}"]  # type: ignore[index]
            if ca:
                parts.append(f"ca-path={ca}")
            sink.append("iot-certificate=iot-certificate," + ",".join(parts))
        else:
            tok = self._fetch_token()
            sink += [f"access-key={tok['ak']}", f"secret-key={tok['sk']}", f"session-token={tok['st']}"]
        return (["gst-launch-1.0", "-e", "-q", "fdsrc", "fd=0", "do-timestamp=true", "!", "multipartdemux", "!", "image/jpeg", "!", "jpegdec", "!"]
                + enc + ["!", "h264parse", "config-interval=-1", "!", "video/x-h264,stream-format=avc,alignment=au", "!"] + sink)

    def _run_session(self) -> None:
        encoder = self._encoder()
        cmd = self._build_command(encoder)
        logger.info(f"Starting upload to Kinesis stream '{self.stream_name}' ({self._region}) with {encoder}")
        self._gst_tail = []
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=self._gst_env())
        self._proc = proc
        self._frames = queue.Queue(maxsize=_QUEUE_FRAMES)
        self._session_alive.set()
        threading.Thread(target=self._read_gst_output, args=(proc,), name="KvsStream.gst-log", daemon=True).start()
        writer = threading.Thread(target=self._write_frames, args=(proc,), name="KvsStream.writer", daemon=True)
        writer.start()
        source = None
        if self._source == "auto":
            source = threading.Thread(target=self._pump_runner_frames, name="KvsStream.runner", daemon=True)
            source.start()
        started = time.time()
        try:
            while self._running and self._want_stream and proc.poll() is None:
                if self._auth == "token" and self._token_expiry and time.time() > self._token_expiry - _TOKEN_REFRESH_MARGIN_S:
                    logger.info("AWS credentials expire soon, restarting the upload with fresh ones")
                    break
                time.sleep(_TICK_S)
        finally:
            self._session_alive.clear()
            self._end_session()
            if source is not None:
                source.join(timeout=5)
            writer.join(timeout=5)
        rc = proc.poll()
        if rc not in (None, 0) and self._want_stream:
            tail = " | ".join(self._gst_tail[-4:])
            self._last_error = f"gst-launch exited with {rc}: {tail}"
            logger.error(self._last_error)
            if self._auth == "iot" and time.time() - started < 30 and ("credential" in tail.lower() or "403" in tail or "auth" in tail.lower()):
                logger.warning("Switching to SDK-fetched credentials (KVS_AUTH=token) after an authentication failure")
                self._auth = "token"

    def _end_session(self) -> None:
        proc = self._proc
        if proc is None:
            return
        self._proc = None
        try:
            if proc.stdin:
                proc.stdin.close()  # EOS: kvssink flushes the last fragment
        except OSError:
            pass
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    def _read_gst_output(self, proc: subprocess.Popen[bytes]) -> None:
        assert proc.stdout is not None
        for raw in iter(proc.stdout.readline, b""):
            line = raw.decode(errors="replace").rstrip()
            if not line:
                continue
            self._gst_tail = (self._gst_tail + [line])[-20:]
            low = line.lower()
            if "error" in low or "[warn" in low or "warning" in low:
                logger.warning(f"gst: {line[:300]}")
            else:
                logger.debug(f"gst: {line[:300]}")

    def _enqueue(self, jpeg: bytes) -> None:
        try:
            self._frames.put_nowait(jpeg)
        except queue.Full:
            try:
                self._frames.get_nowait()
            except queue.Empty:
                pass
            try:
                self._frames.put_nowait(jpeg)
            except queue.Full:
                pass

    def _write_frames(self, proc: subprocess.Popen[bytes]) -> None:
        assert proc.stdin is not None
        while self._session_alive.is_set() and proc.poll() is None:
            try:
                jpeg = self._frames.get(timeout=_TICK_S)
            except queue.Empty:
                continue
            part = b"--kvsframe\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(jpeg) + jpeg + b"\r\n"
            try:
                proc.stdin.write(part)
                proc.stdin.flush()
            except (BrokenPipeError, OSError):
                return
            self._frames_sent += 1
            self._last_frame_ts = time.time()

    def _pump_runner_frames(self) -> None:
        """Receives the camera preview of the app's video runner over its websocket."""
        from websockets.sync.client import connect

        announced = False
        while self._session_alive.is_set():
            host = self._runner_host or next((h for h in RUNNER_HOSTS if _resolvable(h)), "")
            if not host:
                if not announced:
                    logger.warning("No video runner found (video_object_detection / video_image_classification brick). "
                                   "Set KVS_SOURCE=push and call push_frame() from the app.")
                    announced = True
                time.sleep(_RETRY_S)
                continue
            self._runner_host = host
            try:
                with connect(f"ws://{host}:{RUNNER_PORT}", max_size=None, open_timeout=10) as ws:
                    ws.send(json.dumps({"type": "toggle-camera-preview", "enabled": True}))
                    logger.info(f"Receiving camera frames from {host}")
                    while self._session_alive.is_set():
                        try:
                            message = ws.recv(timeout=2)
                        except TimeoutError:
                            continue
                        try:
                            msg = json.loads(message)
                        except (TypeError, ValueError):
                            continue
                        if msg.get("type") != "camera-preview":
                            continue
                        image = msg.get("image") or ""
                        if "," in image:
                            image = image.split(",", 1)[1]
                        try:
                            self._enqueue(base64.b64decode(image))
                        except (ValueError, TypeError):
                            continue
            except Exception as exc:  # noqa: BLE001 - the runner restarts with the app, keep retrying
                if self._session_alive.is_set():
                    logger.warning(f"Video runner connection lost ({exc}); retrying")
                    time.sleep(2.0)
