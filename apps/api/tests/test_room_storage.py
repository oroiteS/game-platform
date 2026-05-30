from app.platform.services.room_storage import InMemoryRoomStorage, SQLiteRoomStorage
from app.platform.services.room_manager import RoomManager


def test_in_memory_delete_all_rooms():
    storage = InMemoryRoomStorage()
    manager = RoomManager(storage=storage)
    manager.create_room("lobby-demo", "Ada", 3)
    manager.create_room("lobby-demo", "Bob", 3)

    assert len(storage.list_room_codes()) == 2

    storage.delete_all_rooms()

    assert len(storage.list_room_codes()) == 0


def test_sqlite_delete_all_rooms(tmp_path):
    db_path = tmp_path / "rooms.sqlite3"
    storage = SQLiteRoomStorage(db_path)
    manager = RoomManager(storage=storage)
    manager.create_room("lobby-demo", "Ada", 3)
    manager.create_room("lobby-demo", "Bob", 3)

    assert len(storage.list_room_codes()) == 2

    storage.delete_all_rooms()

    assert len(storage.list_room_codes()) == 0
