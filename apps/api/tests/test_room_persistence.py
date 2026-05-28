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
