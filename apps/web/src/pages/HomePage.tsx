import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Button } from "../components/ui/Button";
import { FieldError } from "../components/ui/FieldError";
import { Panel } from "../components/ui/Panel";
import { TextField } from "../components/ui/TextField";
import { createRoom, type GameSummary, type JoinResponse } from "../api/client";
import { saveRoomSession } from "../platform/sessionStore";
import { useGames } from "../platform/useGames";

type CreateErrors = {
  nickname?: string;
  capacity?: string;
  gameId?: string;
  form?: string;
};

function saveAndNavigate(response: JoinResponse): void {
  saveRoomSession(response.room.roomCode, {
    gameId: response.room.gameId,
    playerId: response.player.playerId,
    sessionToken: response.sessionToken,
    nickname: response.player.nickname,
  });
  window.location.hash = `/rooms/${response.room.roomCode}`;
}

function GameSelection({
  games,
  selectedGameId,
  selectedGame,
  loading,
  error,
  onSelect,
}: {
  games: GameSummary[];
  selectedGameId: string;
  selectedGame: GameSummary | null;
  loading: boolean;
  error: string | null;
  onSelect: (gameId: string) => void;
}) {
  return (
    <section className="game-picker" aria-labelledby="game-picker-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Game</p>
          <h2 id="game-picker-title">选择游戏</h2>
        </div>
      </div>

      {loading && <p className="state-text">加载游戏列表…</p>}
      {error && <p className="state-text" style={{ color: "var(--color-danger)" }}>{error}</p>}
      {!loading && !error && games.length === 0 && <p className="state-text">暂无可用游戏。</p>}

      {!loading && !error && games.length > 0 && (
        <>
          <select
            id="game-select"
            value={selectedGameId}
            onChange={(e) => onSelect(e.target.value)}
            style={{ width: "100%", padding: "8px 12px", fontSize: "1rem", borderRadius: 6, border: "1px solid var(--color-border)", background: "var(--color-surface)", color: "var(--color-text)" }}
          >
            {games.map((game) => (
              <option key={game.id} value={game.id}>
                {game.name} ({game.minPlayers}-{game.maxPlayers}人)
              </option>
            ))}
          </select>
          {selectedGame && (
            <p className="state-text" style={{ marginTop: 8 }}>
              {selectedGame.name} — {selectedGame.minPlayers}-{selectedGame.maxPlayers} 人
            </p>
          )}
        </>
      )}
    </section>
  );
}

function CreateRoomForm({
  selectedGame,
  selectedGameId,
  capacity,
  capacityMin,
  capacityMax,
  loading,
  errors,
  onCapacityChange,
  onSubmit,
}: {
  selectedGame: GameSummary | null;
  selectedGameId: string;
  capacity: string;
  capacityMin: number;
  capacityMax: number;
  loading: boolean;
  errors: CreateErrors;
  onCapacityChange: (capacity: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="form-stack" onSubmit={onSubmit} noValidate>
      <input type="hidden" name="gameId" value={selectedGameId} />
      <TextField
        id="create-nickname"
        name="nickname"
        label="昵称"
        autoComplete="nickname"
        maxLength={24}
        placeholder="例如 Ada…"
        error={errors.nickname}
      />
      <TextField
        id="create-capacity"
        name="capacity"
        label="本局人数"
        type="number"
        autoComplete="off"
        min={capacityMin}
        max={capacityMax}
        value={capacity}
        onChange={(event) => onCapacityChange(event.target.value)}
        helpText={
          selectedGame ? `${selectedGame.name} 支持 ${capacityMin}-${capacityMax} 人` : undefined
        }
        error={errors.capacity}
      />
      {errors.gameId ? <FieldError message={errors.gameId} /> : null}
      {errors.form ? <FieldError message={errors.form} /> : null}
      <Button type="submit" disabled={loading || !selectedGameId}>
        {loading ? "创建中…" : "创建房间"}
      </Button>
    </form>
  );
}

function JoinRoomForm({
  roomCode,
  loading,
  error,
  onRoomCodeChange,
  onSubmit,
}: {
  roomCode: string;
  loading: boolean;
  error: string | null;
  onRoomCodeChange: (roomCode: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="form-stack" onSubmit={onSubmit} noValidate>
      <TextField
        id="join-room-code"
        name="roomCode"
        label="6 位房间号"
        value={roomCode}
        onChange={(event) => onRoomCodeChange(event.target.value.replace(/\D/g, "").slice(0, 6))}
        inputMode="numeric"
        pattern="[0-9]{6}"
        autoComplete="one-time-code"
        placeholder="123456…"
        error={error}
      />
      <Button type="submit" disabled={loading}>
        进入房间
      </Button>
    </form>
  );
}

export function HomePage() {
  const { games, loading: gamesLoading, error: gamesError } = useGames();
  const [selectedGameId, setSelectedGameId] = useState("");
  const [capacity, setCapacity] = useState("2");
  const [joinRoomCode, setJoinRoomCode] = useState("");
  const [creating, setCreating] = useState(false);
  const [createErrors, setCreateErrors] = useState<CreateErrors>({});
  const [joinError, setJoinError] = useState<string | null>(null);

  useEffect(() => {
    if (selectedGameId || games.length === 0) {
      return;
    }

    const firstGame = games[0];
    setSelectedGameId(firstGame.id);
    setCapacity(String(Math.max(1, firstGame.minPlayers)));
  }, [games, selectedGameId]);

  const selectedGame = useMemo(
    () => games.find((game) => game.id === selectedGameId) ?? null,
    [games, selectedGameId],
  );

  const capacityMax = selectedGame ? Math.min(30, selectedGame.maxPlayers) : 30;
  const capacityMin = selectedGame ? Math.max(1, selectedGame.minPlayers) : 1;

  const onSelectGame = (gameId: string) => {
    const game = games.find((item) => item.id === gameId);
    setSelectedGameId(gameId);
    setCreateErrors((current) => ({ ...current, gameId: undefined, form: undefined }));
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

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const nickname = String(form.get("nickname") ?? "").trim();
    const gameId = String(form.get("gameId") ?? "");
    const nextCapacity = Number(form.get("capacity"));
    const nextErrors: CreateErrors = {};

    if (!gameId) {
      nextErrors.gameId = "请选择一个游戏";
    }
    if (!nickname) {
      nextErrors.nickname = "请填写昵称";
    }
    if (
      !Number.isInteger(nextCapacity) ||
      nextCapacity < capacityMin ||
      nextCapacity > capacityMax
    ) {
      nextErrors.capacity = `本局人数需为 ${capacityMin}-${capacityMax} 之间的整数`;
    }

    if (Object.keys(nextErrors).length > 0) {
      setCreateErrors(nextErrors);
      return;
    }

    setCreating(true);
    setCreateErrors({});
    try {
      const response = await createRoom(gameId, nickname, nextCapacity);
      saveAndNavigate(response);
    } catch (error) {
      setCreateErrors({ form: (error as Error).message });
    } finally {
      setCreating(false);
    }
  };

  const handleJoin = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const roomCode = joinRoomCode.trim();
    if (!/^[0-9]{6}$/.test(roomCode)) {
      setJoinError("请输入 6 位房间号");
      return;
    }

    setJoinError(null);
    window.location.hash = `/rooms/${roomCode}`;
  };

  return (
    <main className="app-shell" id="main-content">
      <section className="top-band">
        <p className="eyebrow">轻量多人游戏平台</p>
        <h1>创建房间或输入房间号加入</h1>
        <p className="hero-copy">匿名身份、单体部署、快速开局；平台只处理房间与连接。</p>
      </section>

      <section className="home-grid" aria-label="房间操作">
        <Panel>
          <div className="section-heading">
            <div>
              <p className="eyebrow">Create</p>
              <h2>创建房间</h2>
            </div>
          </div>
          <GameSelection
            games={games}
            selectedGameId={selectedGameId}
            selectedGame={selectedGame}
            loading={gamesLoading}
            error={gamesError}
            onSelect={onSelectGame}
          />
          <CreateRoomForm
            selectedGame={selectedGame}
            selectedGameId={selectedGameId}
            capacity={capacity}
            capacityMin={capacityMin}
            capacityMax={capacityMax}
            loading={creating}
            errors={createErrors}
            onCapacityChange={setCapacity}
            onSubmit={handleCreate}
          />
        </Panel>

        <Panel>
          <div className="section-heading">
            <div>
              <p className="eyebrow">Join</p>
              <h2>输入房间号进入房间</h2>
            </div>
          </div>
          <JoinRoomForm
            roomCode={joinRoomCode}
            loading={creating}
            error={joinError}
            onRoomCodeChange={setJoinRoomCode}
            onSubmit={handleJoin}
          />
        </Panel>
      </section>
    </main>
  );
}
