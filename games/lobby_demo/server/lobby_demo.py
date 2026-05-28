MAX_MESSAGE_LENGTH = 80


def game_result(status, state, error_code=None):
    return {
        "status": status,
        "state": state,
        "errorCode": error_code,
        "publicEvents": [],
        "privateEvents": [],
    }


def create_initial_state(room_context):
    return {"messages": [], "players": {}}


def on_player_join(state, player):
    state["players"][player["playerId"]] = {
        "playerId": player["playerId"],
        "nickname": player.get("nickname", ""),
        "connected": player.get("connected", True),
    }
    return game_result("accepted", state)


def on_player_disconnect(state, player):
    existing_player = state["players"].get(player["playerId"])
    if existing_player is not None:
        existing_player["connected"] = False
    return game_result("accepted", state)


def on_player_reconnect(state, player):
    existing_player = state["players"].get(player["playerId"])
    if existing_player is not None:
        existing_player["connected"] = True
    return game_result("accepted", state)


def on_player_leave(state, player):
    state["players"].pop(player["playerId"], None)
    return game_result("accepted", state)


def handle_action(state, player, action):
    if action.get("type") != "set_message":
        return game_result("rejected", state, "unknown_action")

    payload = action.get("payload") or {}
    message = payload.get("message")
    if not isinstance(message, str):
        return game_result("rejected", state, "invalid_message")

    stripped_message = message.strip()
    if not stripped_message or len(stripped_message) > MAX_MESSAGE_LENGTH:
        return game_result("rejected", state, "invalid_message")

    state.setdefault("messages", []).append(
        {
            "playerId": player["playerId"],
            "name": player.get("nickname", ""),
            "message": stripped_message,
        }
    )
    return game_result("accepted", state)


def get_state_snapshot(state, viewer):
    players = sorted(
        state["players"].values(),
        key=lambda player: (player.get("nickname", "").lower(), player["playerId"]),
    )
    return {
        "messages": [
            {
                "playerId": message.get("playerId", ""),
                "name": message.get("name", ""),
                "message": message.get("message", ""),
            }
            for message in state.get("messages", [])
        ],
        "players": [
            {
                "playerId": player["playerId"],
                "nickname": player.get("nickname", ""),
                "connected": player.get("connected", False),
            }
            for player in players
        ],
    }
