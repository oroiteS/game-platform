import time

from app import create_app
from app.platform.services.room_manager import RoomManager


def test_create_app_registers_health_endpoint(tmp_path):
    app = create_app({"SQLITE_DB_PATH": str(tmp_path / "test.sqlite3")})
    client = app.test_client()

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_create_app_accepts_injected_room_manager():
    manager = RoomManager()
    app = create_app(room_manager=manager)

    assert app.config["ROOM_MANAGER"] is manager


def test_create_app_uses_sqlite_db_path_config(tmp_path):
    db_path = tmp_path / "app.sqlite3"
    app = create_app({"SQLITE_DB_PATH": str(db_path)})
    client = app.test_client()

    response = client.post(
        "/api/rooms",
        json={"gameId": "lobby-demo", "nickname": "Ada", "capacity": 3},
    )

    assert response.status_code == 201
    assert db_path.exists()


def test_create_app_cleanup_disabled_by_default(tmp_path):
    app = create_app({"SQLITE_DB_PATH": str(tmp_path / "app.sqlite3")})
    assert app.config["ROOM_CLEANUP_ENABLED"] is False


def test_create_app_starts_cleanup_scheduler_when_enabled(tmp_path):
    db_path = tmp_path / "app.sqlite3"
    app = create_app({
        "SQLITE_DB_PATH": str(db_path),
        "ROOM_CLEANUP_ENABLED": True,
        "ROOM_CLEANUP_INTERVAL_SECONDS": 1,
        "WAITING_ROOM_TTL_SECONDS": 1,
        "PLAYING_ROOM_TTL_SECONDS": 3600,
    })
    manager = app.config["ROOM_MANAGER"]

    result = manager.create_room("lobby-demo", "Ada", 3)
    result.room.updated_at = result.room.updated_at.replace(
        year=2020, month=1, day=1
    )
    manager._storage.save_room(result.room)

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if manager._storage.get_room(result.room.room_code) is None:
            break
        time.sleep(0.1)

    assert manager._storage.get_room(result.room.room_code) is None


def test_create_app_deletes_all_rooms_on_startup(tmp_path):
    db_path = tmp_path / "app.sqlite3"
    # First app: create a room
    app1 = create_app({"SQLITE_DB_PATH": str(db_path)})
    manager1 = app1.config["ROOM_MANAGER"]
    manager1.create_room("lobby-demo", "Ada", 3)
    assert len(manager1._storage.list_room_codes()) == 1

    # Second app with same DB: should have deleted the room on startup
    app2 = create_app({"SQLITE_DB_PATH": str(db_path)})
    manager2 = app2.config["ROOM_MANAGER"]
    assert len(manager2._storage.list_room_codes()) == 0
