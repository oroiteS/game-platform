import random
from games.beauty_vote.server.constants import (
    INITIAL_SCORE, MAX_ROUNDS, CONSECUTIVE_NO_ELIMINATION_LIMIT,
)
from games.beauty_vote.server.rules import (
    initial_rule_pool, empty_active_rules, check_unlock, unlock_rule,
    apply_round_20, rule_names_for_display,
)
from games.beauty_vote.server.events import (
    roll_special_event, apply_number_storm, apply_score_reset,
    apply_lucky_exemption,
)
from games.beauty_vote.server.settlement import (
    calculate_T, apply_win_loss_alt, find_extreme_duplicates,
    determine_winners_furthest, settle_round,
)


def game_result(status, state, error_code=None):
    return {
        "status": status,
        "state": state,
        "errorCode": error_code,
        "publicEvents": [],
        "privateEvents": [],
    }


def _fresh_state(capacity=0):
    return {
        "phase": "lobby",
        "round": 0,
        "players": {},
        "playerIds": [],
        "readyPlayerIds": [],
        "capacity": capacity,
        "current_T": None,
        "last_T": None,
        "forbidden_number": None,
        "total_eliminations": 0,
        "consecutive_no_elimination": 0,
        "active_rules": empty_active_rules(),
        "rule_pool": initial_rule_pool(),
        "special_event": None,
        "winner_ids": [],
        "furthest_ids": [],
        "rule_log": [],
        "round_log": [],
        "calculation": None,
        "has_hidden_rule": False,
        "_last_unlock_at_eliminations": 0,
        "_submissions": {},
        "_all_time_submissions": {},
    }


def create_initial_state(room_context):
    state = _fresh_state()
    state["capacity"] = room_context.get("capacity", 0)
    return state


def on_player_join(state, player):
    pid = player["playerId"]
    if pid not in state["playerIds"]:
        state["playerIds"].append(pid)
        state["players"][pid] = {
            "nickname": player.get("nickname", ""),
            "score": INITIAL_SCORE,
            "alive": True,
            "last_number": None,
        }
    return game_result("accepted", state)


def on_player_disconnect(state, player):
    return game_result("accepted", state)


def on_player_reconnect(state, player):
    return game_result("accepted", state)


def on_player_leave(state, player):
    pid = player["playerId"]
    try:
        state["playerIds"].remove(pid)
    except ValueError:
        pass
    state["players"].pop(pid, None)
    try:
        state["readyPlayerIds"].remove(pid)
    except ValueError:
        pass
    return game_result("accepted", state)


def handle_action(state, player, action):
    action_type = action.get("type")
    pid = player["playerId"]
    phase = state.get("phase")

    if action_type == "toggle_ready":
        if phase != "lobby":
            return game_result("rejected", state, "wrong_phase")
        ready_ids = state["readyPlayerIds"]
        if pid in ready_ids:
            ready_ids.remove(pid)
        else:
            ready_ids.append(pid)
        capacity = state["capacity"]
        alive_count = len([p for p in state["playerIds"]
                          if state["players"].get(p, {}).get("alive", True)])
        ready_count = len(ready_ids)
        if alive_count == capacity and ready_count == capacity:
            return _start_game(state)
        return game_result("accepted", state)

    if action_type == "submit_number":
        if phase != "submit":
            return game_result("rejected", state, "wrong_phase")
        if pid not in state["playerIds"] or not state["players"].get(pid, {}).get("alive"):
            return game_result("rejected", state, "player_not_alive")
        if pid in state["_submissions"]:
            return game_result("rejected", state, "already_submitted")
        return _handle_submission(state, pid, action.get("payload", {}))

    if action_type == "next_round":
        if phase != "reveal":
            return game_result("rejected", state, "wrong_phase")
        _transition_to_next_round(state)
        return game_result("accepted", state)

    return game_result("rejected", state, "unknown_action")


def _start_game(state):
    state["phase"] = "submit"
    state["round"] = 1
    state["readyPlayerIds"] = []
    state["_submissions"] = {}
    state["special_event"] = roll_special_event()
    rule_id, replaced_id, msg = check_unlock(state)
    if rule_id is not None:
        state["rule_log"].append({
            "unlocked": rule_id, "replaced": replaced_id,
            "message": msg, "round": 0,
        })
    return game_result("accepted", state)


def _handle_submission(state, pid, payload):
    number = payload.get("number")
    if not isinstance(number, int) or number < 0 or number > 100:
        return game_result("rejected", state, "invalid_number")
    if state["round"] == 1 and number in (0, 100):
        return game_result("rejected", state, "first_round_restriction")

    sub = {
        "number": number,
        "use_leverage": bool(payload.get("use_leverage")),
        "reverse_number": payload.get("reverse_number"),
        "betray_target": payload.get("betray_target"),
    }
    state["_submissions"][pid] = sub

    alive_pids = [p for p in state["playerIds"]
                  if state["players"].get(p, {}).get("alive", True)]
    if all(p in state["_submissions"] for p in alive_pids):
        return _end_round(state)

    return game_result("accepted", state)


def _track_eliminations(state, eliminated_numbers):
    """Update elimination tracking after a round. Call ONCE per round."""
    if eliminated_numbers:
        state["total_eliminations"] += len(eliminated_numbers)
        state["consecutive_no_elimination"] = 0
    else:
        state["consecutive_no_elimination"] += 1


def _end_round(state):
    submissions = dict(state["_submissions"])
    state["_submissions"] = {}
    state["phase"] = "reveal"

    round_num = state["round"]

    # Apply special event: number storm (modifies submissions in place)
    special_event = state.get("special_event")
    if special_event and special_event["type"] == "number_storm":
        submissions = apply_number_storm(submissions)

    # Apply special event: score reset
    if special_event and special_event["type"] == "score_reset":
        apply_score_reset(state)

    # Save storm-modified numbers for history and last_number
    state["_all_time_submissions"][str(round_num)] = {
        pid: sub["number"] for pid, sub in submissions.items()
    }

    for pid, sub in submissions.items():
        if pid in state["players"]:
            state["players"][pid]["last_number"] = sub["number"]

    # Check all-same
    if find_extreme_duplicates(submissions):
        _all_same_settlement(state, submissions)
        return game_result("accepted", state)

    # Calculate T
    if state.get("has_hidden_rule"):
        T, T2, method, label, detail = 0, None, "hidden", "隐藏规则", ""
    else:
        T, T2, method, label, detail = calculate_T(state, submissions)
    state["current_T"] = T
    state["calculation"] = {"method": method, "label": label, "detail": detail}

    # Win/loss alternative
    winloss_triggered, wl_winners, wl_penalized, wl_method, wl_detail = apply_win_loss_alt(
        state, submissions)

    if winloss_triggered:
        winners = wl_winners
        furthest = []
        state["calculation"] = {"method": wl_method, "label": label, "detail": wl_detail}
    else:
        winners, furthest, det_method, det_detail = determine_winners_furthest(
            submissions, T, T2, state)
        state["calculation"]["detail"] += f" | {det_detail}"

    state["winner_ids"] = winners
    state["furthest_ids"] = furthest

    # Apply lucky exemption (pick random player before settlement)
    if special_event and special_event["type"] == "lucky_exemption":
        apply_lucky_exemption(state, special_event)

    # Settlement pipeline
    betray_results = {}
    deltas = settle_round(
        state, submissions, winners, furthest, T,
        winloss_triggered, special_event, betray_results,
    )

    # Mirror punishment specific: penalized players -1
    if winloss_triggered and state["active_rules"]["win_loss_alt"] == 1:
        for penalized_pid in wl_penalized:
            if penalized_pid in deltas:
                deltas[penalized_pid] = -1

    # Apply score changes
    eliminated_this_round = []
    eliminated_numbers = []
    for pid, delta in deltas.items():
        if pid in state["players"]:
            state["players"][pid]["score"] += delta
            if state["players"][pid]["score"] <= 0:
                state["players"][pid]["alive"] = False
                eliminated_this_round.append(pid)
                eliminated_numbers.append(
                    submissions[pid]["number"] if pid in submissions else None
                )

    # Update elimination tracking
    _track_eliminations(state, eliminated_numbers)

    # Forced unlock: 3 consecutive no-elimination rounds
    if (state["consecutive_no_elimination"] >= CONSECUTIVE_NO_ELIMINATION_LIMIT
            and state["rule_pool"]):
        rule_id, replaced_id, msg = unlock_rule(state)
        if rule_id is not None:
            state["rule_log"].append({
                "unlocked": rule_id, "replaced": replaced_id,
                "message": msg, "round": state["round"],
            })
            state["consecutive_no_elimination"] = 0

    # Set forbidden number for next round (Rule 4)
    if 4 in state["active_rules"]["independent"]:
        state["forbidden_number"] = round(T)

    state["last_T"] = T

    state["round_log"].append({
        "round": state["round"],
        "T": T,
        "winners": winners,
        "furthest": furthest,
        "eliminated": eliminated_this_round,
        "deltas": deltas,
    })

    return game_result("accepted", state)


def _all_same_settlement(state, submissions):
    """All players chose same number: no winner, all -2."""
    eliminated_numbers = []
    for pid in submissions:
        if pid in state["players"]:
            state["players"][pid]["score"] -= 2
            if state["players"][pid]["score"] <= 0:
                state["players"][pid]["alive"] = False
                eliminated_numbers.append(
                    submissions[pid]["number"] if pid in submissions else None
                )
    # Update elimination tracking
    _track_eliminations(state, eliminated_numbers)
    state["winner_ids"] = []
    state["furthest_ids"] = []
    state["calculation"] = {
        "method": "all_same",
        "label": "全体相同",
        "detail": "所有玩家选择相同数字，无人获胜，全体扣2分",
    }


def _transition_to_next_round(state):
    alive_pids = [p for p in state["playerIds"]
                  if state["players"].get(p, {}).get("alive", True)]
    if len(alive_pids) <= 1:
        state["phase"] = "ended"
        return

    # Round 20 hidden rule check
    if state["round"] >= MAX_ROUNDS and not state.get("has_hidden_rule"):
        apply_round_20(state)
        state["round_log"].append({
            "round": state["round"],
            "message": "隐藏规则已激活",
        })

    state["round"] += 1
    state["phase"] = "submit"
    state["_submissions"] = {}
    state["special_event"] = roll_special_event()
    state["winner_ids"] = []
    state["furthest_ids"] = []

    # Check rule unlock
    rule_id, replaced_id, msg = check_unlock(state)
    if rule_id is not None:
        state["rule_log"].append({
            "unlocked": rule_id, "replaced": replaced_id,
            "message": msg, "round": state["round"],
        })


def get_state_snapshot(state, viewer):
    viewer_id = viewer.get("playerId")

    players = []
    for pid in state["playerIds"]:
        pdata = state["players"].get(pid)
        if not pdata:
            continue
        entry = {
            "playerId": pid,
            "nickname": pdata["nickname"],
            "score": pdata["score"],
            "alive": pdata.get("alive", True),
        }
        if state["phase"] in ("reveal", "ended"):
            entry["lastNumber"] = pdata.get("last_number")
        players.append(entry)

    my_submission = None
    if viewer_id in state.get("_submissions", {}):
        my_submission = state["_submissions"][viewer_id]

    all_submissions = None
    if state["phase"] == "ended":
        all_submissions = state.get("_all_time_submissions")

    rules_display = None
    if state.get("has_hidden_rule"):
        rules_display = [{"id": 0, "name": "隐藏规则", "description": ""}]
    else:
        rules_display = rule_names_for_display(state)

    snapshot = {
        "phase": state["phase"],
        "round": state["round"],
        "players": players,
        "readyPlayerIds": state.get("readyPlayerIds", []),
        "capacity": state["capacity"],
        "currentT": state.get("current_T"),
        "lastT": state.get("last_T"),
        "forbiddenNumber": state.get("forbidden_number"),
        "activeRules": state["active_rules"],
        "rulesDisplay": rules_display,
        "specialEvent": state.get("special_event"),
        "winnerIds": state.get("winner_ids", []),
        "furthestIds": state.get("furthest_ids", []),
        "ruleLog": state.get("rule_log", []),
        "roundLog": state.get("round_log"),
        "calculation": state.get("calculation"),
        "hasHiddenRule": state.get("has_hidden_rule", False),
        "mySubmission": my_submission,
        "allSubmissions": all_submissions,
        "totalEliminations": state.get("total_eliminations", 0),
    }
    return snapshot
