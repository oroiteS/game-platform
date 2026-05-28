from __future__ import annotations

from datetime import datetime, timezone
import random
import string
from typing import Any
from uuid import uuid4

from app.games.registry import GameRegistration, create_game_registry
from app.platform.errors import PlatformError
from app.platform.models import JoinResult, Player, Room
from app.platform.services.session_tokens import (
    generate_session_token,
    hash_token,
    verify_token,
)

ROOM_CODE_LENGTH = 6
MAX_NICKNAME_LENGTH = 24
PLATFORM_ROOM_CAPACITY = 30


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RoomManager:
    def __init__(self, games: dict[str, GameRegistration] | None = None) -> None:
        self._games = games if games is not None else create_game_registry()
        self._rooms: dict[str, Room] = {}

    @property
    def platform_room_capacity(self) -> int:
        return PLATFORM_ROOM_CAPACITY

    def list_games(self) -> list[dict[str, Any]]:
        return [game.to_list_dict() for game in self._games.values()]

    def get_game_info(self, game_id: str) -> dict[str, Any]:
        return self._get_game(game_id).to_info_dict()

    def create_room(
        self,
        game_id: str,
        nickname: str,
        requested_capacity: int,
    ) -> JoinResult:
        game = self._get_game(game_id)
        nickname = self._validate_nickname(nickname)
        capacity = self._validate_capacity(requested_capacity, game)

        room_code = self._generate_room_code()
        game_state = game.module.create_initial_state(
            {"roomCode": room_code, "gameId": game.game_id, "capacity": capacity}
        )
        room = Room(
            room_code=room_code,
            game_id=game.game_id,
            status="waiting",
            capacity=capacity,
            game_state=game_state,
        )
        self._rooms[room_code] = room
        return self.join_room(room_code, nickname)

    def join_room(self, room_code: str, nickname: str) -> JoinResult:
        room = self._get_room_by_code(room_code)
        game = self._get_game(room.game_id)
        nickname = self._validate_nickname(nickname)

        if len(room.players) >= room.capacity:
            raise PlatformError("room_full", "Room is full.", 409)

        session_token = generate_session_token()
        player = Player(
            player_id=uuid4().hex,
            nickname=nickname,
            session_token_hash=hash_token(session_token),
        )
        room.players.append(player)
        result = game.module.on_player_join(room.game_state, player.to_game_dict())
        room.game_state = result.get("state", room.game_state)
        room.updated_at = _utc_now()
        return JoinResult(room=room, player=player, session_token=session_token)

    def get_room(self, room_code: str) -> Room:
        return self._get_room_by_code(room_code)

    def reconnect(
        self,
        room_code: str,
        player_id: str,
        session_token: str,
        connection_id: str | None = None,
    ) -> JoinResult:
        room = self._get_room_by_code(room_code)
        player = self._find_player(room, player_id)
        if player is None or not verify_token(session_token, player.session_token_hash):
            raise PlatformError("invalid_session", "Invalid session token.", 401)

        player.connected = True
        player.connection_id = connection_id
        player.disconnected_at = None
        player.last_seen_at = _utc_now()
        game = self._get_game(room.game_id)
        result = game.module.on_player_reconnect(room.game_state, player.to_game_dict())
        room.game_state = result.get("state", room.game_state)
        room.updated_at = _utc_now()
        return JoinResult(room=room, player=player, session_token=session_token)

    def mark_disconnected(self, room_code: str, player_id: str) -> Player:
        room = self._get_room_by_code(room_code)
        player = self._require_player(room, player_id)
        disconnected_at = _utc_now()
        player.connected = False
        player.connection_id = None
        player.disconnected_at = disconnected_at
        player.last_seen_at = disconnected_at
        game = self._get_game(room.game_id)
        result = game.module.on_player_disconnect(room.game_state, player.to_game_dict())
        room.game_state = result.get("state", room.game_state)
        room.updated_at = disconnected_at
        return player

    def handle_action(self, room_code: str, player_id: str, action: dict[str, Any]) -> dict[str, Any]:
        room = self._get_room_by_code(room_code)
        player = self._find_player(room, player_id)
        if player is None:
            raise PlatformError("player_not_found", "Player was not found.", 404)

        player.last_seen_at = _utc_now()
        game = self._get_game(room.game_id)
        result = game.module.handle_action(room.game_state, player.to_game_dict(), action)
        room.game_state = result.get("state", room.game_state)
        room.updated_at = _utc_now()
        return result

    def get_snapshot(self, room_code: str, player_id: str) -> dict[str, Any]:
        room = self._get_room_by_code(room_code)
        player = self._find_player(room, player_id)
        if player is None:
            raise PlatformError("player_not_found", "Player was not found.", 404)

        game = self._get_game(room.game_id)
        return {
            "room": room.to_public_dict(),
            "game": game.module.get_state_snapshot(room.game_state, player.to_game_dict()),
        }

    def _get_game(self, game_id: Any) -> GameRegistration:
        if not isinstance(game_id, str) or not game_id.strip():
            raise PlatformError("invalid_game_id", "Game id is required.", 400)

        game = self._games.get(game_id)
        if game is None:
            raise PlatformError("game_not_found", "Game was not found.", 404)
        return game

    def _get_room_by_code(self, room_code: str) -> Room:
        if not self._is_valid_room_code(room_code):
            raise PlatformError("invalid_room_code", "Room code must be 6 digits.", 400)

        room = self._rooms.get(room_code)
        if room is None:
            raise PlatformError("room_not_found", "Room was not found.", 404)
        return room

    def _generate_room_code(self) -> str:
        for _ in range(1000):
            room_code = "".join(random.choices(string.digits, k=ROOM_CODE_LENGTH))
            if room_code not in self._rooms:
                return room_code
        raise PlatformError("room_code_unavailable", "Could not allocate room code.", 503)

    def _validate_nickname(self, nickname: str) -> str:
        if not isinstance(nickname, str):
            raise PlatformError("invalid_nickname", "Nickname is required.", 400)

        normalized = nickname.strip()
        if not normalized or len(normalized) > MAX_NICKNAME_LENGTH:
            raise PlatformError("invalid_nickname", "Nickname must be 1 to 24 characters.", 400)
        return normalized

    def _validate_capacity(self, requested_capacity: int, game: GameRegistration) -> int:
        if type(requested_capacity) is not int:
            raise PlatformError("invalid_capacity", "Capacity must be an integer.", 400)

        max_capacity = min(PLATFORM_ROOM_CAPACITY, game.max_players)
        if requested_capacity < game.min_players or requested_capacity > max_capacity:
            raise PlatformError("invalid_capacity", "Capacity is outside the allowed range.", 400)
        return requested_capacity

    def _require_player(self, room: Room, player_id: str) -> Player:
        player = self._find_player(room, player_id)
        if player is None:
            raise PlatformError("player_not_found", "Player was not found.", 404)
        return player

    def _find_player(self, room: Room, player_id: str) -> Player | None:
        return next((player for player in room.players if player.player_id == player_id), None)

    def _is_valid_room_code(self, room_code: str) -> bool:
        return (
            isinstance(room_code, str)
            and len(room_code) == ROOM_CODE_LENGTH
            and room_code.isdigit()
        )
