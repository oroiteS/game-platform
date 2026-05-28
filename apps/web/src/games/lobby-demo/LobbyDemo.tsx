import { useMemo, useState, type FormEvent } from "react";
import { Button } from "../../components/ui/Button";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { TextField } from "../../components/ui/TextField";
import type { PlayerSummary, RoomSummary } from "../../api/client";

type LobbyDemoState = {
  message?: string;
  messages?: Array<{
    playerId?: string;
    name?: string;
    message?: string;
  }>;
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
  const messages = state.messages ?? (
    state.message ? [{ name: "系统", message: state.message }] : []
  );
  const onlineCount = players.filter((player) => player.connected).length;

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
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
        <StatusBadge tone="neutral" aria-live="polite" aria-atomic="true">
          {onlineCount}/{room.capacity} 在线
        </StatusBadge>
      </div>

      <div className="message-board" aria-live="polite" aria-atomic="false">
        {messages.length > 0 ? (
          <ol className="message-list" aria-label="共享消息历史">
            {messages.map((item, index) => (
              <li className="message-item" key={`${item.playerId ?? "unknown"}-${index}`}>
                <strong>{item.name || "匿名玩家"}:</strong>
                <span>{item.message}</span>
              </li>
            ))}
          </ol>
        ) : (
          <p className="state-text">暂无消息</p>
        )}
      </div>

      <form className="inline-form" onSubmit={submit}>
        <TextField
          id="lobby-message"
          name="message"
          label="广播消息"
          autoComplete="off"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          maxLength={80}
          placeholder="输入要广播的消息…"
        />
        <Button type="submit" disabled={!message.trim()}>
          发送
        </Button>
      </form>

      <div className="player-strip" aria-label="玩家在线状态" aria-live="polite">
        {players.map((player) => (
          <span
            className={player.connected ? "player-chip is-online" : "player-chip is-offline"}
            key={player.playerId}
          >
            <span>{player.nickname}</span>
            <strong>{player.connected ? "在线" : "离线"}</strong>
          </span>
        ))}
      </div>
    </section>
  );
}
