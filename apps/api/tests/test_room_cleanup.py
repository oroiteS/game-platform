from datetime import datetime, timedelta, timezone

from app.platform.services.room_manager import RoomManager
from app.platform.services.room_storage import SQLiteRoomStorage


def sqlite_manager(db_path):
    storage = SQLiteRoomStorage(db_path)
    manager = RoomManager(storage=storage)
    return storage, manager


def test_cleanup_removes_room_past_room_ttl(tmp_path):
    db_path = tmp_path / "rooms.sqlite3"
    storage, manager = sqlite_manager(db_path)
    now = datetime(2026, 5, 29, 12, 0, tzinfo=timezone.utc)
    created = manager.create_room("lobby-demo", "Ada", 3)
    created.room.updated_at = now - timedelta(seconds=60)
    storage.save_room(created.room)

    removed = manager.cleanup_expired_rooms(now=now, room_ttl_seconds=60)

    assert removed == [created.room.room_code]
    assert storage.get_room(created.room.room_code) is None


def test_cleanup_keeps_connected_room_before_room_ttl(tmp_path):
    db_path = tmp_path / "rooms.sqlite3"
    storage, manager = sqlite_manager(db_path)
    now = datetime(2026, 5, 29, 12, 0, tzinfo=timezone.utc)
    created = manager.create_room("lobby-demo", "Ada", 3)
    created.room.updated_at = now - timedelta(seconds=59)
    storage.save_room(created.room)

    removed = manager.cleanup_expired_rooms(now=now, room_ttl_seconds=60)

    assert removed == []
    assert storage.get_room(created.room.room_code) is not None


def test_cleanup_removes_empty_room_after_empty_ttl(tmp_path):
    db_path = tmp_path / "rooms.sqlite3"
    storage, manager = sqlite_manager(db_path)
    now = datetime(2026, 5, 29, 12, 0, tzinfo=timezone.utc)
    created = manager.create_room("lobby-demo", "Ada", 3)
    player = created.room.players[0]
    player.connected = False
    player.disconnected_at = now - timedelta(seconds=30)
    player.last_seen_at = player.disconnected_at
    created.room.updated_at = now - timedelta(seconds=5)
    storage.save_room(created.room)

    removed = manager.cleanup_expired_rooms(now=now, empty_room_ttl_seconds=30)

    assert removed == [created.room.room_code]
    assert storage.get_room(created.room.room_code) is None


def test_cleanup_keeps_recently_empty_room(tmp_path):
    db_path = tmp_path / "rooms.sqlite3"
    storage, manager = sqlite_manager(db_path)
    now = datetime(2026, 5, 29, 12, 0, tzinfo=timezone.utc)
    created = manager.create_room("lobby-demo", "Ada", 3)
    player = created.room.players[0]
    player.connected = False
    player.disconnected_at = now - timedelta(seconds=29)
    player.last_seen_at = player.disconnected_at
    created.room.updated_at = now - timedelta(seconds=5)
    storage.save_room(created.room)

    removed = manager.cleanup_expired_rooms(now=now, empty_room_ttl_seconds=30)

    assert removed == []
    assert storage.get_room(created.room.room_code) is not None

    room = manager.get_room(created.room.room_code)
    assert room.players[0].connected is False


def test_cleanup_uses_last_seen_when_disconnected_at_is_missing(tmp_path):
    db_path = tmp_path / "rooms.sqlite3"
    storage, manager = sqlite_manager(db_path)
    now = datetime(2026, 5, 29, 12, 0, tzinfo=timezone.utc)
    created = manager.create_room("lobby-demo", "Ada", 3)
    player = created.room.players[0]
    player.connected = False
    player.disconnected_at = None
    player.last_seen_at = now - timedelta(seconds=61)
    created.room.updated_at = now - timedelta(seconds=61)
    storage.save_room(created.room)

    removed = manager.cleanup_expired_rooms(
        now=now,
        room_ttl_seconds=300,
        empty_room_ttl_seconds=60,
    )

    assert removed == [created.room.room_code]
    assert storage.get_room(created.room.room_code) is None
