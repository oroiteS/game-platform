from app import create_app


def test_list_games_includes_lobby_demo_summary():
    client = create_app().test_client()

    response = client.get("/api/games")

    assert response.status_code == 200
    games = response.get_json()["games"]
    lobby_demo = next(game for game in games if game["id"] == "lobby-demo")
    assert lobby_demo["name"] == "Lobby Demo"
    assert lobby_demo["summary"]
    assert lobby_demo["minPlayers"] == 1
    assert lobby_demo["maxPlayers"] == 30


def test_get_game_returns_lobby_demo_rules():
    client = create_app().test_client()

    response = client.get("/api/games/lobby-demo")

    assert response.status_code == 200
    game = response.get_json()["game"]
    assert game["id"] == "lobby-demo"
    assert game["rules"]


def test_create_and_join_room_uses_public_serializers():
    client = create_app().test_client()

    create_response = client.post(
        "/api/rooms",
        json={"gameId": "lobby-demo", "nickname": "Ada", "capacity": 4},
    )

    assert create_response.status_code == 201
    create_payload = create_response.get_json()
    assert create_payload["room"]["capacity"] == 4
    assert create_payload["player"]["nickname"] == "Ada"
    assert create_payload["sessionToken"]
    assert "sessionTokenHash" not in create_response.get_data(as_text=True)

    join_response = client.post(
        f"/api/rooms/{create_payload['room']['roomCode']}/join",
        json={"nickname": "Lin"},
    )

    assert join_response.status_code == 200
    join_payload = join_response.get_json()
    assert join_payload["room"]["capacity"] == 4
    assert join_payload["player"]["nickname"] == "Lin"
    assert "sessionTokenHash" not in join_response.get_data(as_text=True)


def test_get_room_rejects_invalid_room_code():
    client = create_app().test_client()

    response = client.get("/api/rooms/abc")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_room_code"


def test_create_room_rejects_capacity_above_platform_limit():
    client = create_app().test_client()

    response = client.post(
        "/api/rooms",
        json={"gameId": "lobby-demo", "nickname": "Ada", "capacity": 31},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_capacity"


def test_create_room_rejects_non_string_game_id():
    client = create_app().test_client()

    response = client.post(
        "/api/rooms",
        json={"gameId": [], "nickname": "Ada", "capacity": 4},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_game_id"


def test_create_room_rejects_missing_body_as_invalid_json():
    client = create_app().test_client()

    response = client.post("/api/rooms")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_json"


def test_create_room_rejects_malformed_json():
    client = create_app().test_client()

    response = client.post(
        "/api/rooms",
        data='{"gameId": "lobby-demo"',
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_json"


def test_create_room_rejects_json_array_body():
    client = create_app().test_client()

    response = client.post("/api/rooms", json=[])

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_json"


def test_create_room_unknown_string_game_id_remains_not_found():
    client = create_app().test_client()

    response = client.post(
        "/api/rooms",
        json={"gameId": "missing-game", "nickname": "Ada", "capacity": 4},
    )

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "game_not_found"


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
