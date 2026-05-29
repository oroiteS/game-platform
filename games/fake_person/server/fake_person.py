import random

from games.fake_person.shared import KEYWORDS, QUESTIONS


def game_result(status, state, error_code=None):
    return {
        "status": status,
        "state": state,
        "errorCode": error_code,
        "publicEvents": [],
        "privateEvents": [],
    }


def _fresh_state():
    return {
        "phase": "lobby",
        "hostPlayerId": None,
        "readyPlayerIds": [],
        "identities": {},
        "currentQuestion": None,
        "currentGuess": None,
        "guessedPlayerIds": [],
        "playerIds": [],
        "playerInfo": {},
        "capacity": 0,
    }


def _reset_to_lobby(state):
    """Reset game state but keep playerIds, playerInfo, capacity."""
    return {
        "phase": "lobby",
        "hostPlayerId": None,
        "readyPlayerIds": [],
        "identities": {},
        "currentQuestion": None,
        "currentGuess": None,
        "guessedPlayerIds": [],
        "playerIds": list(state.get("playerIds", [])),
        "playerInfo": dict(state.get("playerInfo", {})),
        "capacity": state.get("capacity", 0),
    }


def create_initial_state(room_context):
    state = _fresh_state()
    state["capacity"] = room_context.get("capacity", 0)
    return state


def on_player_join(state, player):
    pid = player["playerId"]
    if pid not in state["playerIds"]:
        state["playerIds"].append(pid)
    nickname = player.get("nickname", "")
    state["playerInfo"][pid] = {"nickname": nickname}
    return game_result("accepted", state)


def on_player_disconnect(state, player):
    return game_result("accepted", state)


def on_player_reconnect(state, player):
    return game_result("accepted", state)


def on_player_leave(state, player):
    pid = player["playerId"]
    was_host = state.get("hostPlayerId") == pid

    # Remove pid from all state collections
    try:
        state["playerIds"].remove(pid)
    except ValueError:
        pass
    state["playerInfo"].pop(pid, None)
    state["identities"].pop(pid, None)
    try:
        state["readyPlayerIds"].remove(pid)
    except ValueError:
        pass
    try:
        state["guessedPlayerIds"].remove(pid)
    except ValueError:
        pass

    if was_host:
        result_state = _reset_to_lobby(state)
        return game_result("accepted", result_state)

    return game_result("accepted", state)


def _get_non_host_players(state):
    host = state.get("hostPlayerId")
    return [p for p in state.get("playerIds", []) if p != host]


def handle_action(state, player, action):
    action_type = action.get("type")
    pid = player["playerId"]
    phase = state.get("phase")
    host_id = state.get("hostPlayerId")

    # ---- toggle_ready ----
    if action_type == "toggle_ready":
        if phase != "lobby":
            return game_result("rejected", state, "wrong_phase")
        if pid == host_id:
            return game_result("rejected", state, "host_cannot_ready")
        ready_ids = state.setdefault("readyPlayerIds", [])
        if pid in ready_ids:
            ready_ids.remove(pid)
        else:
            ready_ids.append(pid)
        return game_result("accepted", state)

    # ---- become_host ----
    if action_type == "become_host":
        if phase != "lobby":
            return game_result("rejected", state, "wrong_phase")
        if host_id is not None:
            return game_result("rejected", state, "host_exists")
        player_ids = state.get("playerIds", [])
        ready_ids = state.get("readyPlayerIds", [])
        if len(player_ids) != state.get("capacity", 0):
            return game_result("rejected", state, "not_full")
        if not all(p in ready_ids for p in player_ids):
            return game_result("rejected", state, "not_all_ready")
        state["hostPlayerId"] = pid
        state["readyPlayerIds"] = []
        state["phase"] = "identity_pick"
        return game_result("accepted", state)

    # ---- pick_identity ----
    if action_type == "pick_identity":
        if phase != "identity_pick":
            return game_result("rejected", state, "wrong_phase")
        if pid == host_id:
            return game_result("rejected", state, "host_cannot_pick")
        if pid in state.get("identities", {}):
            return game_result("rejected", state, "already_picked")
        payload = action.get("payload") or {}
        role = payload.get("role")
        if role not in ("human", "fake"):
            return game_result("rejected", state, "invalid_role")
        identity = {"role": role}
        if role == "fake":
            used_keywords = set()
            for ident in state["identities"].values():
                kw = ident.get("keyword")
                if kw:
                    used_keywords.add(kw)
            available = [k for k in KEYWORDS if k not in used_keywords]
            if not available:
                return game_result("rejected", state, "no_keywords_left")
            identity["keyword"] = random.choice(available)
        state.setdefault("identities", {})[pid] = identity
        return game_result("accepted", state)

    # ---- draw_question ----
    if action_type == "draw_question":
        if phase != "identity_pick":
            return game_result("rejected", state, "wrong_phase")
        if pid != host_id:
            return game_result("rejected", state, "not_host")
        non_hosts = _get_non_host_players(state)
        identities = state.get("identities", {})
        if not all(p in identities for p in non_hosts):
            return game_result("rejected", state, "not_all_picked")
        question = random.choice(QUESTIONS)
        state["currentQuestion"] = question
        state["phase"] = "question"
        return game_result("accepted", state)

    # ---- guess ----
    if action_type == "guess":
        if phase != "question":
            return game_result("rejected", state, "wrong_phase")
        if pid != host_id:
            return game_result("rejected", state, "not_host")
        payload = action.get("payload") or {}
        target_pid = payload.get("targetPlayerId")
        guessed_role = payload.get("guessedRole")
        if not target_pid or not guessed_role:
            return game_result("rejected", state, "invalid_payload")
        non_hosts = _get_non_host_players(state)
        if target_pid not in non_hosts:
            return game_result("rejected", state, "invalid_target")
        if target_pid in state.get("guessedPlayerIds", []):
            return game_result("rejected", state, "already_guessed")
        target_identity = state.get("identities", {}).get(target_pid)
        if not target_identity:
            return game_result("rejected", state, "target_no_identity")
        if guessed_role not in ("human", "fake"):
            return game_result("rejected", state, "invalid_role")
        correct = guessed_role == target_identity["role"]
        state["currentGuess"] = {
            "targetPlayerId": target_pid,
            "guessedRole": guessed_role,
            "correct": correct,
        }
        state.setdefault("guessedPlayerIds", []).append(target_pid)
        state["phase"] = "reveal"
        return game_result("accepted", state)

    # ---- next_player ----
    if action_type == "next_player":
        if phase != "reveal":
            return game_result("rejected", state, "wrong_phase")
        if pid != host_id:
            return game_result("rejected", state, "not_host")
        state["currentGuess"] = None
        non_hosts = _get_non_host_players(state)
        guessed = state.get("guessedPlayerIds", [])
        if any(p not in guessed for p in non_hosts):
            state["phase"] = "question"
        else:
            result_state = _reset_to_lobby(state)
            return game_result("accepted", result_state)
        return game_result("accepted", state)

    # ---- end_game ----
    if action_type == "end_game":
        if pid != host_id:
            return game_result("rejected", state, "not_host")
        result_state = _reset_to_lobby(state)
        return game_result("accepted", result_state)

    # ---- unknown action ----
    return game_result("rejected", state, "unknown_action")


def get_state_snapshot(state, viewer):
    viewer_id = viewer.get("playerId")
    host_id = state.get("hostPlayerId")
    is_host = viewer_id == host_id
    non_hosts = _get_non_host_players(state)

    # Build players list
    players = []
    for p in state.get("playerIds", []):
        info = state.get("playerInfo", {}).get(p, {})
        players.append({
            "playerId": p,
            "nickname": info.get("nickname", ""),
            "isHost": p == host_id,
            "ready": p in state.get("readyPlayerIds", []),
        })

    # My identity
    my_identity = state.get("identities", {}).get(viewer_id)
    if my_identity is not None:
        my_identity = dict(my_identity)

    # Current guess (augmented with target's actual identity)
    current_guess = state.get("currentGuess")
    if current_guess is not None:
        target_pid = current_guess.get("targetPlayerId")
        target_identity = state.get("identities", {}).get(target_pid, {})
        current_guess = {
            "targetPlayerId": current_guess.get("targetPlayerId"),
            "guessedRole": current_guess.get("guessedRole"),
            "correct": current_guess.get("correct"),
            "actualRole": target_identity.get("role"),
            "keyword": target_identity.get("keyword"),
        }

    snapshot = {
        "phase": state.get("phase"),
        "hostPlayerId": host_id,
        "readyPlayerIds": list(state.get("readyPlayerIds", [])),
        "currentQuestion": state.get("currentQuestion"),
        "guessedPlayerIds": list(state.get("guessedPlayerIds", [])),
        "players": players,
        "myIdentity": my_identity,
        "currentGuess": current_guess,
        "allIdentities": dict(state.get("identities", {})) if is_host else None,
    }
    return snapshot
