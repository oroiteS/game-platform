from __future__ import annotations

from datetime import datetime, timedelta, timezone
import random
import string
import threading
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
from app.platform.services.room_storage import InMemoryRoomStorage, RoomStorage

ROOM_CODE_LENGTH = 6
MAX_NICKNAME_LENGTH = 24
PLATFORM_ROOM_CAPACITY = 30
DEFAULT_ROOM_TTL_SECONDS = 60 * 60 * 12
DEFAULT_EMPTY_ROOM_TTL_SECONDS = 60 * 30
DEFAULT_PLAYER_ONLINE_TIMEOUT_SECONDS = 30


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RoomManager:
    def __init__(
        self,
        games: dict[str, GameRegistration] | None = None,
        storage: RoomStorage | None = None,
    ) -> None:
        self._games = games if games is not None else create_game_registry()
        self._storage = storage if storage is not None else InMemoryRoomStorage()
        self._create_room_lock = threading.Lock()
        self._room_locks_lock = threading.Lock()
        self._room_locks: dict[str, threading.RLock] = {}
        self._active_connections_lock = threading.Lock()
        self._active_connections: dict[tuple[str, str], str] = {}
        if getattr(self._storage, "loads_saved_connection_state", False):
            self._mark_restored_rooms_disconnected()

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

        with self._create_room_lock:
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
            self._storage.save_room(room)
        return self.join_room(room_code, nickname)

    def join_room(self, room_code: str, nickname: str) -> JoinResult:
        with self._lock_for_room(room_code):
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
            self._storage.save_room(room)
            return JoinResult(room=room, player=player, session_token=session_token)

    def get_room(self, room_code: str) -> Room:
        with self._lock_for_room(room_code):
            return self._get_room_by_code(room_code)

    def cleanup_expired_rooms(
        self,
        now: datetime | None = None,
        room_ttl_seconds: int = DEFAULT_ROOM_TTL_SECONDS,
        empty_room_ttl_seconds: int = DEFAULT_EMPTY_ROOM_TTL_SECONDS,
    ) -> list[str]:
        cleanup_time = now if now is not None else _utc_now()
        removed_room_codes: list[str] = []

        for room in self._storage.list_rooms():
            if self._is_room_expired(
                room,
                cleanup_time,
                room_ttl_seconds=room_ttl_seconds,
                empty_room_ttl_seconds=empty_room_ttl_seconds,
            ):
                self._storage.delete_room(room.room_code)
                removed_room_codes.append(room.room_code)

        return removed_room_codes

    def reconnect(
        self,
        room_code: str,
        player_id: str,
        session_token: str,
        connection_id: str | None = None,
    ) -> JoinResult:
        with self._lock_for_room(room_code):
            room = self._get_room_by_code(room_code)
            player = self._find_player(room, player_id)
            if player is None or not verify_token(session_token, player.session_token_hash):
                raise PlatformError("invalid_session", "Invalid session token.", 401)

            player.connected = True
            player.connection_id = connection_id
            self._set_active_connection(room_code, player_id, connection_id)
            player.disconnected_at = None
            player.last_seen_at = _utc_now()
            game = self._get_game(room.game_id)
            result = game.module.on_player_reconnect(room.game_state, player.to_game_dict())
            room.game_state = result.get("state", room.game_state)
            room.updated_at = _utc_now()
            self._storage.save_room(room)
            return JoinResult(room=room, player=player, session_token=session_token)

    def record_heartbeat(
        self,
        room_code: str,
        player_id: str,
        connection_id: str | None = None,
    ) -> Player:
        with self._lock_for_room(room_code):
            room = self._get_room_by_code(room_code)
            player = self._require_player(room, player_id)
            if not self._connection_matches(room_code, player_id, connection_id):
                return player

            heartbeat_at = _utc_now()
            player.last_seen_at = heartbeat_at
            room.updated_at = heartbeat_at
            self._storage.save_room(room)
            return player

    def mark_disconnected(
        self,
        room_code: str,
        player_id: str,
        connection_id: str | None = None,
    ) -> Player | None:
        with self._lock_for_room(room_code):
            room = self._get_room_by_code(room_code)
            player = self._require_player(room, player_id)
            if not self._connection_matches(room_code, player_id, connection_id):
                return None

            disconnected_at = _utc_now()
            player.connected = False
            player.connection_id = None
            self._clear_active_connection(room_code, player_id)
            player.disconnected_at = disconnected_at
            player.last_seen_at = disconnected_at
            game = self._get_game(room.game_id)
            result = game.module.on_player_disconnect(room.game_state, player.to_game_dict())
            room.game_state = result.get("state", room.game_state)
            room.updated_at = disconnected_at
            self._storage.save_room(room)
            return player

    def mark_inactive_connected_players_disconnected(
        self,
        timeout_seconds: int = DEFAULT_PLAYER_ONLINE_TIMEOUT_SECONDS,
        now: datetime | None = None,
    ) -> list[str]:
        timeout_at = now if now is not None else _utc_now()
        changed_room_codes: list[str] = []

        for room_code in self._storage.list_room_codes():
            with self._lock_for_room(room_code):
                room = self._get_room_by_code(room_code)

                game = self._get_game(room.game_id)
                changed = False
                for player in room.players:
                    if not player.connected:
                        continue
                    if timeout_at - player.last_seen_at <= timedelta(seconds=timeout_seconds):
                        continue

                    player.connected = False
                    player.connection_id = None
                    self._clear_active_connection(room.room_code, player.player_id)
                    player.disconnected_at = timeout_at
                    player.last_seen_at = timeout_at
                    result = game.module.on_player_disconnect(
                        room.game_state,
                        player.to_game_dict(),
                    )
                    room.game_state = result.get("state", room.game_state)
                    changed = True

                if changed:
                    room.updated_at = timeout_at
                    self._storage.save_room(room)
                    changed_room_codes.append(room.room_code)

        return changed_room_codes

    def handle_action(
        self,
        room_code: str,
        player_id: str,
        action: dict[str, Any],
        connection_id: str | None = None,
    ) -> dict[str, Any]:
        with self._lock_for_room(room_code):
            room = self._get_room_by_code(room_code)
            player = self._find_player(room, player_id)
            if player is None:
                raise PlatformError("player_not_found", "Player was not found.", 404)
            if not player.connected:
                raise PlatformError("player_disconnected", "Player is disconnected.", 409)
            if not self._connection_matches(room_code, player_id, connection_id):
                raise PlatformError("stale_connection", "Connection is no longer active.", 409)

            player.last_seen_at = _utc_now()
            game = self._get_game(room.game_id)
            result = game.module.handle_action(room.game_state, player.to_game_dict(), action)
            room.game_state = result.get("state", room.game_state)
            room.updated_at = _utc_now()
            self._storage.save_room(room)
            return result

    def get_snapshot(self, room_code: str, player_id: str) -> dict[str, Any]:
        with self._lock_for_room(room_code):
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

    def _mark_restored_rooms_disconnected(self) -> None:
        disconnected_at = _utc_now()
        for room_code in self._storage.list_room_codes():
            room = self._storage.get_room(room_code)
            if room is None:
                continue

            game = self._get_game(room.game_id)
            changed = False
            for player in room.players:
                if not player.connected and player.connection_id is None:
                    continue

                player.connected = False
                player.connection_id = None
                player.disconnected_at = player.disconnected_at or disconnected_at
                player.last_seen_at = disconnected_at
                result = game.module.on_player_disconnect(room.game_state, player.to_game_dict())
                room.game_state = result.get("state", room.game_state)
                changed = True

            if changed:
                room.updated_at = disconnected_at
                self._storage.save_room(room)

    def _get_room_by_code(self, room_code: str) -> Room:
        if not self._is_valid_room_code(room_code):
            raise PlatformError("invalid_room_code", "Room code must be 6 digits.", 400)

        room = self._storage.get_room(room_code)
        if room is None:
            raise PlatformError("room_not_found", "Room was not found.", 404)
        self._apply_active_connection_ids(room)
        return room

    def _set_active_connection(
        self,
        room_code: str,
        player_id: str,
        connection_id: str | None,
    ) -> None:
        with self._active_connections_lock:
            key = (room_code, player_id)
            if connection_id is None:
                self._active_connections.pop(key, None)
                return
            self._active_connections[key] = connection_id

    def _clear_active_connection(self, room_code: str, player_id: str) -> None:
        with self._active_connections_lock:
            self._active_connections.pop((room_code, player_id), None)

    def _connection_matches(
        self,
        room_code: str,
        player_id: str,
        connection_id: str | None,
    ) -> bool:
        if connection_id is None:
            return True
        with self._active_connections_lock:
            return self._active_connections.get((room_code, player_id)) == connection_id

    def _apply_active_connection_ids(self, room: Room) -> None:
        with self._active_connections_lock:
            for player in room.players:
                player.connection_id = self._active_connections.get(
                    (room.room_code, player.player_id)
                )

    def _is_room_expired(
        self,
        room: Room,
        now: datetime,
        room_ttl_seconds: int,
        empty_room_ttl_seconds: int,
    ) -> bool:
        if room.expires_at is not None and room.expires_at <= now:
            return True

        if now - room.updated_at >= timedelta(seconds=room_ttl_seconds):
            return True

        if room.players and all(not player.connected for player in room.players):
            last_disconnected_at = max(
                player.disconnected_at or player.last_seen_at
                for player in room.players
            )
            if now - last_disconnected_at >= timedelta(seconds=empty_room_ttl_seconds):
                return True

        return False

    def _generate_room_code(self) -> str:
        existing_room_codes = self._storage.list_room_codes()
        for _ in range(1000):
            room_code = "".join(random.choices(string.digits, k=ROOM_CODE_LENGTH))
            if room_code not in existing_room_codes:
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

    def _lock_for_room(self, room_code: str) -> threading.RLock:
        with self._room_locks_lock:
            lock = self._room_locks.get(room_code)
            if lock is None:
                lock = threading.RLock()
                self._room_locks[room_code] = lock
            return lock

    def _is_valid_room_code(self, room_code: str) -> bool:
        return (
            isinstance(room_code, str)
            and len(room_code) == ROOM_CODE_LENGTH
            and room_code.isdigit()
        )
