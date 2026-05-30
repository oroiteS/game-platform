import { useMemo } from "react";
import type { PlayerState } from "../types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Props = {
  players: PlayerState[];
  highlightIds?: string[];
};

// ---------------------------------------------------------------------------
// ScoreBoard — real-time score leaderboard
// ---------------------------------------------------------------------------

export function ScoreBoard({ players, highlightIds = [] }: Props) {
  const sorted = useMemo(() => {
    const highlightSet = new Set(highlightIds);
    return [...players]
      .filter((p) => p.alive)
      .sort((a, b) => b.score - a.score)
      .map((p) => ({
        ...p,
        highlighted: highlightSet.has(p.playerId),
      }));
  }, [players, highlightIds]);

  if (sorted.length === 0) {
    return <p className="state-text">暂无存活玩家</p>;
  }

  return (
    <div className="player-list" aria-label="玩家分数排行榜">
      {sorted.map((p, i) => (
        <div
          className="player-row"
          key={p.playerId}
          style={
            p.highlighted
              ? { backgroundColor: "var(--color-primary-soft)" }
              : undefined
          }
        >
          <span>
            {i + 1}. {p.nickname}
            {p.lastNumber != null && (
              <span style={{ color: "var(--color-text-muted)", marginLeft: 8 }}>
                [{p.lastNumber}]
              </span>
            )}
          </span>
          <span style={{ fontWeight: 600 }}>{p.score} 分</span>
        </div>
      ))}
    </div>
  );
}
