import { useMemo, useState } from "react";
import type { PlayerSummary, RoomSummary } from "../../api/client";

type LobbyDemoState = {
  message?: string;
  players?: PlayerSummary[];
};

type LobbyDemoProps = {
  room: RoomSummary;
  gameState: unknown;
  onAction: (action: { type: string; payload?: unknown }) => boolean;
};

function readState(gameState: unknown): LobbyDemoState {
  if (!gameState || typeof gameState !== "object") {
    return {};
  }
  return gameState as LobbyDemoState;
}

export function LobbyDemo({ room, gameState, onAction }: LobbyDemoProps) {
  const state = useMemo(() => readState(gameState), [gameState]);
  const [message, setMessage] = useState("");
  const players = state.players ?? room.players;

  const submit = () => {
    const nextMessage = message.trim();
    if (!nextMessage) {
      return;
    }
    const accepted = onAction({
      type: "set_message",
      payload: { message: nextMessage },
    });
    if (accepted) {
      setMessage("");
    }
  };

  return (
    <section className="game-surface" aria-labelledby="lobby-demo-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Lobby Demo</p>
          <h2 id="lobby-demo-title">共享消息</h2>
        </div>
        <span className="status-pill">{players.length}/{room.capacity}</span>
      </div>

      <div className="message-board">
        {state.message ? <p>{state.message}</p> : <p className="muted">暂无消息</p>}
      </div>

      <div className="inline-form">
        <input
          aria-label="广播消息"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              submit();
            }
          }}
          maxLength={80}
          placeholder="输入要广播的消息"
        />
        <button type="button" onClick={submit}>
          Send
        </button>
      </div>

      <div className="player-strip" aria-label="玩家在线状态">
        {players.map((player) => (
          <span
            className={player.connected ? "player-chip online" : "player-chip offline"}
            key={player.playerId}
          >
            {player.nickname}
          </span>
        ))}
      </div>
    </section>
  );
}
