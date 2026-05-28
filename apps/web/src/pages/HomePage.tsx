import { useEffect, useMemo, useState } from "react";
import { createRoom, getGames, joinRoom, type GameSummary, type JoinResponse } from "../api/client";
import { saveRoomSession } from "../platform/sessionStore";

function saveAndNavigate(response: JoinResponse): void {
  saveRoomSession(response.room.roomCode, {
    gameId: response.room.gameId,
    playerId: response.player.playerId,
    sessionToken: response.sessionToken,
    nickname: response.player.nickname,
  });
  window.location.hash = `/rooms/${response.room.roomCode}`;
}

export function HomePage() {
  const [games, setGames] = useState<GameSummary[]>([]);
  const [selectedGameId, setSelectedGameId] = useState("");
  const [nickname, setNickname] = useState("");
  const [capacity, setCapacity] = useState("2");
  const [joinRoomCode, setJoinRoomCode] = useState("");
  const [joinNickname, setJoinNickname] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getGames()
      .then((nextGames) => {
        setGames(nextGames);
        const firstGame = nextGames[0];
        if (firstGame) {
          setSelectedGameId(firstGame.id);
          setCapacity(String(Math.max(1, firstGame.minPlayers)));
        }
      })
      .catch((nextError: Error) => setError(nextError.message))
      .finally(() => setLoading(false));
  }, []);

  const selectedGame = useMemo(
    () => games.find((game) => game.id === selectedGameId) ?? null,
    [games, selectedGameId],
  );

  const capacityMax = selectedGame ? Math.min(30, selectedGame.maxPlayers) : 30;
  const capacityMin = selectedGame ? Math.max(1, selectedGame.minPlayers) : 1;

  const onSelectGame = (gameId: string) => {
    const game = games.find((item) => item.id === gameId);
    setSelectedGameId(gameId);
    if (game) {
      const nextMin = Math.max(1, game.minPlayers);
      const nextMax = Math.min(30, game.maxPlayers);
      const currentCapacity = Number(capacity);
      const nextCapacity = Number.isInteger(currentCapacity)
        ? Math.min(Math.max(currentCapacity, nextMin), nextMax)
        : nextMin;
      setCapacity(String(nextCapacity));
    }
  };

  const handleCreate = async () => {
    if (!selectedGameId || !nickname.trim()) {
      setError("请选择游戏并填写昵称");
      return;
    }
    const nextCapacity = Number(capacity);
    if (
      !Number.isInteger(nextCapacity) ||
      nextCapacity < capacityMin ||
      nextCapacity > capacityMax
    ) {
      setError(`本局人数需为 ${capacityMin}-${capacityMax} 之间的整数`);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await createRoom(selectedGameId, nickname.trim(), nextCapacity);
      saveAndNavigate(response);
    } catch (nextError) {
      setError((nextError as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleJoin = async () => {
    const roomCode = joinRoomCode.trim();
    if (!/^[0-9]{6}$/.test(roomCode) || !joinNickname.trim()) {
      setError("请输入 6 位房间号和昵称");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await joinRoom(roomCode, joinNickname.trim());
      saveAndNavigate(response);
    } catch (nextError) {
      setError((nextError as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app-shell">
      <section className="top-band">
        <p className="eyebrow">轻量多人游戏平台</p>
        <h1>创建房间或输入房间号加入</h1>
      </section>

      <section className="home-grid" aria-label="房间操作">
        <div className="work-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Create</p>
              <h2>创建房间</h2>
            </div>
          </div>

          <label>
            昵称
            <input
              value={nickname}
              onChange={(event) => setNickname(event.target.value)}
              maxLength={24}
              placeholder="例如 Ada"
            />
          </label>

          <label>
            本局人数
            <input
              type="number"
              min={capacityMin}
              max={capacityMax}
              value={capacity}
              onChange={(event) => setCapacity(event.target.value)}
            />
          </label>

          <div className="game-options">
            {games.map((game) => (
              <button
                className={game.id === selectedGameId ? "game-option selected" : "game-option"}
                key={game.id}
                type="button"
                onClick={() => onSelectGame(game.id)}
              >
                <strong>{game.name}</strong>
                <span>{game.summary}</span>
                <small>{game.minPlayers}-{game.maxPlayers} 人</small>
              </button>
            ))}
          </div>

          <button type="button" className="primary-button" disabled={loading} onClick={handleCreate}>
            创建房间
          </button>
        </div>

        <div className="work-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Join</p>
              <h2>加入房间</h2>
            </div>
          </div>

          <label>
            6 位房间号
            <input
              value={joinRoomCode}
              onChange={(event) => setJoinRoomCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
              inputMode="numeric"
              pattern="[0-9]{6}"
              placeholder="123456"
            />
          </label>

          <label>
            昵称
            <input
              value={joinNickname}
              onChange={(event) => setJoinNickname(event.target.value)}
              maxLength={24}
              placeholder="例如 Lin"
            />
          </label>

          <button type="button" className="primary-button" disabled={loading} onClick={handleJoin}>
            加入房间
          </button>
        </div>
      </section>

      {error ? (
        <p className="global-error" role="alert">
          {error}
        </p>
      ) : null}
    </main>
  );
}
