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
                '<div style="display:grid;gap:16px;">'
                '<div>'
                '<p class="eyebrow" style="margin:0 0 8px;">角色</p>'
                '<p><strong style="color:var(--color-primary-strong);">1 名主持人</strong>'
                " — 不参与身份分配，负责抽题和猜测</p>"
                '<p><strong style="color:var(--color-accent);">其余玩家</strong>'
                " — 秘密选择「人类」或「伪人」</p>"
                "</div>"
                "<div>"
                '<p class="eyebrow" style="margin:0 0 8px;">流程</p>'
                '<ol style="margin:0;padding-left:1.2em;display:grid;gap:6px;">'
                "<li>所有玩家<strong>准备</strong>，其中一人成为<strong>主持人</strong></li>"
                "<li>每位玩家秘密选择<strong>人类</strong>或<strong>伪人</strong>身份</li>"
                '<li>伪人自动获得一个<strong style="color:var(--color-accent);">关键词</strong></li>'
                "<li>主持人抽取问题，玩家<strong>线下口头</strong>轮流回答</li>"
                '<li style="color:var(--color-accent);font-weight:700;">伪人必须将关键词自然融入回答</li>'
                "<li>主持人逐一猜测每个玩家的真实身份</li>"
                "<li>猜错立刻揭示真相；全部猜对则伪人获胜</li>"
                "</ol>"
                "</div>"
                "</div>"
            ),
            min_players=3,
            max_players=10,
            module=fake_person,
        ),
    }
