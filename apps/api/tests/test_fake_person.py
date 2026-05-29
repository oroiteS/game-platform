"""Tests for the fake-person game backend module."""

from games.fake_person.server.fake_person import (
    create_initial_state,
    get_state_snapshot,
    handle_action,
    on_player_disconnect,
    on_player_join,
    on_player_leave,
    on_player_reconnect,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def player(pid="p1", nickname="Ada", connected=True):
    return {"playerId": pid, "nickname": nickname, "connected": connected}


def fresh_lobby(capacity=4):
    return create_initial_state({
        "roomCode": "123456",
        "gameId": "fake-person",
        "capacity": capacity,
    })


def lobby_with_players(capacity=4, player_ids=None):
    state = fresh_lobby(capacity)
    for pid in (player_ids or ["p1", "p2", "p3", "p4"]):
        state = on_player_join(state, player(pid, f"P{pid[-1]}"))["state"]
    return state


def setup_identity_pick(capacity=4, player_ids=None):
    """Returns state after someone becomes host and all others pick identities."""
    ids = player_ids or ["p1", "p2", "p3", "p4"]
    state = lobby_with_players(capacity, ids)
    state["readyPlayerIds"] = list(ids)
    result = handle_action(state, player(ids[0]), {"type": "become_host"})
    return result["state"]


def setup_question_phase(capacity=4, player_ids=None):
    """All non-host players pick 'human' and host draws a question."""
    ids = player_ids or ["p1", "p2", "p3", "p4"]
    state = setup_identity_pick(capacity, ids)
    host_id = ids[0]
    for pid in ids[1:]:
        state = handle_action(
            state, player(pid),
            {"type": "pick_identity", "payload": {"role": "human"}},
        )["state"]
    state = handle_action(state, player(host_id), {"type": "draw_question"})["state"]
    return state


# ===================================================================
# Initial State
# ===================================================================


def test_create_initial_state():
    state = fresh_lobby(6)

    assert state["phase"] == "lobby"
    assert state["hostPlayerId"] is None
    assert state["readyPlayerIds"] == []
    assert state["identities"] == {}
    assert state["currentQuestion"] is None
    assert state["currentGuess"] is None
    assert state["guessedPlayerIds"] == []
    assert state["playerIds"] == []
    assert state["playerInfo"] == {}
    assert state["capacity"] == 6


# ===================================================================
# Player Lifecycle
# ===================================================================


def test_on_player_join_adds_to_tracking():
    state = fresh_lobby(4)

    result = on_player_join(state, player("p1", "Ada"))

    assert result["status"] == "accepted"
    assert "p1" in result["state"]["playerIds"]
    assert result["state"]["playerInfo"]["p1"]["nickname"] == "Ada"


def test_on_player_leave_removes_player():
    state = lobby_with_players(4, ["p1", "p2", "p3", "p4"])
    # Put p2 into every collection that tracks players
    state["readyPlayerIds"] = ["p2"]
    state["identities"] = {"p2": {"role": "human"}}
    state["guessedPlayerIds"] = ["p2"]

    result = on_player_leave(state, player("p2"))

    assert result["status"] == "accepted"
    new_state = result["state"]
    assert "p2" not in new_state["playerIds"]
    assert "p2" not in new_state["playerInfo"]
    assert "p2" not in new_state["identities"]
    assert "p2" not in new_state["readyPlayerIds"]
    assert "p2" not in new_state["guessedPlayerIds"]


def test_on_player_leave_host_resets_to_lobby():
    state = lobby_with_players(4, ["p1", "p2", "p3", "p4"])
    state["hostPlayerId"] = "p1"

    result = on_player_leave(state, player("p1"))

    assert result["status"] == "accepted"
    new_state = result["state"]
    assert new_state["phase"] == "lobby"
    assert new_state["hostPlayerId"] is None
    assert "p1" not in new_state["playerIds"]
    assert "p2" in new_state["playerIds"]
    assert "p3" in new_state["playerIds"]
    assert "p4" in new_state["playerIds"]
    assert new_state["capacity"] == 4


def test_on_player_disconnect_accepted():
    state = fresh_lobby(4)

    result = on_player_disconnect(state, player("p1"))

    assert result["status"] == "accepted"


def test_on_player_reconnect_accepted():
    state = fresh_lobby(4)

    result = on_player_reconnect(state, player("p1"))

    assert result["status"] == "accepted"


# ===================================================================
# toggle_ready
# ===================================================================


def test_toggle_ready_adds_player():
    state = lobby_with_players(4, ["p1", "p2", "p3", "p4"])

    result = handle_action(state, player("p1"), {"type": "toggle_ready"})

    assert result["status"] == "accepted"
    assert "p1" in result["state"]["readyPlayerIds"]


def test_toggle_ready_removes_player():
    state = lobby_with_players(4, ["p1", "p2", "p3", "p4"])
    state["readyPlayerIds"] = ["p1"]

    result = handle_action(state, player("p1"), {"type": "toggle_ready"})

    assert result["status"] == "accepted"
    assert "p1" not in result["state"]["readyPlayerIds"]


def test_toggle_ready_rejected_wrong_phase():
    state = setup_identity_pick(4, ["p1", "p2", "p3", "p4"])
    # Phase is now identity_pick, not lobby

    result = handle_action(state, player("p2"), {"type": "toggle_ready"})

    assert result["status"] == "rejected"
    assert result["errorCode"] == "wrong_phase"


def test_toggle_ready_rejected_host():
    state = lobby_with_players(4, ["p1", "p2", "p3", "p4"])
    state["hostPlayerId"] = "p1"

    result = handle_action(state, player("p1"), {"type": "toggle_ready"})

    assert result["status"] == "rejected"
    assert result["errorCode"] == "host_cannot_ready"


# ===================================================================
# become_host
# ===================================================================


def test_become_host_success():
    state = lobby_with_players(4, ["p1", "p2", "p3", "p4"])
    state["readyPlayerIds"] = ["p1", "p2", "p3", "p4"]

    result = handle_action(state, player("p1"), {"type": "become_host"})

    assert result["status"] == "accepted"
    new_state = result["state"]
    assert new_state["hostPlayerId"] == "p1"
    assert new_state["phase"] == "identity_pick"
    assert new_state["readyPlayerIds"] == []


def test_become_host_rejected_not_all_ready():
    state = lobby_with_players(4, ["p1", "p2", "p3", "p4"])
    state["readyPlayerIds"] = ["p1", "p2"]  # only 2 of 4 ready

    result = handle_action(state, player("p1"), {"type": "become_host"})

    assert result["status"] == "rejected"
    assert result["errorCode"] == "not_all_ready"


def test_become_host_rejected_not_full():
    state = lobby_with_players(4, ["p1", "p2", "p3"])  # 3 players, capacity 4
    state["readyPlayerIds"] = ["p1", "p2", "p3"]

    result = handle_action(state, player("p1"), {"type": "become_host"})

    assert result["status"] == "rejected"
    assert result["errorCode"] == "not_full"


def test_become_host_rejected_host_exists():
    state = lobby_with_players(4, ["p1", "p2", "p3", "p4"])
    state["hostPlayerId"] = "p2"  # host already set

    result = handle_action(state, player("p1"), {"type": "become_host"})

    assert result["status"] == "rejected"
    assert result["errorCode"] == "host_exists"


# ===================================================================
# pick_identity
# ===================================================================


def test_pick_identity_human():
    state = setup_identity_pick(4, ["p1", "p2", "p3", "p4"])
    # p1 is host, p2 is non-host

    result = handle_action(
        state, player("p2"),
        {"type": "pick_identity", "payload": {"role": "human"}},
    )

    assert result["status"] == "accepted"
    assert result["state"]["identities"]["p2"]["role"] == "human"
    assert result["state"]["identities"]["p2"].get("keyword") is None


def test_pick_identity_fake_assigns_keyword():
    state = setup_identity_pick(4, ["p1", "p2", "p3", "p4"])

    result = handle_action(
        state, player("p2"),
        {"type": "pick_identity", "payload": {"role": "fake"}},
    )

    assert result["status"] == "accepted"
    assert result["state"]["identities"]["p2"]["role"] == "fake"
    keyword = result["state"]["identities"]["p2"]["keyword"]
    assert isinstance(keyword, str)
    assert len(keyword) > 0


def test_pick_identity_rejected_wrong_phase():
    state = lobby_with_players(4, ["p1", "p2", "p3", "p4"])
    # Phase is lobby

    result = handle_action(
        state, player("p2"),
        {"type": "pick_identity", "payload": {"role": "human"}},
    )

    assert result["status"] == "rejected"
    assert result["errorCode"] == "wrong_phase"


def test_pick_identity_rejected_host():
    state = setup_identity_pick(4, ["p1", "p2", "p3", "p4"])
    # p1 is host

    result = handle_action(
        state, player("p1"),
        {"type": "pick_identity", "payload": {"role": "human"}},
    )

    assert result["status"] == "rejected"
    assert result["errorCode"] == "host_cannot_pick"


def test_pick_identity_rejected_duplicate():
    state = setup_identity_pick(4, ["p1", "p2", "p3", "p4"])
    # First pick succeeds
    state = handle_action(
        state, player("p2"),
        {"type": "pick_identity", "payload": {"role": "human"}},
    )["state"]
    # Second pick by same player is rejected
    result = handle_action(
        state, player("p2"),
        {"type": "pick_identity", "payload": {"role": "fake"}},
    )

    assert result["status"] == "rejected"
    assert result["errorCode"] == "already_picked"


def test_pick_identity_rejected_invalid_role():
    state = setup_identity_pick(4, ["p1", "p2", "p3", "p4"])

    result = handle_action(
        state, player("p2"),
        {"type": "pick_identity", "payload": {"role": "alien"}},
    )

    assert result["status"] == "rejected"
    assert result["errorCode"] == "invalid_role"


# ===================================================================
# draw_question
# ===================================================================


def test_draw_question_success():
    ids = ["p1", "p2", "p3", "p4"]
    state = setup_identity_pick(4, ids)
    # All non-host players pick identities
    for pid in ids[1:]:
        state = handle_action(
            state, player(pid),
            {"type": "pick_identity", "payload": {"role": "human"}},
        )["state"]
    # Host draws
    result = handle_action(state, player(ids[0]), {"type": "draw_question"})

    assert result["status"] == "accepted"
    assert result["state"]["phase"] == "question"
    assert isinstance(result["state"]["currentQuestion"], str)
    assert len(result["state"]["currentQuestion"]) > 0


def test_draw_question_rejected_not_all_picked():
    ids = ["p1", "p2", "p3", "p4"]
    state = setup_identity_pick(4, ids)
    # Only p2 picks, p3 and p4 have not
    state = handle_action(
        state, player("p2"),
        {"type": "pick_identity", "payload": {"role": "human"}},
    )["state"]

    result = handle_action(state, player(ids[0]), {"type": "draw_question"})

    assert result["status"] == "rejected"
    assert result["errorCode"] == "not_all_picked"


def test_draw_question_rejected_not_host():
    state = setup_identity_pick(4, ["p1", "p2", "p3", "p4"])
    # p2 is non-host, tries to draw

    result = handle_action(state, player("p2"), {"type": "draw_question"})

    assert result["status"] == "rejected"
    assert result["errorCode"] == "not_host"


# ===================================================================
# guess
# ===================================================================


def test_guess_correct():
    ids = ["p1", "p2", "p3", "p4"]
    state = setup_identity_pick(4, ids)
    # All non-host players pick human
    for pid in ids[1:]:
        state = handle_action(
            state, player(pid),
            {"type": "pick_identity", "payload": {"role": "human"}},
        )["state"]
    state = handle_action(state, player(ids[0]), {"type": "draw_question"})["state"]
    # Guess p2 as human (correct)
    result = handle_action(
        state, player(ids[0]),
        {"type": "guess", "payload": {"targetPlayerId": "p2", "guessedRole": "human"}},
    )

    assert result["status"] == "accepted"
    assert result["state"]["currentGuess"]["correct"] is True
    assert result["state"]["phase"] == "reveal"


def test_guess_wrong():
    ids = ["p1", "p2", "p3", "p4"]
    state = setup_identity_pick(4, ids)
    # p2 picks fake, others human
    state = handle_action(
        state, player("p2"),
        {"type": "pick_identity", "payload": {"role": "fake"}},
    )["state"]
    for pid in ["p3", "p4"]:
        state = handle_action(
            state, player(pid),
            {"type": "pick_identity", "payload": {"role": "human"}},
        )["state"]
    state = handle_action(state, player(ids[0]), {"type": "draw_question"})["state"]
    # Guess p2 as human (wrong)
    result = handle_action(
        state, player(ids[0]),
        {"type": "guess", "payload": {"targetPlayerId": "p2", "guessedRole": "human"}},
    )

    assert result["status"] == "accepted"
    assert result["state"]["currentGuess"]["correct"] is False


def test_guess_rejected_wrong_phase():
    state = setup_identity_pick(4, ["p1", "p2", "p3", "p4"])
    # Phase is identity_pick, not question

    result = handle_action(
        state, player("p1"),
        {"type": "guess", "payload": {"targetPlayerId": "p2", "guessedRole": "human"}},
    )

    assert result["status"] == "rejected"
    assert result["errorCode"] == "wrong_phase"


def test_guess_rejected_not_host():
    state = setup_question_phase(4, ["p1", "p2", "p3", "p4"])
    # p2 is non-host, tries to guess

    result = handle_action(
        state, player("p2"),
        {"type": "guess", "payload": {"targetPlayerId": "p3", "guessedRole": "human"}},
    )

    assert result["status"] == "rejected"
    assert result["errorCode"] == "not_host"


def test_guess_rejected_already_guessed():
    ids = ["p1", "p2", "p3", "p4"]
    state = setup_question_phase(4, ids)
    # Guess p2
    state = handle_action(
        state, player(ids[0]),
        {"type": "guess", "payload": {"targetPlayerId": "p2", "guessedRole": "human"}},
    )["state"]
    # Back to question
    state = handle_action(state, player(ids[0]), {"type": "next_player"})["state"]
    # Try to guess p2 again
    result = handle_action(
        state, player(ids[0]),
        {"type": "guess", "payload": {"targetPlayerId": "p2", "guessedRole": "fake"}},
    )

    assert result["status"] == "rejected"
    assert result["errorCode"] == "already_guessed"


def test_guess_rejected_guessing_host():
    state = setup_question_phase(4, ["p1", "p2", "p3", "p4"])
    # p1 is host, can't be guessed

    result = handle_action(
        state, player("p1"),
        {"type": "guess", "payload": {"targetPlayerId": "p1", "guessedRole": "human"}},
    )

    assert result["status"] == "rejected"
    assert result["errorCode"] == "invalid_target"


# ===================================================================
# next_player
# ===================================================================


def test_next_player_back_to_question():
    ids = ["p1", "p2", "p3", "p4"]
    state = setup_question_phase(4, ids)
    # Guess one player
    state = handle_action(
        state, player(ids[0]),
        {"type": "guess", "payload": {"targetPlayerId": "p2", "guessedRole": "human"}},
    )["state"]
    assert state["phase"] == "reveal"

    result = handle_action(state, player(ids[0]), {"type": "next_player"})

    assert result["status"] == "accepted"
    assert result["state"]["phase"] == "question"
    assert result["state"]["currentGuess"] is None


def test_next_player_all_guessed_resets():
    ids = ["p1", "p2", "p3", "p4"]
    state = setup_question_phase(4, ids)
    # Guess all non-host players
    for target in ids[1:]:
        state = handle_action(
            state, player(ids[0]),
            {"type": "guess", "payload": {"targetPlayerId": target, "guessedRole": "human"}},
        )["state"]
        # Don't do next_player after the last guess
        if target != ids[-1]:
            state = handle_action(state, player(ids[0]), {"type": "next_player"})["state"]

    # All guessed, next_player should reset to lobby
    result = handle_action(state, player(ids[0]), {"type": "next_player"})

    assert result["status"] == "accepted"
    new_state = result["state"]
    assert new_state["phase"] == "lobby"
    assert new_state["hostPlayerId"] is None
    assert new_state["identities"] == {}
    assert new_state["guessedPlayerIds"] == []
    # Players and capacity preserved
    assert "p1" in new_state["playerIds"]
    assert "p2" in new_state["playerIds"]
    assert "p1" in new_state["playerInfo"]
    assert new_state["capacity"] == 4


# ===================================================================
# end_game
# ===================================================================


def test_end_game_resets_to_lobby():
    state = setup_identity_pick(4, ["p1", "p2", "p3", "p4"])
    # Host ends game from identity_pick phase
    result = handle_action(state, player("p1"), {"type": "end_game"})

    assert result["status"] == "accepted"
    new_state = result["state"]
    assert new_state["phase"] == "lobby"
    assert new_state["hostPlayerId"] is None
    assert new_state["identities"] == {}
    # Players and capacity preserved
    assert "p1" in new_state["playerIds"]
    assert "p2" in new_state["playerIds"]
    assert new_state["capacity"] == 4


def test_end_game_rejected_not_host():
    state = setup_identity_pick(4, ["p1", "p2", "p3", "p4"])
    # p2 is non-host
    result = handle_action(state, player("p2"), {"type": "end_game"})

    assert result["status"] == "rejected"
    assert result["errorCode"] == "not_host"


# ===================================================================
# get_state_snapshot
# ===================================================================


def test_snapshot_player_sees_own_identity():
    state = setup_identity_pick(4, ["p1", "p2", "p3", "p4"])
    # p2 picks identity
    state = handle_action(
        state, player("p2"),
        {"type": "pick_identity", "payload": {"role": "human"}},
    )["state"]

    snapshot = get_state_snapshot(state, player("p2"))

    assert snapshot["myIdentity"] == {"role": "human"}


def test_snapshot_other_player_sees_null():
    state = setup_identity_pick(4, ["p1", "p2", "p3", "p4"])
    # p2 picks identity, p3 has not
    state = handle_action(
        state, player("p2"),
        {"type": "pick_identity", "payload": {"role": "human"}},
    )["state"]
    # p3 views the snapshot
    snapshot = get_state_snapshot(state, player("p3"))

    assert snapshot["myIdentity"] is None


def test_snapshot_host_sees_all_identities():
    ids = ["p1", "p2", "p3", "p4"]
    state = setup_identity_pick(4, ids)
    for pid in ids[1:]:
        state = handle_action(
            state, player(pid),
            {"type": "pick_identity", "payload": {"role": "human"}},
        )["state"]
    # Host (p1) views snapshot
    snapshot = get_state_snapshot(state, player("p1"))

    assert snapshot["allIdentities"] is not None
    assert "p2" in snapshot["allIdentities"]
    assert snapshot["allIdentities"]["p2"]["role"] == "human"


def test_snapshot_non_host_no_all_identities():
    ids = ["p1", "p2", "p3", "p4"]
    state = setup_identity_pick(4, ids)
    for pid in ids[1:]:
        state = handle_action(
            state, player(pid),
            {"type": "pick_identity", "payload": {"role": "human"}},
        )["state"]
    # Non-host (p2) views snapshot
    snapshot = get_state_snapshot(state, player("p2"))

    assert snapshot["allIdentities"] is None


def test_snapshot_reveal_has_guess_info():
    ids = ["p1", "p2", "p3", "p4"]
    state = setup_identity_pick(4, ids)
    # p2 is fake
    state = handle_action(
        state, player("p2"),
        {"type": "pick_identity", "payload": {"role": "fake"}},
    )["state"]
    # p3, p4 are human
    for pid in ["p3", "p4"]:
        state = handle_action(
            state, player(pid),
            {"type": "pick_identity", "payload": {"role": "human"}},
        )["state"]
    state = handle_action(state, player(ids[0]), {"type": "draw_question"})["state"]
    # Guess p2 as human (wrong)
    state = handle_action(
        state, player(ids[0]),
        {"type": "guess", "payload": {"targetPlayerId": "p2", "guessedRole": "human"}},
    )["state"]

    snapshot = get_state_snapshot(state, player(ids[0]))

    assert snapshot["currentGuess"] is not None
    assert snapshot["currentGuess"]["targetPlayerId"] == "p2"
    assert snapshot["currentGuess"]["guessedRole"] == "human"
    assert snapshot["currentGuess"]["correct"] is False
    assert snapshot["currentGuess"]["actualRole"] == "fake"
    assert "keyword" in snapshot["currentGuess"]


# ===================================================================
# Unknown action
# ===================================================================


def test_unknown_action_rejected():
    state = fresh_lobby(4)

    result = handle_action(state, player("p1"), {"type": "nonexistent_action"})

    assert result["status"] == "rejected"
    assert result["errorCode"] == "unknown_action"
