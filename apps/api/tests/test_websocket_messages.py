import json

from app.platform.websocket import (
    ConnectionHub,
    build_error_message,
    build_room_snapshot_message,
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
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.sent: list[str] = []

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
