import pytest
from unittest.mock import patch

from games.beauty_vote.server.engine import (
    create_initial_state, on_player_join, handle_action,
    get_state_snapshot, on_player_leave,
)


def make_player(pid, nickname="Test"):
    return {"playerId": pid, "nickname": nickname}


def _auto_start_2p(state):
    """Helper: join 2 players and ready both to auto-start."""
    on_player_join(state, make_player("p1", "Alice"))
    on_player_join(state, make_player("p2", "Bob"))
    handle_action(state, make_player("p1"), {"type": "toggle_ready"})
    handle_action(state, make_player("p2"), {"type": "toggle_ready"})


# ---------------------------------------------------------------------------
# Patch roll_special_event to return None so all tests are deterministic.
# When a number_storm fires it randomly adjusts submitted numbers by +-5,
# which breaks any test that checks for an exact T value or exact scores.
# ---------------------------------------------------------------------------
ENGINE_EVENTS_PATH = "games.beauty_vote.server.engine.roll_special_event"


class TestInitialState:
    @patch(ENGINE_EVENTS_PATH, return_value=None)
    def test_create_initial_state(self, _mock):
        state = create_initial_state({"roomCode": "123456", "gameId": "beauty-vote", "capacity": 4})
        assert state["phase"] == "lobby"
        assert state["capacity"] == 4
        assert state["round"] == 0
        assert len(state["rule_pool"]) == 9
        assert state["active_rules"] == {"independent": [], "target_value": None, "win_loss_alt": None}

    def test_all_rules_in_initial_pool(self):
        state = create_initial_state({"capacity": 4})
        assert set(state["rule_pool"]) == {1, 2, 3, 4, 5, 6, 8, 9, 10}


class TestPlayerJoin:
    def test_player_join_adds_to_state(self):
        state = create_initial_state({"capacity": 4})
        result = on_player_join(state, make_player("p1", "Alice"))
        assert result["status"] == "accepted"
        assert "p1" in state["playerIds"]
        assert state["players"]["p1"]["score"] == 15
        assert state["players"]["p1"]["alive"] is True
        assert state["players"]["p1"]["nickname"] == "Alice"

    def test_duplicate_join_does_not_duplicate(self):
        state = create_initial_state({"capacity": 4})
        on_player_join(state, make_player("p1", "Alice"))
        on_player_join(state, make_player("p1", "AliceAgain"))
        assert state["playerIds"].count("p1") == 1


class TestLobbyAutoStart:
    @patch(ENGINE_EVENTS_PATH, return_value=None)
    def test_auto_start_when_all_ready(self, _mock):
        state = create_initial_state({"capacity": 2})
        on_player_join(state, make_player("p1", "Alice"))
        on_player_join(state, make_player("p2", "Bob"))
        r = handle_action(state, make_player("p1"), {"type": "toggle_ready"})
        assert state["phase"] == "lobby"
        r = handle_action(state, make_player("p2"), {"type": "toggle_ready"})
        assert state["phase"] == "submit"
        assert state["round"] == 1

    @patch(ENGINE_EVENTS_PATH, return_value=None)
    def test_toggle_ready_wrong_phase(self, _mock):
        state = create_initial_state({"capacity": 2})
        _auto_start_2p(state)
        r = handle_action(state, make_player("p1"), {"type": "toggle_ready"})
        assert r["status"] == "rejected"
        assert r["errorCode"] == "wrong_phase"


class TestSubmitNumber:
    @patch(ENGINE_EVENTS_PATH, return_value=None)
    def test_submit_number_success(self, _mock):
        state = create_initial_state({"capacity": 2})
        _auto_start_2p(state)
        r = handle_action(state, make_player("p1"), {
            "type": "submit_number", "payload": {"number": 42},
        })
        assert r["status"] == "accepted"

    @patch(ENGINE_EVENTS_PATH, return_value=None)
    def test_first_round_rejects_0(self, _mock):
        state = create_initial_state({"capacity": 2})
        _auto_start_2p(state)
        r = handle_action(state, make_player("p1"), {
            "type": "submit_number", "payload": {"number": 0},
        })
        assert r["status"] == "rejected"
        assert r["errorCode"] == "first_round_restriction"

    @patch(ENGINE_EVENTS_PATH, return_value=None)
    def test_first_round_rejects_100(self, _mock):
        state = create_initial_state({"capacity": 2})
        _auto_start_2p(state)
        r = handle_action(state, make_player("p1"), {
            "type": "submit_number", "payload": {"number": 100},
        })
        assert r["status"] == "rejected"

    @patch(ENGINE_EVENTS_PATH, return_value=None)
    def test_invalid_number_range(self, _mock):
        state = create_initial_state({"capacity": 2})
        _auto_start_2p(state)
        r = handle_action(state, make_player("p1"), {
            "type": "submit_number", "payload": {"number": 101},
        })
        assert r["status"] == "rejected"

    @patch(ENGINE_EVENTS_PATH, return_value=None)
    def test_duplicate_submission_rejected(self, _mock):
        state = create_initial_state({"capacity": 2})
        _auto_start_2p(state)
        handle_action(state, make_player("p1"), {
            "type": "submit_number", "payload": {"number": 42},
        })
        r = handle_action(state, make_player("p1"), {
            "type": "submit_number", "payload": {"number": 50},
        })
        assert r["status"] == "rejected"
        assert r["errorCode"] == "already_submitted"

    def test_submit_wrong_phase(self):
        state = create_initial_state({"capacity": 2})
        r = handle_action(state, make_player("p1"), {
            "type": "submit_number", "payload": {"number": 42},
        })
        assert r["status"] == "rejected"
        assert r["errorCode"] == "wrong_phase"


class TestRoundFlow:
    @patch(ENGINE_EVENTS_PATH, return_value=None)
    def test_all_submitted_ends_round_to_reveal(self, _mock):
        state = create_initial_state({"capacity": 2})
        _auto_start_2p(state)
        handle_action(state, make_player("p1"), {
            "type": "submit_number", "payload": {"number": 20},
        })
        r = handle_action(state, make_player("p2"), {
            "type": "submit_number", "payload": {"number": 80},
        })
        assert state["phase"] == "reveal"

    @patch(ENGINE_EVENTS_PATH, return_value=None)
    def test_next_round_transitions_to_submit(self, _mock):
        state = create_initial_state({"capacity": 2})
        _auto_start_2p(state)
        handle_action(state, make_player("p1"), {"type": "submit_number", "payload": {"number": 20}})
        handle_action(state, make_player("p2"), {"type": "submit_number", "payload": {"number": 80}})
        r = handle_action(state, make_player("p1"), {"type": "next_round"})
        assert r["status"] == "accepted"
        assert state["phase"] == "submit"
        assert state["round"] == 2


class TestTCalculation:
    @patch(ENGINE_EVENTS_PATH, return_value=None)
    def test_basic_T(self, _mock):
        state = create_initial_state({"capacity": 2})
        _auto_start_2p(state)
        handle_action(state, make_player("p1"), {"type": "submit_number", "payload": {"number": 20}})
        handle_action(state, make_player("p2"), {"type": "submit_number", "payload": {"number": 80}})
        # mean = 50, T = 0.8 * 50 = 40.0
        assert state["current_T"] == 40.0

    @patch(ENGINE_EVENTS_PATH, return_value=None)
    def test_winner_determination(self, _mock):
        state = create_initial_state({"capacity": 3})
        for pid in ["p1", "p2", "p3"]:
            on_player_join(state, make_player(pid, pid))
            handle_action(state, make_player(pid), {"type": "toggle_ready"})
        # p1=40, p2=42, p3=80 -> mean=54, T=43.2 -> p2 closest (|42-43.2|=1.2)
        handle_action(state, make_player("p1"), {"type": "submit_number", "payload": {"number": 40}})
        handle_action(state, make_player("p2"), {"type": "submit_number", "payload": {"number": 42}})
        handle_action(state, make_player("p3"), {"type": "submit_number", "payload": {"number": 80}})
        assert "p2" in state["winner_ids"]


class TestAllSame:
    @patch(ENGINE_EVENTS_PATH, return_value=None)
    def test_all_same_triggers_penalty(self, _mock):
        state = create_initial_state({"capacity": 2})
        _auto_start_2p(state)
        handle_action(state, make_player("p1"), {"type": "submit_number", "payload": {"number": 50}})
        handle_action(state, make_player("p2"), {"type": "submit_number", "payload": {"number": 50}})
        assert state["players"]["p1"]["score"] == 13  # 15 - 2
        assert state["players"]["p2"]["score"] == 13
        assert state["winner_ids"] == []


class TestElimination:
    @patch(ENGINE_EVENTS_PATH, return_value=None)
    def test_score_zero_eliminates(self, _mock):
        state = create_initial_state({"capacity": 2})
        _auto_start_2p(state)
        state["players"]["p1"]["score"] = 1
        state["players"]["p2"]["score"] = 1
        handle_action(state, make_player("p1"), {"type": "submit_number", "payload": {"number": 50}})
        handle_action(state, make_player("p2"), {"type": "submit_number", "payload": {"number": 50}})
        # all-same: both -2 -> score = -1 -> eliminated
        assert state["players"]["p1"]["alive"] is False
        assert state["players"]["p2"]["alive"] is False
        assert state["total_eliminations"] == 2


class TestSnapshot:
    @patch(ENGINE_EVENTS_PATH, return_value=None)
    def test_snapshot_hides_other_submissions(self, _mock):
        state = create_initial_state({"capacity": 3})
        for pid in ["p1", "p2", "p3"]:
            on_player_join(state, make_player(pid, pid))
            handle_action(state, make_player(pid), {"type": "toggle_ready"})
        handle_action(state, make_player("p1"), {"type": "submit_number", "payload": {"number": 42}})
        snap = get_state_snapshot(state, {"playerId": "p2"})
        assert snap["phase"] == "submit"
        assert snap["mySubmission"] is None

    @patch(ENGINE_EVENTS_PATH, return_value=None)
    def test_snapshot_shows_my_submission(self, _mock):
        state = create_initial_state({"capacity": 3})
        for pid in ["p1", "p2", "p3"]:
            on_player_join(state, make_player(pid, pid))
            handle_action(state, make_player(pid), {"type": "toggle_ready"})
        handle_action(state, make_player("p1"), {"type": "submit_number", "payload": {"number": 42}})
        snap = get_state_snapshot(state, {"playerId": "p1"})
        assert snap["mySubmission"] is not None
        assert snap["mySubmission"]["number"] == 42

    @patch(ENGINE_EVENTS_PATH, return_value=None)
    def test_snapshot_hides_lastnumber_during_submit(self, _mock):
        state = create_initial_state({"capacity": 2})
        _auto_start_2p(state)
        snap = get_state_snapshot(state, {"playerId": "p1"})
        for p in snap["players"]:
            assert "lastNumber" not in p


class TestPlayerLeave:
    def test_player_leave_removes_from_state(self):
        state = create_initial_state({"capacity": 4})
        on_player_join(state, make_player("p1", "Alice"))
        on_player_join(state, make_player("p2", "Bob"))
        r = on_player_leave(state, make_player("p1"))
        assert r["status"] == "accepted"
        assert "p1" not in state["playerIds"]
        assert "p1" not in state["players"]
