import json

from flask import Flask

from app.platform.errors import PlatformError
from app.platform.websocket import (
    ConnectionHub,
    build_error_message,
    build_room_snapshot_message,
    decode_client_message,
    register_websocket_routes,
)


def test_build_room_snapshot_message_wraps_room_and_game():
    room = {"roomCode": "123456", "players": []}
    game = {"message": "hello"}

    assert build_room_snapshot_message(room, game) == {
        "type": "room_snapshot",
        "room": room,
        "game": game,
    }


def test_build_error_message_wraps_code_and_message():
    assert build_error_message("invalid_json", "Message must be JSON.") == {
        "type": "error",
        "code": "invalid_json",
        "message": "Message must be JSON.",
    }


class FakeWebSocket:
    def __init__(self, messages: list[str] | None = None, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.messages = messages or []
        self.sent: list[str] = []

    def receive(self) -> str | None:
        if not self.messages:
            return None
        return self.messages.pop(0)

    def send(self, payload: str) -> None:
        if self.should_fail:
            raise RuntimeError("stale connection")
        self.sent.append(payload)


def test_connection_hub_broadcasts_json_to_room_connections_and_removes_failures():
    hub = ConnectionHub()
    live = FakeWebSocket()
    stale = FakeWebSocket(should_fail=True)
    other_room = FakeWebSocket()
    message = {"type": "room_snapshot", "room": {"roomCode": "123456"}, "game": {}}

    hub.add("123456", "conn-live", live)
    hub.add("123456", "conn-stale", stale)
    hub.add("654321", "conn-other", other_room)

    hub.broadcast("123456", message)

    assert live.sent == [json.dumps(message)]
    assert stale.sent == []
    assert other_room.sent == []

    follow_up = {"type": "error", "code": "x", "message": "y"}
    hub.broadcast("123456", follow_up)

    assert live.sent == [json.dumps(message), json.dumps(follow_up)]


def test_decode_client_message_distinguishes_invalid_json_from_invalid_message():
    assert decode_client_message("not json") == (None, "invalid_json")
    assert decode_client_message("[]") == (None, "invalid_message")
    assert decode_client_message("{}") == (None, "invalid_message")


def test_decode_client_message_returns_game_action():
    action = {"type": "set_message", "payload": {"message": "x"}}

    assert decode_client_message(json.dumps({"type": "game_action", "action": action})) == (
        action,
        None,
    )


class FakeSock:
    def __init__(self) -> None:
        self.routes: dict[str, object] = {}

    def route(self, path: str):
        def register(handler):
            self.routes[path] = handler
            return handler

        return register


class ReconnectFailingRoomManager:
    def __init__(self) -> None:
        self.disconnected_players: list[tuple[str, str]] = []

    def reconnect(
        self,
        room_code: str,
        player_id: str,
        session_token: str,
        connection_id: str | None = None,
    ) -> None:
        raise PlatformError("invalid_session", "Invalid session token.", 401)

    def mark_disconnected(self, room_code: str, player_id: str) -> None:
        self.disconnected_players.append((room_code, player_id))


def test_reconnect_failure_does_not_mark_player_disconnected():
    app = Flask(__name__)
    sock = FakeSock()
    room_manager = ReconnectFailingRoomManager()
    register_websocket_routes(sock, room_manager)
    handler = sock.routes["/ws/rooms/<room_code>"]
    websocket = FakeWebSocket()

    with app.test_request_context("/ws/rooms/123456?playerId=p1&sessionToken=bad"):
        handler(websocket, "123456")

    assert room_manager.disconnected_players == []
    assert json.loads(websocket.sent[0])["code"] == "invalid_session"
