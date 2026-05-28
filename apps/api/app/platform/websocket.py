from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs
from uuid import uuid4

from flask import request

from app.platform.errors import PlatformError


def build_room_snapshot_message(room: dict[str, Any], game: dict[str, Any]) -> dict[str, Any]:
    return {"type": "room_snapshot", "room": room, "game": game}


def build_error_message(code: str, message: str) -> dict[str, str]:
    return {"type": "error", "code": code, "message": message}


class ConnectionHub:
    def __init__(self) -> None:
        self._rooms: dict[str, dict[str, Any]] = {}

    def add(self, room_code: str, connection_id: str, websocket: Any) -> None:
        self._rooms.setdefault(room_code, {})[connection_id] = websocket

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
        for connection_id, websocket in list(room_connections.items()):
            try:
                websocket.send(payload)
            except Exception:
                stale_connection_ids.append(connection_id)

        for connection_id in stale_connection_ids:
            self.remove(room_code, connection_id)


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


def _decode_client_message(raw_message: Any) -> dict[str, Any] | None:
    try:
        message = json.loads(raw_message)
    except (TypeError, json.JSONDecodeError):
        return None

    if not isinstance(message, dict):
        return None
    return message


def _is_game_action_message(message: dict[str, Any]) -> bool:
    return message.get("type") == "game_action" and isinstance(message.get("action"), dict)


def register_websocket_routes(sock: Any, room_manager: Any) -> ConnectionHub:
    hub = ConnectionHub()

    @sock.route("/ws/rooms/<room_code>")
    def room_socket(websocket: Any, room_code: str) -> None:
        connection_id = uuid4().hex
        player_id: str | None = None
        connected = False

        try:
            player_id, session_token = _read_connection_credentials(request.query_string)
            room_manager.reconnect(room_code, player_id, session_token, connection_id)
            hub.add(room_code, connection_id, websocket)
            connected = True

            snapshot = room_manager.get_snapshot(room_code, player_id)
            hub.broadcast(
                room_code,
                build_room_snapshot_message(snapshot["room"], snapshot["game"]),
            )

            while True:
                raw_message = websocket.receive()
                if raw_message is None:
                    break

                message = _decode_client_message(raw_message)
                if message is None:
                    _send_error(websocket, "invalid_json", "Message must be valid JSON.")
                    continue

                if not _is_game_action_message(message):
                    _send_error(
                        websocket,
                        "invalid_message",
                        'Message must be {"type": "game_action", "action": {...}}.',
                    )
                    continue

                try:
                    result = room_manager.handle_action(room_code, player_id, message["action"])
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

                snapshot = room_manager.get_snapshot(room_code, player_id)
                hub.broadcast(
                    room_code,
                    build_room_snapshot_message(snapshot["room"], snapshot["game"]),
                )
        except PlatformError as error:
            _send_error(websocket, error.code, error.message)
        finally:
            if connected:
                hub.remove(room_code, connection_id)
            if player_id is not None:
                try:
                    room_manager.mark_disconnected(room_code, player_id)
                except PlatformError:
                    pass

    return hub
