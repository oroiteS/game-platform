from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from types import ModuleType
from typing import Any


@dataclass(frozen=True)
class GameRegistration:
    game_id: str
    name: str
    summary: str
    rules: str
    min_players: int
    max_players: int
    module: ModuleType

    def to_list_dict(self) -> dict[str, Any]:
        return {
            "id": self.game_id,
            "name": self.name,
            "summary": self.summary,
            "minPlayers": self.min_players,
            "maxPlayers": self.max_players,
        }

    def to_info_dict(self) -> dict[str, Any]:
        return {
            **self.to_list_dict(),
            "rules": self.rules,
        }


def create_game_registry() -> dict[str, GameRegistration]:
    lobby_demo = import_module("games.lobby_demo.server")
    return {
        "lobby-demo": GameRegistration(
            game_id="lobby-demo",
            name="Lobby Demo",
            summary=(
                "Demo lobby for validating room creation, anonymous players, "
                "shared message history, and reconnect snapshots."
            ),
            rules=(
                "Players join a shared lobby and may append short messages to a room-wide history. "
                "The demo accepts 1 to 30 players, tracks connected status, and is "
                "intended to exercise platform room/session behavior rather than a "
                "win condition."
            ),
            min_players=1,
            max_players=30,
            module=lobby_demo,
        )
    }
