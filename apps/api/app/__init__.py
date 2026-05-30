import logging
import threading
import time
from pathlib import Path
from typing import Any

from flask import Flask
from flask_sock import Sock

from app.games.registry import create_game_registry
from app.platform.routes import platform_bp
from app.platform.services.room_manager import RoomManager
from app.platform.services.room_storage import SQLiteRoomStorage
from app.platform.websocket import register_websocket_routes

logger = logging.getLogger(__name__)


def _start_cleanup_scheduler(
    room_manager: RoomManager,
    interval_seconds: int,
    room_ttl: int,
    empty_ttl: int,
    waiting_ttl: int,
    playing_ttl: int,
) -> None:
    def _cleanup_loop() -> None:
        while True:
            time.sleep(interval_seconds)
            try:
                removed = room_manager.cleanup_expired_rooms(
                    room_ttl_seconds=room_ttl,
                    empty_room_ttl_seconds=empty_ttl,
                    waiting_room_ttl_seconds=waiting_ttl,
                    playing_room_ttl_seconds=playing_ttl,
                )
                if removed:
                    logger.info(
                        "Cleaned up %d expired rooms: %s",
                        len(removed),
                        removed,
                    )
            except Exception:
                logger.exception("Room cleanup failed")

    thread = threading.Thread(target=_cleanup_loop, daemon=True)
    thread.start()


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
        WAITING_ROOM_TTL_SECONDS=60 * 30,
        PLAYING_ROOM_TTL_SECONDS=60 * 60,
        DISCONNECTED_PLAYER_TTL_SECONDS=60 * 10,
        PLAYER_ONLINE_TIMEOUT_SECONDS=30,
    )
    if config is not None:
        app.config.update(config)

    if room_manager is None:
        storage = SQLiteRoomStorage(app.config["SQLITE_DB_PATH"])
        storage.delete_all_rooms()
        room_manager = RoomManager(
            create_game_registry(),
            storage=storage,
        )
    app.config["ROOM_MANAGER"] = room_manager
    app.register_blueprint(platform_bp)
    sock = Sock(app)
    register_websocket_routes(
        sock,
        room_manager,
        player_timeout_seconds=app.config["PLAYER_ONLINE_TIMEOUT_SECONDS"],
    )

    if app.config["ROOM_CLEANUP_ENABLED"]:
        _start_cleanup_scheduler(
            room_manager,
            app.config["ROOM_CLEANUP_INTERVAL_SECONDS"],
            app.config["ROOM_TTL_SECONDS"],
            app.config["EMPTY_ROOM_TTL_SECONDS"],
            app.config["WAITING_ROOM_TTL_SECONDS"],
            app.config["PLAYING_ROOM_TTL_SECONDS"],
        )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
