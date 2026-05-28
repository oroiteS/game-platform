from flask import Flask

from app.games.registry import create_game_registry
from app.platform.routes import platform_bp
from app.platform.services.room_manager import RoomManager


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["ROOM_MANAGER"] = RoomManager(create_game_registry())
    app.register_blueprint(platform_bp)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
