from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
from urllib.parse import parse_qs
from uuid import uuid4

from flask import request

from app.platform.errors import PlatformError

DEFAULT_PLAYER_ONLINE_TIMEOUT_SECONDS = 30


def build_room_snapshot_message(room: dict[str, Any], game: dict[str, Any]) -> dict[str, Any]:
    return {"type": "room_snapshot", "room": room, "game": game}


def build_error_message(code: str, message: str) -> dict[str, str]:
    return {"type": "error", "code": code, "message": message}


@dataclass(frozen=True)
class RoomConnection:
    websocket: Any
    player_id: str


@dataclass(frozen=True)
class ClientMessage:
    type: str
    action: dict[str, Any] | None = None


class ConnectionHub:
    def __init__(self) -> None:
        self._rooms: dict[str, dict[str, RoomConnection]] = {}

    def add(self, room_code: str, connection_id: str, websocket: Any, player_id: str) -> None:
        self._rooms.setdefault(room_code, {})[connection_id] = RoomConnection(
            websocket=websocket,
            player_id=player_id,
        )

    def remove(self, room_code: str, connection_id: str) -> None:
        room_connections = self._rooms.get(room_code)
        if room_connections is None:
            return

        room_connections.pop(connection_id, None)
        if not room_connections:
            self._rooms.pop(room_code, None)

    def broadcast(self, room_code: str, message: dict[str, Any]) -> None:
        room_connections = self._rooms.get(room_code)
        if not room_connections:
            return

        payload = json.dumps(message)
        stale_connection_ids: list[str] = []
        for connection_id, connection in list(room_connections.items()):
            try:
                connection.websocket.send(payload)
            except Exception:
                stale_connection_ids.append(connection_id)

        for connection_id in stale_connection_ids:
            self.remove(room_code, connection_id)

    def broadcast_snapshots(self, room_code: str, room_manager: Any) -> None:
        room_connections = self._rooms.get(room_code)
        if not room_connections:
            return

        stale_connection_ids: list[str] = []
        for connection_id, connection in list(room_connections.items()):
            try:
                snapshot = room_manager.get_snapshot(room_code, connection.player_id)
            except PlatformError:
                stale_connection_ids.append(connection_id)
                continue

            try:
                connection.websocket.send(
                    json.dumps(build_room_snapshot_message(snapshot["room"], snapshot["game"]))
                )
            except Exception:
                stale_connection_ids.append(connection_id)

        for connection_id in stale_connection_ids:
            self.remove(room_code, connection_id)


def broadcast_player_timeout_snapshots(
    hub: ConnectionHub,
    room_manager: Any,
    timeout_seconds: int = DEFAULT_PLAYER_ONLINE_TIMEOUT_SECONDS,
) -> list[str]:
    changed_room_codes = room_manager.mark_inactive_connected_players_disconnected(
        timeout_seconds=timeout_seconds,
    )
    for changed_room_code in changed_room_codes:
        hub.broadcast_snapshots(changed_room_code, room_manager)
    return changed_room_codes


def _send_error(websocket: Any, code: str, message: str) -> None:
    websocket.send(json.dumps(build_error_message(code, message)))


def _read_connection_credentials(query_string: bytes | str) -> tuple[str, str]:
    if isinstance(query_string, bytes):
        query_string = query_string.decode("utf-8", errors="replace")

    query = parse_qs(query_string, keep_blank_values=True)
    player_id = query.get("playerId", [""])[0]
    session_token = query.get("sessionToken", [""])[0]
    if not player_id or not session_token:
        raise PlatformError(
            "invalid_session",
            "playerId and sessionToken are required.",
            401,
        )
    return player_id, session_token


def decode_client_message(raw_message: Any) -> tuple[ClientMessage | None, str | None]:
    try:
        message = json.loads(raw_message)
    except (TypeError, json.JSONDecodeError):
        return None, "invalid_json"

    if not isinstance(message, dict):
        return None, "invalid_message"
    if _is_heartbeat_message(message):
        return ClientMessage(type="heartbeat"), None
    if _is_game_action_message(message):
        return ClientMessage(type="game_action", action=message["action"]), None
    else:
        return None, "invalid_message"


def _is_game_action_message(message: dict[str, Any]) -> bool:
    return message.get("type") == "game_action" and isinstance(message.get("action"), dict)


def _is_heartbeat_message(message: dict[str, Any]) -> bool:
    return message.get("type") == "heartbeat"


def register_websocket_routes(
    sock: Any,
    room_manager: Any,
    player_timeout_seconds: int = DEFAULT_PLAYER_ONLINE_TIMEOUT_SECONDS,
) -> ConnectionHub:
    hub = ConnectionHub()

    @sock.route("/ws/rooms/<room_code>")
    def room_socket(websocket: Any, room_code: str) -> None:
        connection_id = uuid4().hex
        player_id: str | None = None
        connected_player_id: str | None = None

        try:
            player_id, session_token = _read_connection_credentials(request.query_string)
            room_manager.reconnect(room_code, player_id, session_token, connection_id)
            hub.add(room_code, connection_id, websocket, player_id)
            connected_player_id = player_id

            hub.broadcast_snapshots(room_code, room_manager)

            while True:
                raw_message = websocket.receive()
                if raw_message is None:
                    break

                client_message, error_code = decode_client_message(raw_message)
                if error_code == "invalid_json":
                    _send_error(websocket, "invalid_json", "Message must be valid JSON.")
                    continue
                if error_code == "invalid_message":
                    _send_error(
                        websocket,
                        "invalid_message",
                        'Message must be {"type": "heartbeat"} or {"type": "game_action", "action": {...}}.',
                    )
                    continue

                if client_message is not None and client_message.type == "heartbeat":
                    try:
                        room_manager.record_heartbeat(room_code, player_id, connection_id)
                        broadcast_player_timeout_snapshots(
                            hub,
                            room_manager,
                            timeout_seconds=player_timeout_seconds,
                        )
                    except PlatformError as error:
                        _send_error(websocket, error.code, error.message)
                    continue

                if client_message is None or client_message.action is None:
                    _send_error(websocket, "invalid_message", "Message action is required.")
                    continue

                try:
                    result = room_manager.handle_action(
                        room_code,
                        player_id,
                        client_message.action,
                        connection_id,
                    )
                except PlatformError as error:
                    _send_error(websocket, error.code, error.message)
                    continue

                if result.get("status") == "rejected":
                    _send_error(
                        websocket,
                        result.get("errorCode") or "action_rejected",
                        "Action was rejected.",
                    )
                    continue

                hub.broadcast_snapshots(room_code, room_manager)
        except PlatformError as error:
            _send_error(websocket, error.code, error.message)
        finally:
            if connected_player_id is not None:
                hub.remove(room_code, connection_id)
                try:
                    disconnected_player = room_manager.mark_disconnected(
                        room_code,
                        connected_player_id,
                        connection_id,
                    )
                    if disconnected_player is not None:
                        hub.broadcast_snapshots(room_code, room_manager)
                except PlatformError:
                    pass

    return hub
