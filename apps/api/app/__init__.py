from pathlib import Path
from typing import Any

from flask import Flask
from flask_sock import Sock

from app.games.registry import create_game_registry
from app.platform.routes import platform_bp
from app.platform.services.room_manager import RoomManager
from app.platform.services.room_storage import SQLiteRoomStorage
from app.platform.websocket import register_websocket_routes


def create_app(
    config: dict[str, Any] | None = None,
    room_manager: RoomManager | None = None,
) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        SQLITE_DB_PATH=Path(__file__).resolve().parents[1] / "var" / "game-platform.sqlite3",
        ROOM_CLEANUP_ENABLED=False,
        ROOM_CLEANUP_INTERVAL_SECONDS=300,
        ROOM_TTL_SECONDS=60 * 60 * 12,
        EMPTY_ROOM_TTL_SECONDS=60 * 30,
        DISCONNECTED_PLAYER_TTL_SECONDS=60 * 10,
        PLAYER_ONLINE_TIMEOUT_SECONDS=30,
    )
    if config is not None:
        app.config.update(config)

    if room_manager is None:
        room_manager = RoomManager(
            create_game_registry(),
            storage=SQLiteRoomStorage(app.config["SQLITE_DB_PATH"]),
        )
    app.config["ROOM_MANAGER"] = room_manager
    app.register_blueprint(platform_bp)
    sock = Sock(app)
    register_websocket_routes(
        sock,
        room_manager,
        player_timeout_seconds=app.config["PLAYER_ONLINE_TIMEOUT_SECONDS"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
