# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Avnet
# /IOTCONNECT Brick for Arduino App Lab.
"""/IOTCONNECT Brick for Arduino App Lab.

Add the brick to an app (``bricks/iotconnect`` folder plus ``- iotconnect`` under ``bricks:``
in ``app.yaml``), then in ``python/main.py``:

    from arduino.app_utils import App
    from iotconnect import IoTConnect

    iotc = IoTConnect()

    @iotc.command("set-led")
    def set_led(args: list[str]) -> None:
        ...  # e.g. Bridge.call("set_led_state", args[0] == "1")

    def loop() -> None:
        iotc.send_telemetry({"temperature": 21.5})  # connected once App.run() has started the brick
        time.sleep(5)

    App.run(user_loop=loop)

The brick reaches the cloud in one of two ways, chosen with ``IOTC_MODE`` (``auto`` by default):

* ``direct`` - the app itself is the /IOTCONNECT device. It needs ``iotcDeviceConfig.json``,
  ``device-cert.pem`` and ``device-pkey.pem`` in ``IOTC_CREDENTIALS_DIR`` (``data/iotconnect``
  inside the app folder by default). Commands are acknowledged and OTA requests are delivered.
* ``relay`` - the app talks to the board's ``iotc-relay`` service (the workshop setup), which owns
  the credentials and the cloud connection. The relay acknowledges commands itself, batches
  telemetry every few seconds and lets several apps share one device.

``auto`` picks ``direct`` when the credential files exist and ``relay`` otherwise.
"""

from __future__ import annotations

import json
import math
import os
import queue
import socket
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from arduino.app_utils import Logger, brick

logger = Logger("IoTConnect")

__all__ = [
    "IoTConnect",
    "OtaFile",
    "OtaRequest",
    "MODE_AUTO",
    "MODE_DIRECT",
    "MODE_RELAY",
]

MODE_AUTO = "auto"
MODE_DIRECT = "direct"
MODE_RELAY = "relay"
_MODES = (MODE_AUTO, MODE_DIRECT, MODE_RELAY)

CONFIG_FILE = "iotcDeviceConfig.json"
CERT_FILE = "device-cert.pem"
KEY_FILE = "device-pkey.pem"

DEFAULT_RELAY_ENDPOINT = "tcp://172.17.0.1:8899"
"""The host side of the app container's Docker bridge, where iotc-relay listens."""

_LOOP_TICK_S = 0.5
_RECONNECT_MIN_S = 2.0
_RECONNECT_MAX_S = 60.0
_AUTO_RECONNECT_GRACE_S = 20.0
"""How long a dropped direct session is left to the MQTT library's own reconnect before it is rebuilt."""
_RELAY_KEEPALIVE_S = 30.0
"""The relay server closes clients that stay silent for 60 s."""
_RELAY_CONNECT_TIMEOUT_S = 5.0
_RELAY_IO_TIMEOUT_S = 5.0
_RELAY_WINDOW_S = 5.0
"""The relay server forwards only the LAST telemetry message of each client every 5 s, so the
brick re-sends every value it published in the last window together with the new ones."""
_RELAY_DUPLICATE_WINDOW_S = 0.25
"""The relay server delivers each command line twice to a registered client (it keeps the
connection under two keys); identical lines this close together are collapsed into one."""
_RELAY_STABLE_SESSION_S = 60.0
"""A relay session that lasted at least this long resets the reconnect backoff when it drops."""
_DISCOVERY_TIMEOUT_S = 60.0
"""Upper bound for the SDK's REST discovery call, which has no timeout of its own."""


@dataclass(frozen=True)
class OtaFile:
    """One file of an OTA package."""

    url: str
    file_name: str


@dataclass(frozen=True)
class OtaRequest:
    """An OTA update request from /IOTCONNECT (direct mode only)."""

    version: str
    files: tuple[OtaFile, ...]
    hardware_version: str | None = None


CommandHandler = Callable[[list[str]], Any]
"""Handler for one named command. Receives the command arguments.
Return False (or raise) to report failure, a string to attach a message to the success ack."""

AnyCommandHandler = Callable[[str, list[str]], Any]
"""Catch-all command handler. Receives the command name and its arguments."""

OtaHandler = Callable[[OtaRequest], Any]
"""OTA handler. Download and install the files, return True once the new version is running."""

_AckFn = Callable[[bool, str | None], None]
_OtaAckFn = Callable[[int, str | None], None]


@dataclass(frozen=True)
class _Command:
    name: str
    args: list[str]
    ack: _AckFn | None


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def _default_credentials_dir() -> Path:
    # bricks/iotconnect/__init__.py -> the app folder is two levels up (/app inside the container)
    return Path(__file__).resolve().parent.parent.parent / "data" / "iotconnect"


def _default_client_id() -> str:
    app_home = _env("APP_HOME")
    if app_home:
        name = Path(app_home).name
        if name:
            return name
    return "applab-app"


def _jsonable(value: Any) -> Any:  # noqa: ANN401
    """Turns a telemetry value into something the JSON encoder accepts (numpy scalars, dates, NaN...)."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return None if (math.isnan(value) or math.isinf(value)) else value
    if isinstance(value, Decimal):
        return _jsonable(float(value))
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    tolist = getattr(value, "tolist", None)  # numpy arrays and scalars
    if callable(tolist):
        try:
            return _jsonable(tolist())
        except Exception:
            pass
    item = getattr(value, "item", None)  # other numpy-like scalars
    if callable(item):
        try:
            return _jsonable(item())
        except Exception:
            pass
    return str(value)


def _parse_relay_args(parameters: Any) -> list[str]:  # noqa: ANN401
    """The relay forwards command parameters as one space-joined string."""
    if parameters is None:
        return []
    if isinstance(parameters, str):
        return parameters.split()
    if isinstance(parameters, (list, tuple)):
        return [str(p) for p in parameters]
    return [json.dumps(parameters)]


class _DirectBackend:
    """The app is the /IOTCONNECT device: MQTT over TLS through the /IOTCONNECT Python Lite SDK."""

    def __init__(
        self,
        config_path: Path,
        cert_path: Path,
        key_path: Path,
        server_ca_path: Path | None,
        on_command: Callable[[_Command], None],
        on_ota: Callable[[OtaRequest, _OtaAckFn], None],
        on_lost: Callable[[str], None],
    ) -> None:
        self._config_path = config_path
        self._cert_path = cert_path
        self._key_path = key_path
        self._server_ca_path = server_ca_path
        self._on_command = on_command
        self._on_ota = on_ota
        self._on_lost = on_lost
        self._client: Any = None
        self._session_up = False  # True only between an observed connection and its loss
        self._lost_at: float | None = None
        self._next_attempt_at = 0.0
        self._backoff_s = _RECONNECT_MIN_S

    @property
    def description(self) -> str:
        return f"direct (credentials in {self._config_path.parent})"

    def missing_files(self) -> list[Path]:
        return [p for p in (self._config_path, self._cert_path, self._key_path) if not p.is_file()]

    def is_connected(self) -> bool:
        client = self._client
        return client is not None and bool(client.is_connected())

    def ensure_connected(self) -> bool:
        """Keeps one MQTT session alive. Blocks while an attempt is in progress: up to ~25 s for
        the MQTT connect, plus up to _DISCOVERY_TIMEOUT_S for the SDK's REST discovery call."""
        now = time.monotonic()
        client = self._client
        if client is not None:
            if client.is_connected():
                self._session_up = True
                self._lost_at = None
                return True
            if self._lost_at is None:
                self._lost_at = now
            if now - self._lost_at < _AUTO_RECONNECT_GRACE_S:
                return False  # the MQTT library may still reconnect by itself
            logger.warning("Still disconnected, rebuilding the /IOTCONNECT session")
            self._teardown()

        if now < self._next_attempt_at:
            return False

        missing = self.missing_files()
        if missing:
            logger.error("Missing credential file(s): " + ", ".join(str(p) for p in missing))
        else:
            try:
                self._client = self._build_client_with_timeout()
                self._client.connect()  # one attempt, see ClientSettings below
            except Exception as e:
                logger.error(f"Could not connect to /IOTCONNECT: {e}")
                self._teardown()

        if self.is_connected():
            self._session_up = True
            self._lost_at = None
            self._backoff_s = _RECONNECT_MIN_S
            logger.info("Connected to /IOTCONNECT")
            return True

        self._teardown()
        logger.warning(f"Not connected to /IOTCONNECT, next attempt in {self._backoff_s:.0f}s")
        self._next_attempt_at = time.monotonic() + self._backoff_s
        self._backoff_s = min(self._backoff_s * 2, _RECONNECT_MAX_S)
        return False

    def disconnect(self) -> None:
        self._teardown()

    def send(self, values: dict[str, Any], timestamp: datetime | None) -> bool:
        client = self._client
        if client is None or not client.is_connected():
            return False
        try:
            client.send_telemetry(values, timestamp=timestamp)
            return True
        except Exception as e:
            logger.error(f"Telemetry send failed: {e}")
            return False

    def _build_client_with_timeout(self) -> Any:  # noqa: ANN401
        """The SDK's constructor does a REST discovery call without a timeout; bound it so a stalled
        HTTP connection cannot freeze the brick's loop thread for good."""
        result: dict[str, Any] = {}

        def build() -> None:
            try:
                result["client"] = self._build_client()
            except BaseException as e:  # noqa: BLE001 - re-raised on the loop thread
                result["error"] = e

        worker = threading.Thread(target=build, name="IoTConnect.discovery", daemon=True)
        worker.start()
        worker.join(_DISCOVERY_TIMEOUT_S)
        if worker.is_alive():
            # The worker finishes on its own later; its client is never connected and gets collected.
            raise TimeoutError(f"/IOTCONNECT discovery did not answer within {_DISCOVERY_TIMEOUT_S:.0f}s")
        if "error" in result:
            raise result["error"]
        return result["client"]

    def _build_client(self) -> Any:  # noqa: ANN401
        from avnet.iotconnect.sdk.lite import Callbacks, Client, ClientSettings, DeviceConfig

        device_config = DeviceConfig.from_iotc_device_config_json_file(
            device_config_json_path=str(self._config_path),
            device_cert_path=str(self._cert_path),
            device_pkey_path=str(self._key_path),
            server_ca_cert_path=str(self._server_ca_path) if self._server_ca_path else None,
        )
        # connect_tries=2 means exactly one attempt per call (the SDK loops over range(1, tries));
        # this brick's loop owns the retry cadence.
        settings = ClientSettings(verbose=False, connect_timeout_secs=20, connect_tries=2, connect_backoff_max_secs=2)
        callbacks = Callbacks(
            command_cb=self._on_sdk_command,
            ota_cb=self._on_sdk_ota,
            disconnected_cb=self._on_sdk_disconnect,
        )
        client = Client(config=device_config, callbacks=callbacks, settings=settings)
        self._install_resubscribe_hook(client)
        logger.info(f"Device '{client.get_duid()}' (client id '{client.get_client_id()}')")
        return client

    @staticmethod
    def _install_resubscribe_hook(client: Any) -> None:  # noqa: ANN401
        """The SDK subscribes to the command topic only inside connect(); the MQTT library's own
        reconnect would come back without it. Re-subscribe on every (re)connect."""
        try:
            topic = client._identity_data.topics.c2d
            mqttc = client.mqtt
            previous = mqttc.on_connect
        except AttributeError:
            logger.debug("SDK internals changed, skipping the re-subscribe hook")
            return

        def on_connect(mqttc: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:  # noqa: ANN401
            if previous is not None:
                previous(mqttc, userdata, flags, reason_code, properties)
            if not getattr(reason_code, "is_failure", False):
                try:
                    mqttc.subscribe(topic, qos=1)
                except Exception as e:
                    logger.warning(f"Could not re-subscribe to commands: {e}")

        mqttc.on_connect = on_connect

    def _teardown(self) -> None:
        client, self._client = self._client, None
        self._session_up = False
        self._lost_at = None
        if client is None:
            return
        try:
            client.mqtt.loop_stop()
        except Exception:
            pass
        try:
            client.disconnect()
        except Exception:
            pass

    # --- SDK callbacks, called on the MQTT network thread ---

    def _publish_ack(self, what: str, send: Callable[[Any], Any]) -> None:
        """Runs an SDK ack call against the CURRENT session (the one at message time may have been
        rebuilt while the handler ran) and reports a lost ack, which the SDK itself only prints."""
        client = self._client
        if client is None or not client.is_connected():
            logger.error(f"Could not acknowledge {what}: not connected")
            return
        try:
            info = send(client)
        except Exception as e:
            logger.error(f"Could not acknowledge {what}: {e}")
            return
        rc = getattr(info, "rc", 0)
        if info is None or rc != 0:
            logger.error(f"Could not acknowledge {what}: publish returned {rc if info is not None else 'nothing'}")

    def _on_sdk_command(self, msg: Any) -> None:  # noqa: ANN401
        name = msg.command_name or ""
        args = [str(a) for a in (msg.command_args or [])]
        ack: _AckFn | None = None
        if msg.ack_id:

            def send_command_ack(success: bool, message: str | None) -> None:
                from avnet.iotconnect.sdk.lite import C2dAck

                status = C2dAck.CMD_SUCCESS_WITH_ACK if success else C2dAck.CMD_FAILED
                # send_ack() returns the publish result; the SDK's send_command_ack() wrapper drops it.
                self._publish_ack(
                    f"command '{name}'",
                    lambda client: client.send_ack(
                        ack_id=msg.ack_id, message_type=msg.type, status=status, message_str=message, original_command=name
                    ),
                )

            ack = send_command_ack

        self._on_command(_Command(name=name, args=args, ack=ack))

    def _on_sdk_ota(self, msg: Any) -> None:  # noqa: ANN401
        request = OtaRequest(
            version=str(msg.version or ""),
            files=tuple(OtaFile(url=str(u.url), file_name=str(u.file_name)) for u in (msg.urls or [])),
            hardware_version=str(msg.hardware_version) if msg.hardware_version else None,
        )

        def send_ota_ack(status: int, message: str | None) -> None:
            self._publish_ack(
                "OTA request",
                lambda client: client.send_ack(ack_id=msg.ack_id, message_type=msg.type, status=status, message_str=message),
            )

        self._on_ota(request, send_ota_ack)

    def _on_sdk_disconnect(self, reason: str, from_server: bool) -> None:
        # paho also fires this for sockets that never reached CONNECTED (a rejected certificate, the
        # SDK's own connect timeout...). Only a session that was up counts as lost.
        if self._client is None or not self._session_up:
            logger.debug(f"MQTT disconnect during a connection attempt: {reason}")
            return
        self._session_up = False
        self._lost_at = time.monotonic()
        self._on_lost(f"connection lost ({reason}{', closed by the server' if from_server else ''})")


class _RelayBackend:
    """The board's iotc-relay service owns the cloud connection.
    Wire format: newline-delimited JSON over TCP (tcp://host:port) or a unix socket (a path)."""

    def __init__(self, endpoint: str, client_id: str, on_command: Callable[[_Command], None], on_lost: Callable[[str], None]) -> None:
        self._endpoint = endpoint
        self._client_id = client_id
        self._on_command = on_command
        self._on_lost = on_lost
        self._lock = threading.RLock()
        self._sock: socket.socket | None = None
        self._reader: threading.Thread | None = None
        self._last_tx = 0.0
        self._connected_at = 0.0
        self._next_attempt_at = 0.0
        self._backoff_s = _RECONNECT_MIN_S
        self._closing = False
        self._recent: dict[str, tuple[float, Any]] = {}  # values sent in the last relay window
        self._last_command: tuple[bytes, float] | None = None

    @property
    def description(self) -> str:
        return f"relay (endpoint {self._endpoint}, client id '{self._client_id}')"

    def is_connected(self) -> bool:
        return self._sock is not None

    def ensure_connected(self) -> bool:
        if self._sock is not None:
            self._keepalive()
            return self._sock is not None  # the keepalive may just have found the socket dead
        now = time.monotonic()
        if now < self._next_attempt_at:
            return False
        try:
            self._closing = False  # a brick restarted with App.start_brick() reports losses again
            sock = self._open()
            with self._lock:
                self._sock = sock
                self._last_tx = 0.0
                self._connected_at = time.monotonic()
                self._recent.clear()
            if not self._write({"type": "register", "client_id": self._client_id}):
                raise OSError("registration failed")
            self._reader = threading.Thread(target=self._reader_loop, args=(sock,), name="IoTConnect.relay-reader", daemon=True)
            self._reader.start()
        except OSError as e:
            logger.warning(f"Relay {self._endpoint} not reachable ({e}), next attempt in {self._backoff_s:.0f}s")
            self._next_attempt_at = time.monotonic() + self._backoff_s
            self._backoff_s = min(self._backoff_s * 2, _RECONNECT_MAX_S)
            return False
        # The backoff is only reset once a session proves stable (see _close), so an endpoint that
        # accepts and immediately drops connections cannot cause a reconnect storm.
        logger.info(f"Connected to the /IOTCONNECT relay at {self._endpoint} as '{self._client_id}'")
        return True

    def disconnect(self) -> None:
        self._closing = True
        self._close("stopped")
        reader = self._reader
        if reader is not None and reader is not threading.current_thread():
            reader.join(timeout=2.0)

    def send(self, values: dict[str, Any], timestamp: datetime | None) -> bool:
        if timestamp is not None:
            logger.debug("Telemetry timestamps are not supported in relay mode and were dropped")
        if self._sock is None:
            return False
        # The relay keeps only the LAST message per client and forwards it every 5 s, so two calls
        # with different keys inside one window would lose the first. Re-send the window's values.
        now = time.monotonic()
        with self._lock:
            self._recent = {k: v for k, v in self._recent.items() if now - v[0] < _RELAY_WINDOW_S}
            for k, v in values.items():
                self._recent[k] = (now, v)
            merged = {k: v[1] for k, v in self._recent.items()}
        return self._write({"type": "telemetry", "client_id": self._client_id, "data": merged})

    def _open(self) -> socket.socket:
        endpoint = self._endpoint
        if "/" not in endpoint and ":" in endpoint:
            endpoint = "tcp://" + endpoint  # a bare host:port is not a unix socket path
        if endpoint.startswith("tcp://"):
            target = endpoint[len("tcp://") :]
            if target.startswith("["):  # [ipv6]:port
                host, _, port_str = target[1:].partition("]")
                port_str = port_str.lstrip(":")
            else:
                host, _, port_str = target.rpartition(":")
            if not host or not port_str.isdigit():
                raise OSError(f"invalid relay endpoint '{endpoint}', expected tcp://host:port")
            sock = socket.create_connection((host, int(port_str)), timeout=_RELAY_CONNECT_TIMEOUT_S)
        else:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(_RELAY_CONNECT_TIMEOUT_S)
            sock.connect(endpoint)
        sock.settimeout(_RELAY_IO_TIMEOUT_S)
        return sock

    def _write(self, message: dict[str, Any]) -> bool:
        line = (json.dumps(message) + "\n").encode("utf-8")
        with self._lock:
            sock = self._sock
            if sock is None:
                return False
            try:
                sock.sendall(line)
                self._last_tx = time.monotonic()
                return True
            except OSError as e:
                self._close(f"send failed ({e})")
                return False

    def _keepalive(self) -> None:
        if time.monotonic() - self._last_tx < _RELAY_KEEPALIVE_S:
            return
        # The relay answers an unknown message type with an error line and keeps the connection,
        # which is exactly what a keepalive needs. Resending "register" would work too but logs on the relay.
        self._write({"type": "ping", "client_id": self._client_id})

    def _reader_loop(self, sock: socket.socket) -> None:
        buffer = b""
        try:
            while self._sock is sock:
                try:
                    chunk = sock.recv(4096)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    self._handle_line(line)
        finally:
            if self._sock is sock:
                self._close("relay closed the connection")

    def _handle_line(self, line: bytes) -> None:
        try:
            message = json.loads(line.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            logger.debug(f"Ignoring malformed relay message: {line!r}")
            return
        if not isinstance(message, dict):
            return
        if message.get("type") == "command":
            # The relay server keeps each connection under two keys and broadcasts to both, so every
            # command arrives twice back to back. Collapse an identical line that follows immediately.
            now = time.monotonic()
            previous, self._last_command = self._last_command, (line, now)
            if previous is not None and previous[0] == line and now - previous[1] < _RELAY_DUPLICATE_WINDOW_S:
                self._last_command = None  # a third identical line is a real repeat
                return
            name = str(message.get("command_name") or "")
            self._on_command(_Command(name=name, args=_parse_relay_args(message.get("parameters")), ack=None))
        elif message.get("status") == "error":
            logger.debug(f"Relay reported: {message.get('message')}")

    def _close(self, reason: str) -> None:
        with self._lock:
            sock, self._sock = self._sock, None
            session_s = time.monotonic() - self._connected_at
        if sock is None:
            return
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            sock.close()
        except OSError:
            pass
        if self._closing:
            return
        # Pace the reconnect: a session that stayed up resets the backoff, a short-lived one grows it.
        if session_s >= _RELAY_STABLE_SESSION_S:
            self._backoff_s = _RECONNECT_MIN_S
        self._next_attempt_at = time.monotonic() + self._backoff_s
        self._backoff_s = min(self._backoff_s * 2, _RECONNECT_MAX_S)
        self._on_lost(reason)


@brick
class IoTConnect:
    """Publishes telemetry to Avnet /IOTCONNECT and receives cloud-to-device commands (and OTA
    requests in direct mode). Instantiate it before ``App.run()``; the app framework starts and
    stops it. Everything is configurable through the brick's variables or the constructor.

    Args:
        mode: ``"auto"``, ``"direct"`` or ``"relay"``. Default: ``IOTC_MODE`` or ``"auto"``.
        credentials_dir: Folder holding ``iotcDeviceConfig.json``, ``device-cert.pem`` and
            ``device-pkey.pem`` (direct mode). Default: ``IOTC_CREDENTIALS_DIR`` or ``data/iotconnect``
            in the app folder. ``IOTC_DEVICE_CONFIG``, ``IOTC_DEVICE_CERT``, ``IOTC_DEVICE_KEY`` and
            ``IOTC_SERVER_CA_CERT`` override the individual paths.
        relay_endpoint: ``tcp://host:port`` or a unix socket path (relay mode). Default:
            ``IOTC_RELAY_ENDPOINT`` or ``tcp://172.17.0.1:8899``.
        client_id: Name this app registers with the relay. Default: ``IOTC_CLIENT_ID`` or the app
            folder name.
        send_interval: Seconds between telemetry transmissions. ``0`` (default, or
            ``IOTC_SEND_INTERVAL``) sends every call immediately. A positive value merges the
            values of all calls and sends one message per interval with the latest value of each
            field, which keeps high-rate sensors within the device template's data frequency.
    """

    def __init__(
        self,
        mode: str | None = None,
        credentials_dir: str | os.PathLike[str] | None = None,
        relay_endpoint: str | None = None,
        client_id: str | None = None,
        send_interval: float | None = None,
    ) -> None:
        requested = (mode or _env("IOTC_MODE", MODE_AUTO)).lower()
        if requested not in _MODES:
            raise ValueError(f"IoTConnect mode must be one of {_MODES}, got '{requested}'")

        base = Path(credentials_dir) if credentials_dir is not None else Path(_env("IOTC_CREDENTIALS_DIR") or _default_credentials_dir())
        config_path = Path(_env("IOTC_DEVICE_CONFIG") or base / CONFIG_FILE)
        cert_path = Path(_env("IOTC_DEVICE_CERT") or base / CERT_FILE)
        key_path = Path(_env("IOTC_DEVICE_KEY") or base / KEY_FILE)
        server_ca = _env("IOTC_SERVER_CA_CERT")
        if server_ca.lower() == "system":
            server_ca = ""  # the brick variable's default: the system trust store
        server_ca_path = Path(server_ca) if server_ca else None

        self._relay_endpoint = relay_endpoint or _env("IOTC_RELAY_ENDPOINT", DEFAULT_RELAY_ENDPOINT)
        env_client_id = _env("IOTC_CLIENT_ID")
        if env_client_id.lower() == "auto":
            env_client_id = ""  # the brick variable's default: derive it from the app folder
        self._client_id = client_id or env_client_id or _default_client_id()

        if send_interval is None:
            try:
                send_interval = float(_env("IOTC_SEND_INTERVAL", "0"))
            except ValueError:
                logger.warning("IOTC_SEND_INTERVAL is not a number, sending immediately")
                send_interval = 0.0
        self._send_interval = max(0.0, float(send_interval))

        have_credentials = config_path.is_file() and cert_path.is_file() and key_path.is_file()
        if requested == MODE_AUTO:
            self._mode = MODE_DIRECT if have_credentials else MODE_RELAY
        else:
            self._mode = requested

        self._handlers: dict[str, CommandHandler] = {}
        self._any_handler: AnyCommandHandler | None = None
        self._ota_handler: OtaHandler | None = None
        self._connect_callbacks: list[Callable[[], Any]] = []
        self._disconnect_callbacks: list[Callable[[str], Any]] = []
        self._commands: queue.Queue[_Command] = queue.Queue()
        self._pending: dict[str, Any] = {}
        self._pending_timestamp: datetime | None = None
        self._pending_lock = threading.Lock()
        self._last_flush = 0.0
        self._running = False
        self._was_connected = False

        if self._mode == MODE_DIRECT:
            self._backend: _DirectBackend | _RelayBackend = _DirectBackend(
                config_path, cert_path, key_path, server_ca_path, self._enqueue_command, self._handle_ota, self._lost
            )
        else:
            self._backend = _RelayBackend(self._relay_endpoint, self._client_id, self._enqueue_command, self._lost)

    # --- public API ---

    @property
    def mode(self) -> str:
        """The effective mode: ``"direct"`` or ``"relay"``."""
        return self._mode

    def is_connected(self) -> bool:
        """True while the cloud (direct) or the relay service (relay) is reachable."""
        return self._backend.is_connected()

    def send_telemetry(self, values: Mapping[str, Any], timestamp: datetime | None = None) -> bool:
        """Sends one telemetry record. Keys must match the device template's attributes; unknown
        attributes are silently dropped by /IOTCONNECT.

        Returns True when the record was handed to the cloud/relay (or queued, when a send
        interval is set), False when offline. The brick connects once ``App.run()`` has started
        it, so calls made before that return False.

        ``timestamp`` is honoured in direct mode only: an aware datetime is converted to UTC, a
        naive one is taken as UTC. With a send interval the merged record carries the timestamp
        of the last call (None = server time).
        """
        if not isinstance(values, Mapping):
            raise TypeError("send_telemetry() expects a dict of attribute name -> value")
        data = {str(k): _jsonable(v) for k, v in values.items()}
        if not data:
            return False
        if timestamp is not None and timestamp.tzinfo is not None:
            timestamp = timestamp.astimezone(timezone.utc)  # the SDK formats the wall clock and appends "Z"
        if self._send_interval > 0:
            with self._pending_lock:
                self._pending.update(data)
                self._pending_timestamp = timestamp
            return True
        sent = self._backend.send(data, timestamp)
        if sent:
            logger.debug(f"Sent {data}")
        return sent

    def on_command(self, name: str | AnyCommandHandler, handler: CommandHandler | None = None) -> None:
        """Registers a command handler.

        ``on_command("set-led", fn)`` routes the ``set-led`` command to ``fn(args)``.
        ``on_command(fn)`` registers a catch-all ``fn(name, args)`` for commands without a named handler.
        In direct mode the handler's outcome is acknowledged to the cloud: return False or raise
        to report failure, return a string to attach a message to the success ack.
        """
        if callable(name) and handler is None:
            self._any_handler = name
            return
        if not isinstance(name, str) or not name:
            raise TypeError("on_command() expects a command name and a handler, or a single catch-all handler")
        if not callable(handler):
            raise TypeError(f"handler for command '{name}' must be callable")
        self._handlers[name] = handler

    def command(self, name: str) -> Callable[[CommandHandler], CommandHandler]:
        """Decorator form of :meth:`on_command`: ``@iotc.command("set-led")``."""

        def register(fn: CommandHandler) -> CommandHandler:
            self.on_command(name, fn)
            return fn

        return register

    def on_ota(self, handler: OtaHandler) -> None:
        """Registers the OTA handler (direct mode). It receives an :class:`OtaRequest`; download and
        install the files and return True once the new version is running. Without a handler OTA
        requests are rejected with a failure ack."""
        if not callable(handler):
            raise TypeError("OTA handler must be callable")
        self._ota_handler = handler

    def on_connect(self, fn: Callable[[], Any]) -> None:
        """Calls ``fn()`` each time the cloud/relay connection is (re)established."""
        self._connect_callbacks.append(fn)

    def on_disconnect(self, fn: Callable[[str], Any]) -> None:
        """Calls ``fn(reason)`` each time the cloud/relay connection is lost."""
        self._disconnect_callbacks.append(fn)

    # --- lifecycle, driven by the app framework ---

    def start(self) -> None:
        self._running = True
        self._was_connected = False
        logger.info(f"Mode: {self._backend.description}")
        if isinstance(self._backend, _DirectBackend):
            missing = self._backend.missing_files()
            if missing:
                logger.error(
                    "Direct mode needs these files: "
                    + ", ".join(str(p) for p in missing)
                    + ". Copy them from the board's /opt/demo folder or set IOTC_MODE=relay."
                )
        if self._send_interval > 0:
            logger.info(f"Telemetry is merged and sent every {self._send_interval:g}s")

    def stop(self) -> None:
        self._running = False
        self._backend.disconnect()
        self._was_connected = False

    def loop(self) -> None:
        """Keeps the connection up and flushes batched telemetry. Runs in its own thread."""
        if not self._running:
            time.sleep(_LOOP_TICK_S)
            return
        connected = self._backend.ensure_connected()
        if connected and not self._was_connected:
            self._was_connected = True
            self._fire(self._connect_callbacks)
        elif not connected and self._was_connected:
            self._was_connected = False  # the backend already reported the loss through _lost()
        if connected:
            self._flush_pending()
        time.sleep(_LOOP_TICK_S)

    @brick.loop
    def _dispatch_commands(self) -> None:
        """Runs command handlers one at a time, off the network threads."""
        try:
            command = self._commands.get(timeout=_LOOP_TICK_S)
        except queue.Empty:
            return
        self._run_command(command)

    # --- internals ---

    def _enqueue_command(self, command: _Command) -> None:
        self._commands.put(command)

    def _run_command(self, command: _Command) -> None:
        handler = self._handlers.get(command.name)
        try:
            if handler is not None:
                logger.info(f"Command '{command.name}' {command.args}")
                result = handler(command.args)
            elif self._any_handler is not None:
                logger.info(f"Command '{command.name}' {command.args} (catch-all handler)")
                result = self._any_handler(command.name, command.args)
            else:
                if self._mode == MODE_RELAY:
                    # the relay broadcasts every command to every app, so this is normal
                    logger.info(f"Ignoring command '{command.name}' (no handler)")
                else:
                    logger.warning(f"No handler for command '{command.name}'")
                self._ack(command, False, f"No handler for command '{command.name}'")
                return
        except Exception as e:
            logger.exception(f"Command '{command.name}' failed: {e}")
            self._ack(command, False, f"{type(e).__name__}: {e}")
            return
        if result is False:
            self._ack(command, False, None)
        elif isinstance(result, str):
            self._ack(command, True, result)
        else:
            self._ack(command, True, None)

    @staticmethod
    def _ack(command: _Command, success: bool, message: str | None) -> None:
        if command.ack is not None:
            command.ack(success, message)

    def _handle_ota(self, request: OtaRequest, ack: _OtaAckFn) -> None:
        from avnet.iotconnect.sdk.lite import C2dAck

        handler = self._ota_handler
        if handler is None:
            logger.warning(f"OTA request for version '{request.version}' rejected: this app has no OTA handler")
            ack(C2dAck.OTA_FAILED, "This app has no OTA handler")
            return

        def run() -> None:
            logger.info(f"OTA request for version '{request.version}' with {len(request.files)} file(s)")
            ack(C2dAck.OTA_DOWNLOADING, None)
            try:
                result = handler(request)
            except Exception as e:
                logger.exception(f"OTA handler failed: {e}")
                ack(C2dAck.OTA_DOWNLOAD_FAILED, f"{type(e).__name__}: {e}")
                return
            if result is False:
                ack(C2dAck.OTA_DOWNLOAD_FAILED, "OTA handler reported failure")
            else:
                ack(C2dAck.OTA_DOWNLOAD_DONE, result if isinstance(result, str) else None)

        threading.Thread(target=run, name="IoTConnect.ota", daemon=True).start()

    def _flush_pending(self) -> None:
        now = time.monotonic()
        if now - self._last_flush < self._send_interval:
            return
        with self._pending_lock:
            if not self._pending:
                return
            data, self._pending = self._pending, {}
            timestamp, self._pending_timestamp = self._pending_timestamp, None
        if self._backend.send(data, timestamp):
            self._last_flush = now
            logger.debug(f"Sent {data}")
        else:
            with self._pending_lock:  # keep the snapshot for the next tick, newer values win
                self._pending = {**data, **self._pending}
                self._pending_timestamp = self._pending_timestamp or timestamp

    def _lost(self, reason: str) -> None:
        logger.warning(f"Disconnected: {reason}")
        self._was_connected = False
        for fn in list(self._disconnect_callbacks):
            try:
                fn(reason)
            except Exception as e:
                logger.exception(f"on_disconnect callback failed: {e}")

    @staticmethod
    def _fire(callbacks: list[Callable[[], Any]]) -> None:
        for fn in list(callbacks):
            try:
                fn()
            except Exception as e:
                logger.exception(f"on_connect callback failed: {e}")


# The workshop relay client's API on top of the brick (see compat.py); imported last to avoid a cycle.
from .compat import IoTConnectRelayClient  # noqa: E402, F401
