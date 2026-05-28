from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Player:
    player_id: str
    nickname: str
    session_token_hash: str
    connection_id: str | None = None
    connected: bool = True
    disconnected_at: datetime | None = None
    last_seen_at: datetime = field(default_factory=utc_now)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "playerId": self.player_id,
            "nickname": self.nickname,
            "connected": self.connected,
        }

    def to_game_dict(self) -> dict[str, Any]:
        return self.to_public_dict()


@dataclass
class Room:
    room_code: str
    game_id: str
    status: str
    capacity: int
    players: list[Player] = field(default_factory=list)
    game_state: Any = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    expires_at: datetime | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "roomCode": self.room_code,
            "gameId": self.game_id,
            "status": self.status,
            "capacity": self.capacity,
            "players": [player.to_public_dict() for player in self.players],
        }


@dataclass(frozen=True)
class JoinResult:
    room: Room
    player: Player
    session_token: str
