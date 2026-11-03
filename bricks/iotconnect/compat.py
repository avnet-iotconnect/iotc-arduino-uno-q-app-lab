# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Avnet
"""Drop-in replacement for the workshop's ``iotc_relay_client.IoTConnectRelayClient``.

``scripts/add_iotconnect_brick.sh`` writes a shim ``python/iotc_relay_client.py`` into an app whose code imports
the relay client, so ``from iotc_relay_client import IoTConnectRelayClient`` keeps working unchanged while the
brick does the work, in relay or direct mode according to the brick's variables.

Differences from the classic client:

* ``start()`` does not open a connection itself. The app framework starts the brick when ``App.run()`` runs, so
  telemetry sent before that returns False (the classic client returned False while disconnected, too).
* ``command_callback(command_name, parameters)`` keeps its signature. ``parameters`` is the space-joined
  parameter string, exactly as the relay delivers it; in direct mode the cloud's parameter list is re-joined
  with single spaces.
* The brick's relay fixes apply: a command repeated by the relay is delivered once, and telemetry sent within
  the relay's 5 s window is merged instead of lost.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from . import IoTConnect, logger

CommandCallback = Callable[[str, str], Any]


class IoTConnectRelayClient:
    """The classic relay client's API, backed by the /IOTCONNECT brick.

    Args:
        socket_path: ``tcp://host:port`` or a unix socket path. Overrides the brick's ``IOTC_RELAY_ENDPOINT``.
        client_id: Name registered with the relay. Overrides the brick's ``IOTC_CLIENT_ID``.
        command_callback: ``fn(command_name, parameters)``; may also be assigned later, as the examples do.
        reconnect_delay: Kept for compatibility; the brick paces its own reconnects.
    """

    def __init__(
        self,
        socket_path: str | None = None,
        client_id: str | None = None,
        command_callback: CommandCallback | None = None,
        reconnect_delay: float = 5,
        **_ignored: Any,
    ) -> None:
        self.socket_path = socket_path
        self.client_id = client_id
        self.command_callback = command_callback
        self.reconnect_delay = reconnect_delay
        self.running = False
        self.iotc = IoTConnect(relay_endpoint=socket_path or None, client_id=client_id or None)
        self.iotc.on_command(self._dispatch)

    # --- classic API -------------------------------------------------------------------------

    def start(self) -> None:
        """No connection is opened here: the brick connects once ``App.run()`` has started it."""
        self.running = True
        logger.info(f"Relay-client API served by the /IOTCONNECT brick ({self.iotc.mode} mode)")

    def stop(self) -> None:
        self.running = False  # the app framework stops the brick

    def connect(self) -> bool:
        return self.iotc.is_connected()

    def disconnect(self) -> None:
        pass

    @property
    def connected(self) -> bool:
        return self.iotc.is_connected()

    def is_connected(self) -> bool:
        return self.iotc.is_connected()

    def send_telemetry(self, data: Mapping[str, Any]) -> bool:
        """Returns True when the record was handed to the relay/cloud, False while offline."""
        if not isinstance(data, Mapping):
            logger.warning(f"send_telemetry() ignored a non-dict payload: {type(data).__name__}")
            return False
        return self.iotc.send_telemetry(data)

    # --- plumbing ----------------------------------------------------------------------------

    def _dispatch(self, command_name: str, args: list[str]) -> None:
        callback = self.command_callback
        if callback is None:
            logger.info(f"Command '{command_name}' ignored: no command_callback set")
            return
        callback(command_name, " ".join(args))  # the return value is not an ack, as in the classic client
