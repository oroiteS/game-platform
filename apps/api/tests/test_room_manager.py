from datetime import datetime, timedelta, timezone

import pytest

from app.platform.errors import PlatformError
from app.platform.services.room_manager import RoomManager


def test_room_manager_accepts_explicit_storage():
    from app.platform.services.room_storage import InMemoryRoomStorage

    storage = InMemoryRoomStorage()
    manager = RoomManager(storage=storage)

    result = manager.create_room("lobby-demo", "Ada", 3)

    assert storage.get_room(result.room.room_code) is result.room


def test_create_room_generates_code_saves_capacity_and_returns_join_result():
    manager = RoomManager()

    result = manager.create_room("lobby-demo", "Ada", 3)

    assert len(result.room.room_code) == 6
    assert result.room.room_code.isdigit()
    assert result.room.capacity == 3
    assert result.player.nickname == "Ada"
    assert result.session_token
    assert result.room.players == [result.player]


def test_join_room_limits_by_requested_capacity():
    manager = RoomManager()
    result = manager.create_room("lobby-demo", "Ada", 3)
    room_code = result.room.room_code

    manager.join_room(room_code, "Bob")
    manager.join_room(room_code, "Cy")

    with pytest.raises(PlatformError) as error:
        manager.join_room(room_code, "Dee")

    assert error.value.code == "room_full"
    assert error.value.status_code == 409


def test_platform_room_capacity_is_30():
    assert RoomManager().platform_room_capacity == 30


def test_create_room_rejects_capacity_above_platform_limit():
    manager = RoomManager()

    with pytest.raises(PlatformError) as error:
        manager.create_room("lobby-demo", "Ada", 31)

    assert error.value.code == "invalid_capacity"
    assert error.value.status_code == 400


@pytest.mark.parametrize("requested_capacity", [True, False, "3"])
def test_create_room_rejects_non_integer_capacity_types(requested_capacity):
    manager = RoomManager()

    with pytest.raises(PlatformError) as error:
        manager.create_room("lobby-demo", "Ada", requested_capacity)

    assert error.value.code == "invalid_capacity"
    assert error.value.status_code == 400


def test_reconnect_restores_same_player():
    manager = RoomManager()
    result = manager.create_room("lobby-demo", "Ada", 3)

    manager.mark_disconnected(result.room.room_code, result.player.player_id)
    reconnect = manager.reconnect(
        result.room.room_code,
        result.player.player_id,
        result.session_token,
        connection_id="conn-2",
    )

    assert reconnect.player is result.player
    assert reconnect.player.connected is True
    assert reconnect.player.connection_id == "conn-2"
    assert reconnect.session_token == result.session_token


def test_mark_disconnected_ignores_stale_connection_id():
    manager = RoomManager()
    result = manager.create_room("lobby-demo", "Ada", 3)
    manager.reconnect(
        result.room.room_code,
        result.player.player_id,
        result.session_token,
        connection_id="conn-new",
    )

    disconnected = manager.mark_disconnected(
        result.room.room_code,
        result.player.player_id,
        connection_id="conn-old",
    )

    assert disconnected is None
    assert result.player.connected is True
    assert result.player.connection_id == "conn-new"


def test_snapshot_reflects_disconnected_and_reconnected_player_state():
    manager = RoomManager()
    result = manager.create_room("lobby-demo", "Ada", 3)

    manager.mark_disconnected(result.room.room_code, result.player.player_id)
    disconnected_snapshot = manager.get_snapshot(result.room.room_code, result.player.player_id)

    assert disconnected_snapshot["room"]["players"][0]["connected"] is False
    assert disconnected_snapshot["game"]["players"][0]["connected"] is False

    manager.reconnect(
        result.room.room_code,
        result.player.player_id,
        result.session_token,
        connection_id="conn-2",
    )
    reconnected_snapshot = manager.get_snapshot(result.room.room_code, result.player.player_id)

    assert reconnected_snapshot["room"]["players"][0]["connected"] is True
    assert reconnected_snapshot["game"]["players"][0]["connected"] is True


def test_record_heartbeat_updates_player_last_seen(monkeypatch):
    manager = RoomManager()
    result = manager.create_room("lobby-demo", "Ada", 3)
    heartbeat_at = datetime(2026, 5, 29, 12, 0, tzinfo=timezone.utc)

    result.player.last_seen_at = heartbeat_at - timedelta(seconds=20)
    monkeypatch.setattr(
        "app.platform.services.room_manager._utc_now",
        lambda: heartbeat_at,
    )

    manager.record_heartbeat(result.room.room_code, result.player.player_id)

    assert result.player.connected is True
    assert result.player.disconnected_at is None
    assert result.player.last_seen_at == heartbeat_at


def test_mark_inactive_connected_players_disconnected_updates_room_and_game_state():
    manager = RoomManager()
    result = manager.create_room("lobby-demo", "Ada", 3)
    now = datetime(2026, 5, 29, 12, 0, tzinfo=timezone.utc)
    result.player.last_seen_at = now - timedelta(seconds=31)

    changed_room_codes = manager.mark_inactive_connected_players_disconnected(
        timeout_seconds=30,
        now=now,
    )

    assert changed_room_codes == [result.room.room_code]
    assert result.player.connected is False
    assert result.player.connection_id is None
    assert result.player.disconnected_at == now
    snapshot = manager.get_snapshot(result.room.room_code, result.player.player_id)
    assert snapshot["room"]["players"][0]["connected"] is False
    assert snapshot["game"]["players"][0]["connected"] is False


def test_mark_inactive_connected_players_disconnected_keeps_recent_players_online():
    manager = RoomManager()
    result = manager.create_room("lobby-demo", "Ada", 3)
    now = datetime(2026, 5, 29, 12, 0, tzinfo=timezone.utc)
    result.player.last_seen_at = now - timedelta(seconds=29)

    changed_room_codes = manager.mark_inactive_connected_players_disconnected(
        timeout_seconds=30,
        now=now,
    )

    assert changed_room_codes == []
    assert result.player.connected is True


def test_disconnected_player_cannot_handle_game_action():
    manager = RoomManager()
    result = manager.create_room("lobby-demo", "Ada", 3)
    manager.mark_disconnected(result.room.room_code, result.player.player_id)

    with pytest.raises(PlatformError) as error:
        manager.handle_action(
            result.room.room_code,
            result.player.player_id,
            {"type": "set_message", "payload": {"message": "after disconnect"}},
        )

    assert error.value.code == "player_disconnected"
    snapshot = manager.get_snapshot(result.room.room_code, result.player.player_id)
    assert snapshot["game"]["messages"] == []


def test_reconnect_rejects_invalid_token():
    manager = RoomManager()
    result = manager.create_room("lobby-demo", "Ada", 3)

    with pytest.raises(PlatformError) as error:
        manager.reconnect(result.room.room_code, result.player.player_id, "bad-token")

    assert error.value.code == "invalid_session"
    assert error.value.status_code == 401


def test_get_snapshot_rejects_unknown_player():
    manager = RoomManager()
    result = manager.create_room("lobby-demo", "Ada", 3)

    with pytest.raises(PlatformError) as error:
        manager.get_snapshot(result.room.room_code, "missing-player")

    assert error.value.code == "player_not_found"
    assert error.value.status_code == 404


def test_get_game_info_includes_rules():
    info = RoomManager().get_game_info("lobby-demo")

    assert info["id"] == "lobby-demo"
    assert info["rules"]
