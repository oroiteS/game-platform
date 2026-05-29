import json

from flask import Flask

from app.platform import websocket as websocket_module
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

    hub.add("123456", "conn-live", live, "p1")
    hub.add("123456", "conn-stale", stale, "p2")
    hub.add("654321", "conn-other", other_room, "p3")

    hub.broadcast("123456", message)

    assert live.sent == [json.dumps(message)]
    assert stale.sent == []
    assert other_room.sent == []

    follow_up = {"type": "error", "code": "x", "message": "y"}
    hub.broadcast("123456", follow_up)

    assert live.sent == [json.dumps(message), json.dumps(follow_up)]


class ViewerSnapshotRoomManager:
    def get_snapshot(self, room_code: str, player_id: str) -> dict[str, object]:
        return {
            "room": {"roomCode": room_code},
            "game": {"viewer": player_id, "privateHand": [f"{player_id}-card"]},
        }


def test_connection_hub_broadcast_snapshots_uses_each_connection_player_id():
    hub = ConnectionHub()
    player_one = FakeWebSocket()
    player_two = FakeWebSocket()
    other_room = FakeWebSocket()
    room_manager = ViewerSnapshotRoomManager()

    hub.add("123456", "conn-p1", player_one, "p1")
    hub.add("123456", "conn-p2", player_two, "p2")
    hub.add("654321", "conn-other", other_room, "p3")

    hub.broadcast_snapshots("123456", room_manager)

    assert json.loads(player_one.sent[0])["game"] == {
        "viewer": "p1",
        "privateHand": ["p1-card"],
    }
    assert json.loads(player_two.sent[0])["game"] == {
        "viewer": "p2",
        "privateHand": ["p2-card"],
    }
    assert other_room.sent == []


def test_decode_client_message_distinguishes_invalid_json_from_invalid_message():
    assert decode_client_message("not json") == (None, "invalid_json")
    assert decode_client_message("[]") == (None, "invalid_message")
    assert decode_client_message("{}") == (None, "invalid_message")


def test_decode_client_message_returns_game_action():
    action = {"type": "set_message", "payload": {"message": "x"}}
    client_message, error_code = decode_client_message(
        json.dumps({"type": "game_action", "action": action})
    )

    assert error_code is None
    assert getattr(client_message, "type", None) == "game_action"
    assert getattr(client_message, "action", None) == action


def test_decode_client_message_returns_heartbeat():
    client_message, error_code = decode_client_message(json.dumps({"type": "heartbeat"}))

    assert error_code is None
    assert getattr(client_message, "type", None) == "heartbeat"
    assert getattr(client_message, "action", None) is None


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


class DisconnectBroadcastRoomManager:
    def __init__(self) -> None:
        self.marked_disconnected: list[tuple[str, str, str | None]] = []
        self.connected = True

    def reconnect(
        self,
        room_code: str,
        player_id: str,
        session_token: str,
        connection_id: str | None = None,
    ) -> None:
        self.connected = True

    def get_snapshot(self, room_code: str, player_id: str) -> dict[str, object]:
        return {
            "room": {
                "roomCode": room_code,
                "players": [{"playerId": "p1", "connected": self.connected}],
            },
            "game": {"viewer": player_id},
        }

    def mark_disconnected(
        self,
        room_code: str,
        player_id: str,
        connection_id: str | None = None,
    ) -> object | None:
        self.marked_disconnected.append((room_code, player_id, connection_id))
        self.connected = False
        return object()


def test_websocket_disconnect_broadcasts_disconnected_snapshot():
    app = Flask(__name__)
    sock = FakeSock()
    room_manager = DisconnectBroadcastRoomManager()
    hub = register_websocket_routes(sock, room_manager)
    handler = sock.routes["/ws/rooms/<room_code>"]
    websocket = FakeWebSocket()
    other_websocket = FakeWebSocket()
    hub.add("123456", "conn-other", other_websocket, "p2")

    with app.test_request_context("/ws/rooms/123456?playerId=p1&sessionToken=token"):
        handler(websocket, "123456")

    assert len(room_manager.marked_disconnected) == 1
    room_code, player_id, connection_id = room_manager.marked_disconnected[0]
    assert room_code == "123456"
    assert player_id == "p1"
    assert isinstance(connection_id, str)
    snapshots = [json.loads(payload) for payload in other_websocket.sent]
    assert snapshots[-1] == {
        "type": "room_snapshot",
        "room": {
            "roomCode": "123456",
            "players": [{"playerId": "p1", "connected": False}],
        },
        "game": {"viewer": "p2"},
    }


class HeartbeatRoomManager:
    def __init__(self) -> None:
        self.heartbeats: list[tuple[str, str]] = []

    def reconnect(
        self,
        room_code: str,
        player_id: str,
        session_token: str,
        connection_id: str | None = None,
    ) -> None:
        pass

    def get_snapshot(self, room_code: str, player_id: str) -> dict[str, object]:
        return {
            "room": {"roomCode": room_code, "players": [{"playerId": player_id}]},
            "game": {"viewer": player_id},
        }

    def record_heartbeat(
        self,
        room_code: str,
        player_id: str,
        connection_id: str | None = None,
    ) -> None:
        self.heartbeats.append((room_code, player_id))

    def handle_action(self, room_code: str, player_id: str, action: dict[str, object]) -> None:
        raise AssertionError("heartbeat must not be handled as a game action")

    def mark_inactive_connected_players_disconnected(self, timeout_seconds: int) -> list[str]:
        return []

    def mark_disconnected(
        self,
        room_code: str,
        player_id: str,
        connection_id: str | None = None,
    ) -> None:
        pass


def test_websocket_heartbeat_updates_last_seen_without_broadcasting_snapshot():
    app = Flask(__name__)
    sock = FakeSock()
    room_manager = HeartbeatRoomManager()
    register_websocket_routes(sock, room_manager)
    handler = sock.routes["/ws/rooms/<room_code>"]
    websocket = FakeWebSocket([json.dumps({"type": "heartbeat"})])

    with app.test_request_context("/ws/rooms/123456?playerId=p1&sessionToken=token"):
        handler(websocket, "123456")

    assert room_manager.heartbeats == [("123456", "p1")]
    assert len(websocket.sent) == 1
    assert json.loads(websocket.sent[0])["type"] == "room_snapshot"


class TimeoutBroadcastRoomManager:
    def __init__(self) -> None:
        self.timeout_checks: list[int] = []

    def mark_inactive_connected_players_disconnected(self, timeout_seconds: int) -> list[str]:
        self.timeout_checks.append(timeout_seconds)
        return ["123456"]

    def get_snapshot(self, room_code: str, player_id: str) -> dict[str, object]:
        return {
            "room": {"roomCode": room_code, "players": [{"playerId": "p1", "connected": False}]},
            "game": {"viewer": player_id},
        }


def test_broadcast_player_timeout_snapshots_broadcasts_changed_rooms():
    hub = ConnectionHub()
    websocket = FakeWebSocket()
    room_manager = TimeoutBroadcastRoomManager()
    hub.add("123456", "conn-p2", websocket, "p2")
    broadcast_player_timeout_snapshots = getattr(
        websocket_module,
        "broadcast_player_timeout_snapshots",
        None,
    )

    assert callable(broadcast_player_timeout_snapshots)

    changed_room_codes = broadcast_player_timeout_snapshots(
        hub,
        room_manager,
        timeout_seconds=30,
    )

    assert changed_room_codes == ["123456"]
    assert room_manager.timeout_checks == [30]
    assert json.loads(websocket.sent[-1]) == {
        "type": "room_snapshot",
        "room": {"roomCode": "123456", "players": [{"playerId": "p1", "connected": False}]},
        "game": {"viewer": "p2"},
    }
