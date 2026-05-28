from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any
from typing import Protocol

from app.platform.models import Player, Room


class RoomStorageError(RuntimeError):
    pass


class RoomStorage(Protocol):
    def list_room_codes(self) -> set[str]:
        ...

    def get_room(self, room_code: str) -> Room | None:
        ...

    def save_room(self, room: Room) -> None:
        ...

    def delete_room(self, room_code: str) -> None:
        ...


class InMemoryRoomStorage:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}

    def list_room_codes(self) -> set[str]:
        return set(self._rooms)

    def get_room(self, room_code: str) -> Room | None:
        return self._rooms.get(room_code)

    def save_room(self, room: Room) -> None:
        self._rooms[room.room_code] = room

    def delete_room(self, room_code: str) -> None:
        self._rooms.pop(room_code, None)


def _datetime_to_text(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _datetime_from_text(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class SQLiteRoomStorage:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def list_room_codes(self) -> set[str]:
        with self._connect() as connection:
            rows = connection.execute("select room_code from rooms").fetchall()
        return {row["room_code"] for row in rows}

    def get_room(self, room_code: str) -> Room | None:
        with self._connect() as connection:
            room_row = connection.execute(
                "select * from rooms where room_code = ?",
                (room_code,),
            ).fetchone()
            if room_row is None:
                return None
            player_rows = connection.execute(
                "select * from players where room_code = ? order by rowid",
                (room_code,),
            ).fetchall()
            state_row = connection.execute(
                "select state_json from game_state where room_code = ?",
                (room_code,),
            ).fetchone()

        players = [
            Player(
                player_id=row["player_id"],
                nickname=row["nickname"],
                session_token_hash=row["session_token_hash"],
                connection_id=None,
                connected=False,
                disconnected_at=_datetime_from_text(row["disconnected_at"]),
                last_seen_at=_datetime_from_text(row["last_seen_at"]),
            )
            for row in player_rows
        ]
        game_state: Any = None
        if state_row is not None:
            game_state = json.loads(state_row["state_json"])
        return Room(
            room_code=room_row["room_code"],
            game_id=room_row["game_id"],
            status=room_row["status"],
            capacity=room_row["capacity"],
            players=players,
            game_state=game_state,
            created_at=_datetime_from_text(room_row["created_at"]),
            updated_at=_datetime_from_text(room_row["updated_at"]),
            expires_at=_datetime_from_text(room_row["expires_at"]),
        )

    def save_room(self, room: Room) -> None:
        try:
            state_json = json.dumps(room.game_state, separators=(",", ":"), sort_keys=True)
        except (TypeError, ValueError) as error:
            raise RoomStorageError("Room game_state must be JSON serializable.") from error

        with self._connect() as connection:
            connection.execute(
                """
                insert into rooms (
                    room_code, game_id, status, capacity, created_at, updated_at, expires_at
                ) values (?, ?, ?, ?, ?, ?, ?)
                on conflict(room_code) do update set
                    game_id = excluded.game_id,
                    status = excluded.status,
                    capacity = excluded.capacity,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at,
                    expires_at = excluded.expires_at
                """,
                (
                    room.room_code,
                    room.game_id,
                    room.status,
                    room.capacity,
                    _datetime_to_text(room.created_at),
                    _datetime_to_text(room.updated_at),
                    _datetime_to_text(room.expires_at),
                ),
            )
            connection.execute("delete from players where room_code = ?", (room.room_code,))
            connection.executemany(
                """
                insert into players (
                    player_id, room_code, nickname, session_token_hash,
                    connected, disconnected_at, last_seen_at
                ) values (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        player.player_id,
                        room.room_code,
                        player.nickname,
                        player.session_token_hash,
                        1 if player.connected else 0,
                        _datetime_to_text(player.disconnected_at),
                        _datetime_to_text(player.last_seen_at),
                    )
                    for player in room.players
                ],
            )
            connection.execute(
                """
                insert into game_state (room_code, state_json, updated_at)
                values (?, ?, ?)
                on conflict(room_code) do update set
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                (room.room_code, state_json, _datetime_to_text(room.updated_at)),
            )

    def delete_room(self, room_code: str) -> None:
        with self._connect() as connection:
            connection.execute("delete from rooms where room_code = ?", (room_code,))

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("pragma foreign_keys = on")
        return connection

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                create table if not exists rooms (
                    room_code text primary key,
                    game_id text not null,
                    status text not null,
                    capacity integer not null,
                    created_at text not null,
                    updated_at text not null,
                    expires_at text null
                );

                create table if not exists players (
                    player_id text primary key,
                    room_code text not null references rooms(room_code) on delete cascade,
                    nickname text not null,
                    session_token_hash text not null,
                    connected integer not null,
                    disconnected_at text null,
                    last_seen_at text not null
                );

                create table if not exists game_state (
                    room_code text primary key references rooms(room_code) on delete cascade,
                    state_json text not null,
                    updated_at text not null
                );
                """
            )
