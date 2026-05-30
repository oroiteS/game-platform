import { useMemo } from "react";
import type { BeautyVoteState } from "../types";

type Props = {
  state: BeautyVoteState;
  playerId: string;
};

const EVENT_LABELS: Record<string, string> = {
  number_storm: "数字风暴：所有数字被随机扰动±5",
  score_reset: "分数重置：所有分数被重置为平均值",
  anonymity_break: "匿名破除：本轮数字公开",
  double_points: "双倍积分：所有分数变动翻倍",
  lucky_exemption: "幸运豁免：随机一名玩家免于扣分",
};

export function SettlementPanel({ state, playerId }: Props) {
  const isAllSame = state.calculation?.method === "all_same";
  const winnerSet = new Set(state.winnerIds);
  const furthestSet = new Set(state.furthestIds);

  const alivePlayers = useMemo(
    () => state.players.filter((p) => p.alive),
    [state.players],
  );

  const hasExtraRules =
    state.activeRules.independent.length > 0 ||
    (state.activeRules.target_value !== null && state.calculation?.method !== "basic") ||
    state.activeRules.win_loss_alt !== null;

  const resultLabel = (pid: string) => {
    if (isAllSame) return { text: "全体相同", tone: "danger" as const };
    if (winnerSet.has(pid)) return { text: "获胜", tone: "success" as const };
    if (furthestSet.has(pid)) return { text: "最远", tone: "danger" as const };
    return null;
  };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      {/* Player numbers */}
      <div>
        <h4 style={{ margin: "0 0 8px", fontSize: "0.95rem" }}>本轮选择</h4>
        <div style={{ display: "grid", gap: 4 }}>
          {alivePlayers.map((p) => {
            const label = resultLabel(p.playerId);
            return (
              <div
                key={p.playerId}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "4px 8px",
                  borderRadius: 6,
                  background:
                    p.playerId === playerId
                      ? "var(--color-surface-high)"
                      : undefined,
                }}
              >
                <span>
                  {p.nickname}
                  {p.playerId === playerId ? "（你）" : ""}
                </span>
                <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontVariantNumeric: "tabular-nums" }}>
                    {p.lastNumber != null ? p.lastNumber : "—"}
                  </span>
                  {label && (
                    <span
                      style={{
                        fontSize: "0.8rem",
                        color:
                          label.tone === "success"
                            ? "var(--color-success)"
                            : "var(--color-danger)",
                      }}
                    >
                      [{label.text}]
                    </span>
                  )}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* T calculation */}
      {state.calculation && (
        <div>
          <h4 style={{ margin: "0 0 4px", fontSize: "0.95rem" }}>
            {state.calculation.label}
          </h4>
          <code
            style={{
              display: "block",
              fontSize: "0.85rem",
              color: "var(--color-text-muted)",
              padding: "6px 10px",
              background: "var(--color-surface-high)",
              borderRadius: 6,
              wordBreak: "break-all",
            }}
          >
            {state.calculation.detail}
          </code>
        </div>
      )}

      {/* Rule-specific effects */}
      {hasExtraRules && (
        <div style={{ display: "grid", gap: 8 }}>
          <h4 style={{ margin: 0, fontSize: "0.95rem" }}>规则效果</h4>

          {/* Rule 4: Forbidden number */}
          {state.forbiddenNumber != null && (
            <div
              style={{
                fontSize: "0.85rem",
                padding: "6px 10px",
                borderRadius: 6,
                background: "var(--color-danger-soft)",
              }}
            >
              禁区数字：<strong>{state.forbiddenNumber}</strong>
              {alivePlayers.some((p) => p.lastNumber === state.forbiddenNumber) &&
                ` — ${alivePlayers
                  .filter((p) => p.lastNumber === state.forbiddenNumber)
                  .map((p) => p.nickname)
                  .join("、")} 触发禁区惩罚（-3分）`}
            </div>
          )}

          {/* Rule 7: Inheritance */}
          {state.inheritedNumber != null && (
            <div
              style={{
                fontSize: "0.85rem",
                padding: "6px 10px",
                borderRadius: 6,
                background: "var(--color-surface-high)",
              }}
            >
              继承数字：<strong>{state.inheritedNumber}</strong>
              {alivePlayers.some(
                (p) => p.lastNumber === state.inheritedNumber,
              ) &&
                ` — ${alivePlayers
                  .filter((p) => p.lastNumber === state.inheritedNumber)
                  .map((p) => p.nickname)
                  .join("、")} 选择继承数字（失败仅扣1分）`}
            </div>
          )}

          {/* Rule 6: Leverage (own only) */}
          {state.mySubmission?.use_leverage && (
            <div
              style={{
                fontSize: "0.85rem",
                padding: "6px 10px",
                borderRadius: 6,
                background: "var(--color-surface-high)",
              }}
            >
              你使用了分数杠杆
              {winnerSet.has(playerId) ? "：获胜 +2分" : "：未获胜 -1分"}
            </div>
          )}

          {/* Rule 9: Betrayer (own only) */}
          {state.mySubmission?.betray_target && (
            <div
              style={{
                fontSize: "0.85rem",
                padding: "6px 10px",
                borderRadius: 6,
                background: "var(--color-surface-high)",
              }}
            >
              背叛目标：
              <strong>
                {state.players.find(
                  (p) => p.playerId === state.mySubmission?.betray_target,
                )?.nickname ?? state.mySubmission.betray_target}
              </strong>
              {furthestSet.has(state.mySubmission.betray_target)
                ? " — 猜中！你免扣分，其他玩家各-1分"
                : " — 未猜中，你额外-2分"}
            </div>
          )}

          {/* Rule 5: Reverse voting (own only) */}
          {state.mySubmission?.reverse_number != null && (
            <div
              style={{
                fontSize: "0.85rem",
                padding: "6px 10px",
                borderRadius: 6,
                background: "var(--color-surface-high)",
              }}
            >
              你的反向数字：<strong>{state.mySubmission.reverse_number}</strong>
            </div>
          )}

          {/* Special event */}
          {state.specialEvent && (
            <div
              style={{
                fontSize: "0.85rem",
                padding: "6px 10px",
                borderRadius: 6,
                background: "var(--color-surface-high)",
              }}
            >
              {EVENT_LABELS[state.specialEvent.type] ??
                state.specialEvent.type}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
