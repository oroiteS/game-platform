from flask import Flask
from flask_sock import Sock

from app.games.registry import create_game_registry
from app.platform.routes import platform_bp
from app.platform.services.room_manager import RoomManager
from app.platform.websocket import register_websocket_routes


def create_app() -> Flask:
    app = Flask(__name__)
    room_manager = RoomManager(create_game_registry())
    app.config["ROOM_MANAGER"] = room_manager
    app.register_blueprint(platform_bp)
    sock = Sock(app)
    register_websocket_routes(sock, room_manager)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
