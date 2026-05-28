# SQLite Persistence And Room Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist rooms, players, session token hashes, and game state in SQLite, then add deterministic expired-room cleanup.

**Architecture:** Keep Flask routes and WebSocket handlers talking to `RoomManager`. Add a storage layer below `RoomManager` with an in-memory implementation for existing tests and a SQLite implementation for persistence tests and app runtime. `RoomManager` remains the platform rules and game hook orchestration boundary.

**Tech Stack:** Python 3.11+, Flask, Flask-Sock, pytest, uv, standard-library `sqlite3`, standard-library `json`.

---

## File Structure

- Create `apps/api/app/platform/services/room_storage.py`
  - Defines `RoomStorage`, `InMemoryRoomStorage`, `SQLiteRoomStorage`, `RoomStorageError`.
  - Owns SQLite schema creation, JSON serialization, datetime serialization, room save/load/delete.
- Modify `apps/api/app/platform/services/room_manager.py`
  - Accepts optional `storage`.
  - Replaces direct `_rooms` use with storage methods.
  - Persists every room mutation after game hooks update state.
  - Adds `cleanup_expired_rooms(now=None, room_ttl_seconds=DEFAULT_ROOM_TTL_SECONDS, empty_room_ttl_seconds=DEFAULT_EMPTY_ROOM_TTL_SECONDS)`.
- Modify `apps/api/app/__init__.py`
  - Accepts optional `config` and optional `room_manager`.
  - Builds `SQLiteRoomStorage` from `SQLITE_DB_PATH` by default.
  - Keeps tests able to inject a manager.
- Create `apps/api/tests/test_room_persistence.py`
  - Covers SQLite persistence, restart recovery, token hash persistence, and JSON state.
- Create `apps/api/tests/test_room_cleanup.py`
  - Covers deterministic cleanup behavior.
- Modify existing tests only where constructor behavior changes require it.
- Modify docs listed in the spec after backend tests pass.

## Task 1: Add Storage Layer And Preserve Existing In-Memory Behavior

**Files:**
- Create: `apps/api/app/platform/services/room_storage.py`
- Modify: `apps/api/app/platform/services/room_manager.py`
- Test: `apps/api/tests/test_room_manager.py`

- [ ] **Step 1: Write failing in-memory storage behavior test**

Add this test to `apps/api/tests/test_room_manager.py`:

```python
def test_room_manager_accepts_explicit_storage():
    from app.platform.services.room_storage import InMemoryRoomStorage

    storage = InMemoryRoomStorage()
    manager = RoomManager(storage=storage)

    result = manager.create_room("lobby-demo", "Ada", 3)

    assert storage.get_room(result.room.room_code) is result.room
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd apps/api && uv run pytest -v tests/test_room_manager.py::test_room_manager_accepts_explicit_storage
```

Expected: FAIL because `app.platform.services.room_storage` or `RoomManager(storage=...)` does not exist.

- [ ] **Step 3: Implement storage protocol and in-memory storage**

Create `apps/api/app/platform/services/room_storage.py`:

```python
from __future__ import annotations

from typing import Protocol

from app.platform.models import Room


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
```

Modify `apps/api/app/platform/services/room_manager.py`:

```python
from app.platform.services.room_storage import InMemoryRoomStorage, RoomStorage
```

Change constructor:

```python
class RoomManager:
    def __init__(
        self,
        games: dict[str, GameRegistration] | None = None,
        storage: RoomStorage | None = None,
    ) -> None:
        self._games = games if games is not None else create_game_registry()
        self._storage = storage if storage is not None else InMemoryRoomStorage()
```

Change room creation:

```python
self._storage.save_room(room)
return self.join_room(room_code, nickname)
```

Change `_get_room_by_code` lookup:

```python
room = self._storage.get_room(room_code)
```

Change `_generate_room_code` to this complete function:

```python
def _generate_room_code(self) -> str:
    existing_room_codes = self._storage.list_room_codes()
    for _ in range(1000):
        room_code = "".join(random.choices(string.digits, k=ROOM_CODE_LENGTH))
        if room_code not in existing_room_codes:
            return room_code
    raise PlatformError("room_code_unavailable", "Could not allocate room code.", 503)
```

After every mutation in `join_room`, `reconnect`, `mark_disconnected`, and `handle_action`, call:

```python
self._storage.save_room(room)
```

Do not alter public method names or route/WebSocket behavior.

- [ ] **Step 4: Run targeted room manager tests**

Run:

```bash
cd apps/api && uv run pytest -v tests/test_room_manager.py
```

Expected: all tests in `test_room_manager.py` PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/platform/services/room_storage.py apps/api/app/platform/services/room_manager.py apps/api/tests/test_room_manager.py
git commit -m "feat: add room storage boundary"
```

## Task 2: Add SQLite Storage And Persistence Tests

**Files:**
- Modify: `apps/api/app/platform/services/room_storage.py`
- Create: `apps/api/tests/test_room_persistence.py`

- [ ] **Step 1: Write failing SQLite persistence tests**

Create `apps/api/tests/test_room_persistence.py`:

```python
import sqlite3

from app.platform.services.room_manager import RoomManager
from app.platform.services.room_storage import SQLiteRoomStorage


def sqlite_manager(db_path):
    return RoomManager(storage=SQLiteRoomStorage(db_path))


def test_create_room_persists_room_host_and_game_state(tmp_path):
    db_path = tmp_path / "rooms.sqlite3"
    manager = sqlite_manager(db_path)

    result = manager.create_room("lobby-demo", "Ada", 3)

    with sqlite3.connect(db_path) as connection:
        room_row = connection.execute(
            "select room_code, game_id, capacity from rooms where room_code = ?",
            (result.room.room_code,),
        ).fetchone()
        player_row = connection.execute(
            "select player_id, nickname, session_token_hash from players where room_code = ?",
            (result.room.room_code,),
        ).fetchone()
        state_row = connection.execute(
            "select state_json from game_state where room_code = ?",
            (result.room.room_code,),
        ).fetchone()

    assert room_row == (result.room.room_code, "lobby-demo", 3)
    assert player_row[0] == result.player.player_id
    assert player_row[1] == "Ada"
    assert player_row[2]
    assert result.session_token not in player_row[2]
    assert '"players"' in state_row[0]


def test_join_room_persists_joined_player_and_capacity(tmp_path):
    db_path = tmp_path / "rooms.sqlite3"
    manager = sqlite_manager(db_path)
    created = manager.create_room("lobby-demo", "Ada", 2)

    joined = manager.join_room(created.room.room_code, "Lin")

    restarted = sqlite_manager(db_path)
    restored = restarted.get_room(created.room.room_code)
    assert restored.capacity == 2
    assert [player.nickname for player in restored.players] == ["Ada", "Lin"]
    assert restored.players[1].player_id == joined.player.player_id


def test_restarted_room_manager_restores_lobby_demo_state(tmp_path):
    db_path = tmp_path / "rooms.sqlite3"
    manager = sqlite_manager(db_path)
    created = manager.create_room("lobby-demo", "Ada", 3)
    manager.handle_action(
        created.room.room_code,
        created.player.player_id,
        {"type": "set_message", "payload": {"message": "hello"}},
    )

    restarted = sqlite_manager(db_path)
    snapshot = restarted.get_snapshot(created.room.room_code, created.player.player_id)

    assert snapshot["room"]["roomCode"] == created.room.room_code
    assert snapshot["room"]["players"][0]["connected"] is False
    assert snapshot["game"]["messages"] == [
        {"playerId": created.player.player_id, "name": "Ada", "message": "hello"}
    ]


def test_restarted_room_manager_allows_reconnect_with_existing_session_token(tmp_path):
    db_path = tmp_path / "rooms.sqlite3"
    manager = sqlite_manager(db_path)
    created = manager.create_room("lobby-demo", "Ada", 3)

    restarted = sqlite_manager(db_path)
    reconnect = restarted.reconnect(
        created.room.room_code,
        created.player.player_id,
        created.session_token,
        connection_id="conn-1",
    )

    assert reconnect.player.player_id == created.player.player_id
    assert reconnect.player.connected is True
    assert reconnect.player.connection_id == "conn-1"
    assert reconnect.session_token == created.session_token
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd apps/api && uv run pytest -v tests/test_room_persistence.py
```

Expected: FAIL because `SQLiteRoomStorage` does not exist.

- [ ] **Step 3: Implement SQLiteRoomStorage**

Add to `apps/api/app/platform/services/room_storage.py`:

```python
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any

from app.platform.models import Player
```

Add helpers:

```python
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
```

Add class:

```python
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
```

- [ ] **Step 4: Run persistence tests**

Run:

```bash
cd apps/api && uv run pytest -v tests/test_room_persistence.py
```

Expected: all tests in `test_room_persistence.py` PASS.

- [ ] **Step 5: Run room manager regression tests**

Run:

```bash
cd apps/api && uv run pytest -v tests/test_room_manager.py
```

Expected: all tests in `test_room_manager.py` PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/platform/services/room_storage.py apps/api/tests/test_room_persistence.py
git commit -m "feat: persist rooms in sqlite"
```

## Task 3: Add Deterministic Room Cleanup

**Files:**
- Modify: `apps/api/app/platform/services/room_manager.py`
- Modify: `apps/api/app/platform/services/room_storage.py`
- Create: `apps/api/tests/test_room_cleanup.py`

- [ ] **Step 1: Write failing cleanup tests**

Create `apps/api/tests/test_room_cleanup.py`:

```python
from datetime import timedelta

from app.platform.models import utc_now
from app.platform.services.room_manager import RoomManager
from app.platform.services.room_storage import SQLiteRoomStorage


def sqlite_manager(db_path):
    return RoomManager(storage=SQLiteRoomStorage(db_path))


def test_cleanup_removes_room_past_room_ttl(tmp_path):
    db_path = tmp_path / "rooms.sqlite3"
    now = utc_now()
    storage = SQLiteRoomStorage(db_path)
    manager = RoomManager(storage=storage)
    created = manager.create_room("lobby-demo", "Ada", 3)
    room = manager.get_room(created.room.room_code)
    room.updated_at = now - timedelta(seconds=301)
    storage.save_room(room)

    removed = manager.cleanup_expired_rooms(
        now=now,
        room_ttl_seconds=300,
        empty_room_ttl_seconds=60,
    )

    assert removed == [created.room.room_code]
    restarted = sqlite_manager(db_path)
    try:
        restarted.get_room(created.room.room_code)
    except Exception as error:
        assert getattr(error, "code", "") == "room_not_found"
    else:
        raise AssertionError("expired room should be deleted")


def test_cleanup_keeps_connected_room_before_room_ttl(tmp_path):
    db_path = tmp_path / "rooms.sqlite3"
    now = utc_now()
    storage = SQLiteRoomStorage(db_path)
    manager = RoomManager(storage=storage)
    created = manager.create_room("lobby-demo", "Ada", 3)
    room = manager.get_room(created.room.room_code)
    room.updated_at = now - timedelta(seconds=299)
    storage.save_room(room)

    removed = manager.cleanup_expired_rooms(
        now=now,
        room_ttl_seconds=300,
        empty_room_ttl_seconds=60,
    )

    assert removed == []
    assert manager.get_room(created.room.room_code).room_code == created.room.room_code


def test_cleanup_removes_empty_room_after_empty_ttl(tmp_path):
    db_path = tmp_path / "rooms.sqlite3"
    now = utc_now()
    storage = SQLiteRoomStorage(db_path)
    manager = RoomManager(storage=storage)
    created = manager.create_room("lobby-demo", "Ada", 3)
    manager.mark_disconnected(created.room.room_code, created.player.player_id)
    room = manager.get_room(created.room.room_code)
    room.updated_at = now - timedelta(seconds=61)
    room.players[0].disconnected_at = now - timedelta(seconds=61)
    room.players[0].last_seen_at = now - timedelta(seconds=61)
    storage.save_room(room)

    removed = manager.cleanup_expired_rooms(
        now=now,
        room_ttl_seconds=300,
        empty_room_ttl_seconds=60,
    )

    assert removed == [created.room.room_code]


def test_cleanup_keeps_recently_empty_room(tmp_path):
    db_path = tmp_path / "rooms.sqlite3"
    now = utc_now()
    storage = SQLiteRoomStorage(db_path)
    manager = RoomManager(storage=storage)
    created = manager.create_room("lobby-demo", "Ada", 3)
    manager.mark_disconnected(created.room.room_code, created.player.player_id)
    room = manager.get_room(created.room.room_code)
    room.updated_at = now - timedelta(seconds=30)
    room.players[0].disconnected_at = now - timedelta(seconds=30)
    room.players[0].last_seen_at = now - timedelta(seconds=30)
    storage.save_room(room)

    removed = manager.cleanup_expired_rooms(
        now=now,
        room_ttl_seconds=300,
        empty_room_ttl_seconds=60,
    )

    assert removed == []
    assert manager.get_room(created.room.room_code).room_code == created.room.room_code
```

- [ ] **Step 2: Run cleanup tests to verify they fail**

Run:

```bash
cd apps/api && uv run pytest -v tests/test_room_cleanup.py
```

Expected: FAIL because `cleanup_expired_rooms` does not exist.

- [ ] **Step 3: Add storage room listing**

Extend `RoomStorage` protocol in `room_storage.py`:

```python
def list_rooms(self) -> list[Room]:
    ...
```

Implement in `InMemoryRoomStorage`:

```python
def list_rooms(self) -> list[Room]:
    return list(self._rooms.values())
```

Implement in `SQLiteRoomStorage`:

```python
def list_rooms(self) -> list[Room]:
    return [
        room
        for room_code in sorted(self.list_room_codes())
        if (room := self.get_room(room_code)) is not None
    ]
```

- [ ] **Step 4: Add cleanup to RoomManager**

Add constants to `room_manager.py`:

```python
DEFAULT_ROOM_TTL_SECONDS = 60 * 60 * 12
DEFAULT_EMPTY_ROOM_TTL_SECONDS = 60 * 30
```

Add public method:

```python
def cleanup_expired_rooms(
    self,
    now: datetime | None = None,
    room_ttl_seconds: int = DEFAULT_ROOM_TTL_SECONDS,
    empty_room_ttl_seconds: int = DEFAULT_EMPTY_ROOM_TTL_SECONDS,
) -> list[str]:
    now = now or _utc_now()
    removed_room_codes: list[str] = []
    for room in self._storage.list_rooms():
        if self._is_room_expired(now, room, room_ttl_seconds, empty_room_ttl_seconds):
            self._storage.delete_room(room.room_code)
            removed_room_codes.append(room.room_code)
    return removed_room_codes
```

Add private helper:

```python
def _is_room_expired(
    self,
    now: datetime,
    room: Room,
    room_ttl_seconds: int,
    empty_room_ttl_seconds: int,
) -> bool:
    if room.expires_at is not None and room.expires_at <= now:
        return True
    if (now - room.updated_at).total_seconds() >= room_ttl_seconds:
        return True
    if room.players and all(not player.connected for player in room.players):
        last_disconnect = max(
            player.disconnected_at or player.last_seen_at
            for player in room.players
        )
        return (now - last_disconnect).total_seconds() >= empty_room_ttl_seconds
    return False
```

- [ ] **Step 5: Run cleanup tests**

Run:

```bash
cd apps/api && uv run pytest -v tests/test_room_cleanup.py
```

Expected: all tests in `test_room_cleanup.py` PASS.

- [ ] **Step 6: Run persistence and manager regression tests**

Run:

```bash
cd apps/api && uv run pytest -v tests/test_room_persistence.py tests/test_room_cleanup.py tests/test_room_manager.py
```

Expected: all listed tests PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/platform/services/room_manager.py apps/api/app/platform/services/room_storage.py apps/api/tests/test_room_cleanup.py
git commit -m "feat: clean up expired rooms"
```

## Task 4: Wire SQLite Storage Into Flask App Configuration

**Files:**
- Modify: `apps/api/app/__init__.py`
- Modify: `apps/api/tests/test_app_factory.py`
- Modify: `apps/api/tests/test_platform_routes.py`

- [ ] **Step 1: Write failing app factory tests**

Add to `apps/api/tests/test_app_factory.py`:

```python
from app.platform.services.room_manager import RoomManager


def test_create_app_accepts_injected_room_manager():
    manager = RoomManager()
    app = create_app(room_manager=manager)

    assert app.config["ROOM_MANAGER"] is manager


def test_create_app_uses_sqlite_db_path_config(tmp_path):
    db_path = tmp_path / "app.sqlite3"
    app = create_app({"SQLITE_DB_PATH": str(db_path)})
    client = app.test_client()

    response = client.post(
        "/api/rooms",
        json={"gameId": "lobby-demo", "nickname": "Ada", "capacity": 3},
    )

    assert response.status_code == 201
    assert db_path.exists()
```

Add to `apps/api/tests/test_platform_routes.py`:

```python
def test_room_created_with_sqlite_backing_survives_app_restart(tmp_path):
    db_path = tmp_path / "routes.sqlite3"
    first_client = create_app({"SQLITE_DB_PATH": str(db_path)}).test_client()
    create_response = first_client.post(
        "/api/rooms",
        json={"gameId": "lobby-demo", "nickname": "Ada", "capacity": 3},
    )
    room_code = create_response.get_json()["room"]["roomCode"]

    restarted_client = create_app({"SQLITE_DB_PATH": str(db_path)}).test_client()
    response = restarted_client.get(f"/api/rooms/{room_code}")

    assert response.status_code == 200
    assert response.get_json()["room"]["roomCode"] == room_code
```

- [ ] **Step 2: Run app tests to verify they fail**

Run:

```bash
cd apps/api && uv run pytest -v tests/test_app_factory.py tests/test_platform_routes.py::test_room_created_with_sqlite_backing_survives_app_restart
```

Expected: FAIL because `create_app` does not accept arguments.

- [ ] **Step 3: Implement configurable app factory**

Modify `apps/api/app/__init__.py`:

```python
from pathlib import Path
from typing import Any

from flask import Flask
from flask_sock import Sock

from app.games.registry import create_game_registry
from app.platform.routes import platform_bp
from app.platform.services.room_manager import RoomManager
from app.platform.services.room_storage import SQLiteRoomStorage
from app.platform.websocket import register_websocket_routes


def create_app(
    config: dict[str, Any] | None = None,
    room_manager: RoomManager | None = None,
) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        SQLITE_DB_PATH=str(Path(__file__).resolve().parents[1] / "var" / "game-platform.sqlite3"),
        ROOM_CLEANUP_ENABLED=True,
        ROOM_CLEANUP_INTERVAL_SECONDS=300,
        ROOM_TTL_SECONDS=60 * 60 * 12,
        EMPTY_ROOM_TTL_SECONDS=60 * 30,
        DISCONNECTED_PLAYER_TTL_SECONDS=60 * 10,
    )
    if config is not None:
        app.config.update(config)

    if room_manager is None:
        room_manager = RoomManager(
            create_game_registry(),
            storage=SQLiteRoomStorage(app.config["SQLITE_DB_PATH"]),
        )
    app.config["ROOM_MANAGER"] = room_manager
    app.register_blueprint(platform_bp)
    sock = Sock(app)
    register_websocket_routes(sock, room_manager)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
```

- [ ] **Step 4: Run app and route tests**

Run:

```bash
cd apps/api && uv run pytest -v tests/test_app_factory.py tests/test_platform_routes.py
```

Expected: all listed tests PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/__init__.py apps/api/tests/test_app_factory.py apps/api/tests/test_platform_routes.py
git commit -m "feat: configure sqlite-backed app"
```

## Task 5: Update Documentation And Contract Notes

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/deployment.md`
- Modify: `docs/development.md`
- Modify: `apps/api/README.md`
- Modify: `packages/game-contract/README.md`
- Modify: `docs/add-new-game.md`

- [ ] **Step 1: Update README storage description**

In `README.md`, replace:

```text
- 第一阶段存储：内存房间状态 + 内存匿名 session 恢复信息
```

with:

```text
- 第一阶段存储：SQLite 持久化房间、玩家、session token hash 和游戏状态；WebSocket 连接仍在进程内管理
```

- [ ] **Step 2: Update architecture document**

In `docs/architecture.md`, update the top runtime diagram to say:

```text
浏览器
  -> 静态前端资源
  -> /api 和 /ws 转发到单个 Python 后端
  -> 后端使用 SQLite 持久化房间、玩家、session token hash 和游戏状态
  -> 后端使用内存 ConnectionHub 管理当前 WebSocket 连接
```

Replace the first-stage limitation paragraph with:

```text
当前阶段采用 SQLite 持久化房间、玩家、session token hash 和游戏状态。后端进程重启后，房间和游戏状态可以从 SQLite 恢复；实时 WebSocket 连接和 connection_id 不会恢复，客户端需要用 playerId + sessionToken 重新连接。

SQLite 解决轻量持久化，不解决跨进程 WebSocket 广播或多 worker 连接映射。因此在没有 Redis、消息队列或跨进程广播层前，后端仍建议只运行一个 worker。
```

Add cleanup description:

```text
房间清理由平台层执行。超过 ROOM_TTL_SECONDS 的房间会被删除；所有玩家断线且超过 EMPTY_ROOM_TTL_SECONDS 的房间也会被删除。TTL 删除不会调用游戏模块钩子。
```

- [ ] **Step 3: Update deployment and development docs**

In `docs/deployment.md`, document:

```text
后端需要一个可写 SQLite 文件路径，默认配置为 SQLITE_DB_PATH。生产部署时应把该路径放到持久化磁盘目录，并确保后端进程有读写权限。SQLite 文件应纳入备份策略。

SQLite 不替代跨进程实时同步。没有跨进程 WebSocket 广播前，仍推荐单后端进程。
```

In `docs/development.md`, add backend guidance:

```text
平台持久化通过 RoomManager 下方的 storage 层完成。业务规则留在 RoomManager，SQLite 读写留在 storage。新增持久化测试应使用 pytest tmp_path 创建临时 SQLite 文件。
```

- [ ] **Step 4: Update API README and game contract docs**

In `apps/api/README.md`, replace the memory-state sentence with:

```text
早期推荐单进程运行。房间、玩家、session token hash 和游戏状态会保存到 SQLite；当前 WebSocket 连接仍保存在进程内。
```

Add config list:

```text
关键配置：

- SQLITE_DB_PATH
- ROOM_TTL_SECONDS
- EMPTY_ROOM_TTL_SECONDS
- DISCONNECTED_PLAYER_TTL_SECONDS
- ROOM_CLEANUP_ENABLED
- ROOM_CLEANUP_INTERVAL_SECONDS
```

In `packages/game-contract/README.md`, add under Snapshot:

```text
平台可能把 gameState 持久化到 SQLite，因此游戏状态必须保持 JSON 可序列化。游戏模块不应依赖进程内对象身份、文件句柄、连接对象或其他不可序列化状态。
```

In `docs/add-new-game.md`, add to "新游戏不应该做的事":

```text
- SQLite 持久化。
- 平台 sessionToken 或 sessionTokenHash 存储。
```

And add:

```text
游戏返回的状态需要保持 JSON 可序列化，平台会负责保存和恢复该状态。
```

- [ ] **Step 5: Run docs grep checks**

Run:

```bash
rg -n "内存房间状态|内存 RoomManager|重启.*丢失|房间状态默认保存在内存" README.md docs apps/api/README.md packages/game-contract/README.md
```

Expected: no stale statements claiming room state is only in memory or restart always loses rooms. Mentions that WebSocket connections are in memory are acceptable.

- [ ] **Step 6: Commit**

```bash
git add README.md docs/architecture.md docs/deployment.md docs/development.md apps/api/README.md packages/game-contract/README.md docs/add-new-game.md
git commit -m "docs: document sqlite persistence"
```

## Task 6: Full Verification

**Files:**
- No production edits expected.

- [ ] **Step 1: Run full backend test suite**

Run:

```bash
cd apps/api && uv run pytest -v
```

Expected: all backend tests PASS.

- [ ] **Step 2: Check worktree**

Run:

```bash
git status --short
```

Expected: clean worktree.

- [ ] **Step 3: Commit verification-only fixes if needed**

If Step 1 exposes issues, fix with TDD if new behavior is required, then run:

```bash
cd apps/api && uv run pytest -v
git add <changed-files>
git commit -m "fix: stabilize sqlite persistence"
```

If no fixes are needed, do not create an empty commit.

## Self-Review Notes

- Spec coverage: storage model is covered by Tasks 1-2; restart recovery by Task 2; cleanup by Task 3; app configuration by Task 4; docs by Task 5; verification by Task 6.
- Placeholder scan: no task contains placeholder instructions or undefined follow-up work.
- Type consistency: `RoomStorage`, `InMemoryRoomStorage`, `SQLiteRoomStorage`, `cleanup_expired_rooms`, and config keys are named consistently across tasks.
