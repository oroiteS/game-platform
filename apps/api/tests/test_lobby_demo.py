import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from games.lobby_demo.server.lobby_demo import (
    create_initial_state,
    get_state_snapshot,
    handle_action,
    on_player_join,
)


def player(player_id="p1", nickname="Ada", connected=True):
    return {"playerId": player_id, "nickname": nickname, "connected": connected}


def test_lobby_demo_tracks_joined_players():
    state = create_initial_state({"roomCode": "123456"})

    result = on_player_join(state, player())

    assert result["status"] == "accepted"
    assert result["state"]["players"]["p1"]["nickname"] == "Ada"


def test_lobby_demo_rejects_empty_message():
    state = create_initial_state({"roomCode": "123456"})
    on_player_join(state, player())

    result = handle_action(state, player(), {"type": "set_message", "payload": {"message": ""}})

    assert result["status"] == "rejected"
    assert result["errorCode"] == "invalid_message"


def test_lobby_demo_snapshot_is_public():
    state = create_initial_state({"roomCode": "123456"})
    on_player_join(state, player())
    handle_action(state, player(), {"type": "set_message", "payload": {"message": "hello"}})

    snapshot = get_state_snapshot(state, player())

    assert snapshot == {
        "message": "hello",
        "players": [{"playerId": "p1", "nickname": "Ada", "connected": True}],
    }
