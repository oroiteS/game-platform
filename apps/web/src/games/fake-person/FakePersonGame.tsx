import { useMemo } from "react";
import { Button } from "../../components/ui/Button";
import { Panel } from "../../components/ui/Panel";
import { StatusBadge } from "../../components/ui/StatusBadge";
import type { RoomSummary } from "../../api/client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type GamePhase = "lobby" | "identity_pick" | "question" | "reveal";

type FakePersonState = {
  phase: GamePhase;
  hostPlayerId: string | null;
  readyPlayerIds: string[];
  myIdentity: { role: "human" | "fake"; keyword?: string } | null;
  currentQuestion: string | null;
  currentGuess: {
    targetPlayerId: string;
    guessedRole: string;
    correct: boolean;
    actualRole: string;
    keyword: string | null;
  } | null;
  guessedPlayerIds: string[];
  players: {
    playerId: string;
    nickname: string;
    isHost: boolean;
    ready: boolean;
  }[];
  allIdentities?: Record<string, { role: string; keyword?: string }> | null;
};

type Props = {
  room: RoomSummary;
  gameState: unknown;
  playerId: string;
  onAction: (action: { type: string; payload?: unknown }) => boolean;
};

// ---------------------------------------------------------------------------
// readState helper
// ---------------------------------------------------------------------------

function readState(gameState: unknown): FakePersonState | null {
  if (!gameState || typeof gameState !== "object") {
    return null;
  }
  const state = gameState as Record<string, unknown>;
  if (!state.phase || typeof state.phase !== "string") {
    return null;
  }
  const phase = state.phase as string;
  if (!["lobby", "identity_pick", "question", "reveal"].includes(phase)) {
    return null;
  }
  return gameState as FakePersonState;
}

// ---------------------------------------------------------------------------
// Host control bar
// ---------------------------------------------------------------------------

function HostControls({
  isHost,
  onEndGame,
}: {
  isHost: boolean;
  onEndGame: () => void;
}) {
  if (!isHost) return null;

  return (
    <div style={{ display: "flex", justifyContent: "flex-end", paddingTop: 12, borderTop: "1px solid var(--color-border)" }}>
      <Button variant="ghost" onClick={onEndGame}>
        结束游戏
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// LobbyPhase
// ---------------------------------------------------------------------------

function LobbyPhase({
  state,
  room,
  playerId,
  onAction,
  isHost,
}: {
  state: FakePersonState;
  room: RoomSummary;
  playerId: string;
  onAction: (action: { type: string; payload?: unknown }) => boolean;
  isHost: boolean;
}) {
  const readyCount = state.readyPlayerIds.length;
  const totalPlayers = state.players.length;
  const isReady = state.readyPlayerIds.includes(playerId);
  const allReady = state.players.every((p) => state.readyPlayerIds.includes(p.playerId));
  const isFull = totalPlayers === room.capacity;
  const canBecomeHost = allReady && isFull && state.hostPlayerId === null && !isHost;

  return (
    <section className="game-surface" aria-labelledby="fp-lobby-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">伪人游戏</p>
          <h2 id="fp-lobby-title">准备阶段</h2>
        </div>
        <StatusBadge tone="neutral" aria-live="polite" aria-atomic="true">
          {readyCount}/{totalPlayers} 已准备
        </StatusBadge>
      </div>

      <div className="player-list" aria-label="玩家准备状态">
        {state.players.length === 0 ? (
          <p className="state-text">暂无玩家</p>
        ) : (
          state.players.map((p) => {
            const ready = state.readyPlayerIds.includes(p.playerId);
            return (
              <div className="player-row" key={p.playerId}>
                <span>
                  {p.nickname}
                  {p.isHost ? " (主持人)" : ""}
                </span>
                <StatusBadge tone={ready ? "success" : "neutral"}>
                  {ready ? "已准备" : "未准备"}
                </StatusBadge>
              </div>
            );
          })
        )}
      </div>

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        {!isHost && (
          <Button
            variant={isReady ? "secondary" : "primary"}
            onClick={() => onAction({ type: "toggle_ready" })}
          >
            {isReady ? "取消准备" : "准备"}
          </Button>
        )}
        <Button
          variant="primary"
          disabled={!canBecomeHost}
          onClick={() => onAction({ type: "become_host" })}
        >
          成为主持人
        </Button>
      </div>

      <HostControls isHost={isHost} onEndGame={() => onAction({ type: "end_game" })} />
    </section>
  );
}

// ---------------------------------------------------------------------------
// IdentityPickPhase
// ---------------------------------------------------------------------------

function IdentityPickPhase({
  state,
  playerId,
  onAction,
  isHost,
}: {
  state: FakePersonState;
  playerId: string;
  onAction: (action: { type: string; payload?: unknown }) => boolean;
  isHost: boolean;
}) {
  const hasPicked = state.myIdentity !== null;
  const nonHostPlayers = state.players.filter((p) => p.playerId !== state.hostPlayerId);
  const pickedCount = state.allIdentities
    ? Object.keys(state.allIdentities).length
    : 0;

  const allNonHostPicked = state.allIdentities
    ? nonHostPlayers.every((p) => p.playerId in state.allIdentities!)
    : false;

  return (
    <section className="game-surface" aria-labelledby="fp-identity-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">伪人游戏</p>
          <h2 id="fp-identity-title">选择身份</h2>
        </div>
        {state.allIdentities && (
          <StatusBadge tone="neutral" aria-live="polite" aria-atomic="true">
            {pickedCount}/{nonHostPlayers.length} 已选择
          </StatusBadge>
        )}
      </div>

      {isHost ? (
        <div className="form-stack">
          <p className="state-text">等待所有玩家选择身份...</p>
          <Button
            variant="primary"
            disabled={!allNonHostPicked}
            onClick={() => onAction({ type: "draw_question" })}
          >
            抽取问题
          </Button>
        </div>
      ) : hasPicked ? (
        <div className="form-stack">
          <Panel>
            <p style={{ fontWeight: 800, fontSize: "1.1rem" }}>
              你的身份：{state.myIdentity!.role === "human" ? "人类" : "伪人"}
            </p>
            {state.myIdentity!.keyword && (
              <p style={{ color: "var(--color-accent)", fontWeight: 900, marginTop: 8 }}>
                关键词：{state.myIdentity!.keyword}
              </p>
            )}
          </Panel>
          <p className="state-text">等待主持人抽取问题...</p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <button
            className="game-option"
            style={{ padding: 24, textAlign: "center", cursor: "pointer" }}
            onClick={() => onAction({ type: "pick_identity", payload: { role: "human" } })}
          >
            <strong style={{ fontSize: "1.3rem" }}>人类</strong>
            <small>自由回答</small>
          </button>
          <button
            className="game-option"
            style={{ padding: 24, textAlign: "center", cursor: "pointer" }}
            onClick={() => onAction({ type: "pick_identity", payload: { role: "fake" } })}
          >
            <strong style={{ fontSize: "1.3rem" }}>伪人</strong>
            <small>需要关键词</small>
          </button>
        </div>
      )}

      {/* Player pick status strip */}
      {state.allIdentities && (
        <div className="player-strip" aria-label="玩家选择状态">
          {state.players
            .filter((p) => p.playerId !== state.hostPlayerId)
            .map((p) => {
              const picked = p.playerId in state.allIdentities!;
              return (
                <span
                  className={picked ? "player-chip is-online" : "player-chip is-offline"}
                  key={p.playerId}
                >
                  <span>{p.nickname}</span>
                  <strong>{picked ? "已选择" : "未选择"}</strong>
                </span>
              );
            })}
        </div>
      )}

      <HostControls isHost={isHost} onEndGame={() => onAction({ type: "end_game" })} />
    </section>
  );
}

// ---------------------------------------------------------------------------
// QuestionPhase
// ---------------------------------------------------------------------------

function QuestionPhase({
  state,
  playerId,
  onAction,
  isHost,
}: {
  state: FakePersonState;
  playerId: string;
  onAction: (action: { type: string; payload?: unknown }) => boolean;
  isHost: boolean;
}) {
  const nonHostPlayers = state.players.filter((p) => p.playerId !== state.hostPlayerId);
  const unguessedPlayers = nonHostPlayers.filter(
    (p) => !state.guessedPlayerIds.includes(p.playerId),
  );

  return (
    <section className="game-surface" aria-labelledby="fp-question-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">伪人游戏</p>
          <h2 id="fp-question-title">问答阶段</h2>
        </div>
        <StatusBadge tone="neutral">
          {state.guessedPlayerIds.length}/{nonHostPlayers.length} 已猜测
        </StatusBadge>
      </div>

      {/* Question box */}
      <Panel
        style={{
          textAlign: "center",
          padding: 24,
          background: "var(--color-primary-soft)",
          borderColor: "var(--color-primary)",
        }}
      >
        <p className="eyebrow">当前问题</p>
        <p style={{ fontSize: "1.2rem", fontWeight: 800, marginTop: 8 }}>
          {state.currentQuestion}
        </p>
      </Panel>

      {!isHost ? (
        <p className="state-text" style={{ textAlign: "center", padding: "12px 0" }}>
          请线下口头回答问题。等待主持人猜测...
        </p>
      ) : unguessedPlayers.length === 0 ? (
        <p className="state-text" style={{ textAlign: "center", padding: "12px 0" }}>
          所有玩家已猜测完毕
        </p>
      ) : (
        <div className="player-list" aria-label="待猜测的玩家">
          {unguessedPlayers.map((p) => (
            <div className="player-row" key={p.playerId}>
              <span>{p.nickname}</span>
              <div style={{ display: "flex", gap: 8 }}>
                <Button
                  variant="secondary"
                  onClick={() =>
                    onAction({
                      type: "guess",
                      payload: { targetPlayerId: p.playerId, guessedRole: "human" },
                    })
                  }
                >
                  人类
                </Button>
                <Button
                  variant="secondary"
                  onClick={() =>
                    onAction({
                      type: "guess",
                      payload: { targetPlayerId: p.playerId, guessedRole: "fake" },
                    })
                  }
                >
                  伪人
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <HostControls isHost={isHost} onEndGame={() => onAction({ type: "end_game" })} />
    </section>
  );
}

// ---------------------------------------------------------------------------
// RevealPhase
// ---------------------------------------------------------------------------

function RevealPhase({
  state,
  playerId,
  onAction,
  isHost,
}: {
  state: FakePersonState;
  playerId: string;
  onAction: (action: { type: string; payload?: unknown }) => boolean;
  isHost: boolean;
}) {
  const guess = state.currentGuess;
  if (!guess) {
    return (
      <section className="game-surface">
        <p className="state-text">等待揭晓结果...</p>
      </section>
    );
  }

  const guessedPlayer = state.players.find(
    (p) => p.playerId === guess.targetPlayerId,
  );
  const guessedName = guessedPlayer?.nickname ?? guess.targetPlayerId;

  const nonHostPlayers = state.players.filter(
    (p) => p.playerId !== state.hostPlayerId,
  );
  const hasUnguessed = nonHostPlayers.some(
    (p) => !state.guessedPlayerIds.includes(p.playerId),
  );

  return (
    <section className="game-surface" aria-labelledby="fp-reveal-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">伪人游戏</p>
          <h2 id="fp-reveal-title">揭晓结果</h2>
        </div>
      </div>

      {/* Centered result */}
      <div
        style={{
          textAlign: "center",
          padding: "32px 16px",
        }}
      >
        {/* Big check/cross */}
        <div
          style={{
            fontSize: "4rem",
            fontWeight: 900,
            lineHeight: 1,
            marginBottom: 12,
            color: guess.correct ? "var(--color-success)" : "var(--color-danger)",
          }}
        >
          {guess.correct ? "✓" : "✗"}
        </div>

        <p style={{ fontSize: "1.1rem", fontWeight: 800, marginBottom: 8 }}>
          {guess.correct ? "猜测正确！" : "猜测错误！"}
        </p>

        <Panel style={{ textAlign: "center" }}>
          <p>
            <strong>{guessedName}</strong> 的真实身份：
          </p>
          <p
            style={{
              fontSize: "1.3rem",
              fontWeight: 900,
              marginTop: 8,
              color:
                guess.actualRole === "human"
                  ? "var(--color-primary-strong)"
                  : "var(--color-accent)",
            }}
          >
            {guess.actualRole === "human" ? "人类" : "伪人"}
          </p>

          {guess.actualRole === "fake" && guess.keyword && (
            <p
              style={{
                color: "var(--color-accent)",
                fontWeight: 900,
                marginTop: 8,
              }}
            >
              关键词：{guess.keyword}
            </p>
          )}

          <p style={{ color: "var(--color-muted)", marginTop: 8 }}>
            主持人猜测为：{guess.guessedRole === "human" ? "人类" : "伪人"}
          </p>
        </Panel>
      </div>

      {/* Host controls */}
      {isHost ? (
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "center" }}>
          {hasUnguessed && (
            <Button
              variant="primary"
              onClick={() => onAction({ type: "next_player" })}
            >
              下一个玩家
            </Button>
          )}
          <Button
            variant={hasUnguessed ? "secondary" : "primary"}
            onClick={() => onAction({ type: "next_player" })}
          >
            结束游戏
          </Button>
        </div>
      ) : (
        <p className="state-text" style={{ textAlign: "center" }}>
          等待主持人操作...
        </p>
      )}

      <HostControls isHost={isHost} onEndGame={() => onAction({ type: "end_game" })} />
    </section>
  );
}

// ---------------------------------------------------------------------------
// Main FakePersonGame component
// ---------------------------------------------------------------------------

export function FakePersonGame({ room, gameState, playerId, onAction }: Props) {
  const state = useMemo(() => readState(gameState), [gameState]);

  if (!state) {
    return (
      <Panel>
        <p className="state-text" aria-live="polite">
          等待游戏状态...
        </p>
      </Panel>
    );
  }

  const isHost = state.hostPlayerId === playerId;

  switch (state.phase) {
    case "lobby":
      return (
        <LobbyPhase
          state={state}
          room={room}
          playerId={playerId}
          onAction={onAction}
          isHost={isHost}
        />
      );
    case "identity_pick":
      return (
        <IdentityPickPhase
          state={state}
          playerId={playerId}
          onAction={onAction}
          isHost={isHost}
        />
      );
    case "question":
      return (
        <QuestionPhase
          state={state}
          playerId={playerId}
          onAction={onAction}
          isHost={isHost}
        />
      );
    case "reveal":
      return (
        <RevealPhase
          state={state}
          playerId={playerId}
          onAction={onAction}
          isHost={isHost}
        />
      );
    default:
      return (
        <Panel>
          <p className="state-text">未知游戏阶段</p>
        </Panel>
      );
  }
}
