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


def test_lobby_demo_keeps_message_history_with_sender_names():
    state = create_initial_state({"roomCode": "123456"})
    on_player_join(state, player("p1", "Ada"))
    on_player_join(state, player("p2", "Lin"))

    first_result = handle_action(
        state,
        player("p1", "Ada"),
        {"type": "set_message", "payload": {"message": "hello"}},
    )
    second_result = handle_action(
        state,
        player("p2", "Lin"),
        {"type": "set_message", "payload": {"message": "ready"}},
    )

    snapshot = get_state_snapshot(state, player("viewer", "Viewer"))

    assert first_result["status"] == "accepted"
    assert second_result["status"] == "accepted"
    assert snapshot["messages"] == [
        {"playerId": "p1", "name": "Ada", "message": "hello"},
        {"playerId": "p2", "name": "Lin", "message": "ready"},
    ]


def test_lobby_demo_snapshot_is_public():
    state = create_initial_state({"roomCode": "123456"})
    on_player_join(state, player())
    handle_action(state, player(), {"type": "set_message", "payload": {"message": "hello"}})

    snapshot = get_state_snapshot(state, player())

    assert snapshot == {
        "messages": [{"playerId": "p1", "name": "Ada", "message": "hello"}],
        "players": [{"playerId": "p1", "nickname": "Ada", "connected": True}],
    }


def test_lobby_demo_snapshot_sorts_duplicate_nicknames_by_player_id():
    state = create_initial_state({"roomCode": "123456"})
    on_player_join(state, player("p2", "Ada"))
    on_player_join(state, player("p1", "ada"))

    snapshot = get_state_snapshot(state, player())

    assert [player["playerId"] for player in snapshot["players"]] == ["p1", "p2"]
