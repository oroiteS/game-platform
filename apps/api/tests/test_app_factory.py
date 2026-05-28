from app import create_app
from app.platform.services.room_manager import RoomManager


def test_create_app_registers_health_endpoint():
    app = create_app()
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
