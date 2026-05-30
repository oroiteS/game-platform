import { useMemo } from "react";
import { Button } from "../../../components/ui/Button";
import { Panel } from "../../../components/ui/Panel";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import type { RoomSummary } from "../../../api/client";
import type { BeautyVoteState } from "../types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Props = {
  state: BeautyVoteState;
  room: RoomSummary;
  playerId: string;
  onAction: (action: { type: string; payload?: unknown }) => boolean;
};

// ---------------------------------------------------------------------------
// LobbyPhase
// ---------------------------------------------------------------------------

export function LobbyPhase({ state, room, playerId, onAction }: Props) {
  const readyCount = state.readyPlayerIds.length;
  const totalPlayers = state.players.length;
  const isReady = state.readyPlayerIds.includes(playerId);
  const allReady = state.players.every((p) => state.readyPlayerIds.includes(p.playerId));
  const isFull = totalPlayers === room.capacity;

  const statusText = useMemo(() => {
    if (isFull && allReady) {
      return "游戏即将开始...";
    }
    if (isFull && !allReady) {
      return "等待所有玩家准备";
    }
    return "等待更多玩家加入";
  }, [isFull, allReady]);

  return (
    <section className="game-surface" aria-labelledby="bv-lobby-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">美人投票</p>
          <h2 id="bv-lobby-title">准备阶段</h2>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <StatusBadge tone="neutral" aria-live="polite" aria-atomic="true">
            {totalPlayers}/{room.capacity} 人
          </StatusBadge>
          <StatusBadge tone="neutral" aria-live="polite" aria-atomic="true">
            {readyCount}/{totalPlayers} 已准备
          </StatusBadge>
        </div>
      </div>

      <p className="state-text" aria-live="polite">
        {statusText}
      </p>

      <div className="player-list" aria-label="玩家准备状态">
        {state.players.length === 0 ? (
          <p className="state-text">暂无玩家</p>
        ) : (
          state.players.map((p) => {
            const ready = state.readyPlayerIds.includes(p.playerId);
            return (
              <div className="player-row" key={p.playerId}>
                <span>{p.nickname}</span>
                <StatusBadge tone={ready ? "success" : "neutral"}>
                  {ready ? "已准备" : "未准备"}
                </StatusBadge>
              </div>
            );
          })
        )}
      </div>

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <Button
          variant={isReady ? "secondary" : "primary"}
          onClick={() => onAction({ type: "toggle_ready" })}
        >
          {isReady ? "取消准备" : "准备"}
        </Button>
      </div>
    </section>
  );
}
