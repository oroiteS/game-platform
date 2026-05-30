import { useMemo } from "react";
import { Panel } from "../../../components/ui/Panel";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import type { BeautyVoteState } from "../types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Props = {
  state: BeautyVoteState;
  playerId: string;
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type RankedPlayer = {
  rank: number;
  playerId: string;
  nickname: string;
  score: number;
  alive: boolean;
};

function buildRankings(
  players: BeautyVoteState["players"],
): RankedPlayer[] {
  const sorted = [...players].sort((a, b) => b.score - a.score);
  const ranked: RankedPlayer[] = [];
  let currentRank = 0;
  let prevScore: number | null = null;

  for (let i = 0; i < sorted.length; i++) {
    if (prevScore === null || sorted[i].score < prevScore) {
      currentRank = i + 1;
    }
    prevScore = sorted[i].score;
    ranked.push({
      rank: currentRank,
      playerId: sorted[i].playerId,
      nickname: sorted[i].nickname,
      score: sorted[i].score,
      alive: sorted[i].alive,
    });
  }

  return ranked;
}

function buildRoundsArray(
  allSubmissions: Record<number, Record<string, number>>,
): number[] {
  return Object.keys(allSubmissions)
    .map(Number)
    .sort((a, b) => a - b);
}

// ---------------------------------------------------------------------------
// GameOverPhase
// ---------------------------------------------------------------------------

export function GameOverPhase({ state, playerId }: Props) {
  const rankings = useMemo(() => buildRankings(state.players), [state.players]);
  const rounds = useMemo(() => {
    if (!state.allSubmissions) return [];
    return buildRoundsArray(state.allSubmissions);
  }, [state.allSubmissions]);

  const winner = useMemo(() => {
    const alive = rankings.filter((p) => p.alive);
    if (alive.length === 0) return null;
    return alive[0];
  }, [rankings]);

  const currentPlayer = state.players.find((p) => p.playerId === playerId);
  const survived = currentPlayer?.alive ?? false;

  return (
    <section className="game-surface" aria-labelledby="bv-gameover-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">美人投票</p>
          <h2 id="bv-gameover-title">游戏结束</h2>
        </div>
      </div>

      {/* Winner announcement */}
      {winner ? (
        <Panel
          style={{
            textAlign: "center",
            padding: 24,
            background: "var(--color-primary-soft)",
            borderColor: "var(--color-primary)",
          }}
        >
          <p className="eyebrow">胜者</p>
          <p style={{ fontSize: "1.4rem", fontWeight: 900, marginTop: 8, overflowWrap: "anywhere" }}>
            {winner.nickname}
          </p>
          <p style={{ color: "var(--color-muted)", marginTop: 4 }}>
            最终得分：{winner.score}
          </p>
        </Panel>
      ) : (
        <p className="state-text" style={{ textAlign: "center" }}>
          无存活玩家
        </p>
      )}

      {/* Survival status */}
      <div style={{ textAlign: "center", padding: "12px 0" }}>
        {survived ? (
          <StatusBadge tone="success">你存活到了最后！</StatusBadge>
        ) : (
          <StatusBadge tone="danger">你被淘汰了</StatusBadge>
        )}
      </div>

      {/* Final rankings */}
      <div className="player-list" aria-label="最终排行榜">
        {rankings.length === 0 ? (
          <p className="state-text">暂无玩家数据</p>
        ) : (
          rankings.map((p) => (
            <div className="player-row" key={p.playerId}>
              <div style={{ display: "flex", gap: 12, alignItems: "center", minWidth: 0 }}>
                <span
                  style={{
                    fontWeight: 900,
                    fontSize: "1.1rem",
                    minWidth: 32,
                    textAlign: "center",
                    flexShrink: 0,
                    color:
                      p.rank === 1
                        ? "var(--color-primary-strong)"
                        : p.rank <= 3
                          ? "var(--color-accent)"
                          : "var(--color-muted)",
                  }}
                >
                  #{p.rank}
                </span>
                <span style={{ overflowWrap: "anywhere", minWidth: 0 }}>{p.nickname}</span>
              </div>
              <div style={{ display: "flex", gap: 12, alignItems: "center", flexShrink: 0 }}>
                <span style={{ fontWeight: 700, whiteSpace: "nowrap" }}>{p.score} 分</span>
                <StatusBadge tone={p.alive ? "success" : "neutral"}>
                  {p.alive ? "存活" : "淘汰"}
                </StatusBadge>
              </div>
            </div>
          ))
        )}
      </div>

      {/* All-time submissions table */}
      {state.allSubmissions && rounds.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h3
            style={{
              fontSize: "1.1rem",
              fontWeight: 800,
              marginBottom: 12,
            }}
          >
            所有回合数字
          </h3>
          <div style={{ overflowX: "auto", minWidth: 0 }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: "0.9rem",
              }}
            >
              <thead>
                <tr
                  style={{
                    borderBottom: "2px solid var(--color-border)",
                  }}
                >
                  <th
                    style={{
                      padding: "8px 12px",
                      textAlign: "left",
                      fontWeight: 700,
                      whiteSpace: "nowrap",
                    }}
                  >
                    玩家
                  </th>
                  {rounds.map((r) => (
                    <th
                      key={r}
                      style={{
                        padding: "8px 12px",
                        textAlign: "center",
                        fontWeight: 700,
                        whiteSpace: "nowrap",
                      }}
                    >
                      R{r}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rankings.map((p, idx) => (
                  <tr
                    key={p.playerId}
                    style={{
                      borderBottom: "1px solid var(--color-border)",
                      background:
                        idx % 2 === 0
                          ? "transparent"
                          : "var(--color-surface-raised)",
                    }}
                  >
                    <td
                      style={{
                        padding: "8px 12px",
                        fontWeight: 600,
                        whiteSpace: "nowrap",
                      }}
                    >
                      {p.nickname}
                    </td>
                    {rounds.map((r) => {
                      const num = state.allSubmissions![r]?.[p.playerId];
                      return (
                        <td
                          key={r}
                          style={{
                            padding: "8px 12px",
                            textAlign: "center",
                            fontVariantNumeric: "tabular-nums",
                          }}
                        >
                          {num != null ? num : "—"}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
