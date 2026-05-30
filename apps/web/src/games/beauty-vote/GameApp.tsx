import { useMemo } from "react";
import { Panel } from "../../components/ui/Panel";
import type { RoomSummary } from "../../api/client";
import type { BeautyVoteState } from "./types";
import { LobbyPhase } from "./phases/LobbyPhase";
import { SubmitPhase } from "./phases/SubmitPhase";
import { RevealPhase } from "./phases/RevealPhase";
import { GameOverPhase } from "./phases/GameOverPhase";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Props = {
  room: RoomSummary;
  gameState: unknown;
  playerId: string;
  onAction: (action: { type: string; payload?: unknown }) => boolean;
};

// ---------------------------------------------------------------------------
// readState helper
// ---------------------------------------------------------------------------

const VALID_PHASES = ["lobby", "submit", "reveal", "ended"] as const;

function readState(gameState: unknown): BeautyVoteState | null {
  if (!gameState || typeof gameState !== "object") {
    return null;
  }
  const state = gameState as Record<string, unknown>;
  if (!state.phase || typeof state.phase !== "string") {
    return null;
  }
  if (!(VALID_PHASES as readonly string[]).includes(state.phase)) {
    return null;
  }
  return gameState as BeautyVoteState;
}

// ---------------------------------------------------------------------------
// Main BeautyVoteGame component
// ---------------------------------------------------------------------------

export function BeautyVoteGame({ room, gameState, playerId, onAction }: Props) {
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

  const currentPlayer = state.players.find((p) => p.playerId === playerId);
  const isEliminated = currentPlayer && !currentPlayer.alive;

  if (isEliminated && state.phase !== "ended") {
    return (
      <Panel>
        <div style={{ textAlign: "center", padding: "24px 0" }}>
          <p style={{ fontSize: "1.2rem", fontWeight: 600, margin: "0 0 8px" }}>
            你已被淘汰
          </p>
          <p className="state-text">
            你的分数已归零，请等待其他玩家完成游戏
          </p>
        </div>
      </Panel>
    );
  }

  switch (state.phase) {
    case "lobby":
      return (
        <LobbyPhase
          state={state}
          room={room}
          playerId={playerId}
          onAction={onAction}
        />
      );
    case "submit":
      return (
        <SubmitPhase
          state={state}
          playerId={playerId}
          onAction={onAction}
        />
      );
    case "reveal":
      return (
        <RevealPhase
          state={state}
          playerId={playerId}
          onAction={onAction}
        />
      );
    case "ended":
      return <GameOverPhase state={state} playerId={playerId} />;
    default:
      return (
        <Panel>
          <p className="state-text">未知阶段</p>
        </Panel>
      );
  }
}
