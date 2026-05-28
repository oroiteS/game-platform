from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, request

from app.platform.errors import PlatformError, error_response
from app.platform.models import JoinResult
from app.platform.services.room_manager import RoomManager

platform_bp = Blueprint("platform", __name__)


def _manager() -> RoomManager:
    return current_app.config["ROOM_MANAGER"]


def _json_body() -> dict[str, Any]:
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else {}


def _join_result_dict(result: JoinResult) -> dict[str, Any]:
    return {
        "room": result.room.to_public_dict(),
        "player": result.player.to_public_dict(),
        "sessionToken": result.session_token,
    }


@platform_bp.errorhandler(PlatformError)
def handle_platform_error(error: PlatformError) -> tuple[dict[str, dict[str, str]], int]:
    return error_response(error)


@platform_bp.get("/api/games")
def list_games() -> dict[str, list[dict[str, Any]]]:
    return {"games": _manager().list_games()}


@platform_bp.get("/api/games/<game_id>")
def get_game(game_id: str) -> dict[str, dict[str, Any]]:
    return {"game": _manager().get_game_info(game_id)}


@platform_bp.post("/api/rooms")
def create_room() -> tuple[dict[str, Any], int]:
    body = _json_body()
    result = _manager().create_room(
        body.get("gameId"),
        body.get("nickname"),
        body.get("capacity"),
    )
    return _join_result_dict(result), 201


@platform_bp.post("/api/rooms/<room_code>/join")
def join_room(room_code: str) -> dict[str, Any]:
    body = _json_body()
    result = _manager().join_room(room_code, body.get("nickname"))
    return _join_result_dict(result)


@platform_bp.get("/api/rooms/<room_code>")
def get_room(room_code: str) -> dict[str, Any]:
    return {"room": _manager().get_room(room_code).to_public_dict()}
