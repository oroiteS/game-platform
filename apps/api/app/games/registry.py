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
    fake_person = import_module("games.fake_person.server")
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
        ),
        "fake-person": GameRegistration(
            game_id="fake-person",
            name="伪人游戏",
            summary="谁是伪人？玩家秘密获取身份，主持人猜测每个人的真实身份。",
            rules=(
                "1 名主持人（不参与），其余玩家秘密选择「人类」或「伪人」身份。"
                "伪人随机获得一个关键词。主持人抽取问题后，玩家线下轮流回答"
                "（伪人必须将关键词融入回答）。主持人逐一猜测每个玩家是人是伪人，"
                "猜错即揭示真相。"
            ),
            min_players=3,
            max_players=10,
            module=fake_person,
        ),
    }
