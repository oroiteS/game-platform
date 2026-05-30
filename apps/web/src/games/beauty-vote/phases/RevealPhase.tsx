import { useMemo } from "react";
import { Panel } from "../../../components/ui/Panel";
import { Button } from "../../../components/ui/Button";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { ScoreBoard } from "../ui/ScoreBoard";
import { RulePanel } from "../ui/RulePanel";
import { CalculationBox } from "../ui/CalculationBox";
import { EventBanner } from "../ui/EventBanner";
import { RuleChangeToast } from "../ui/RuleChangeToast";
import type { BeautyVoteState } from "../types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Props = {
  state: BeautyVoteState;
  playerId: string;
  onAction: (action: { type: string; payload?: unknown }) => boolean;
};

// ---------------------------------------------------------------------------
// RevealPhase — round result reveal
// ---------------------------------------------------------------------------

export function RevealPhase({ state, playerId, onAction }: Props) {
  const isAllSame = state.calculation?.method === "all_same";
  const isWinner = state.winnerIds.includes(playerId);
  const isFurthest = state.furthestIds.includes(playerId);

  const winnerNames = useMemo(() => {
    const names = state.winnerIds
      .map((id) => state.players.find((p) => p.playerId === id)?.nickname)
      .filter((n): n is string => n != null);
    return names;
  }, [state.winnerIds, state.players]);

  const playerStatus = useMemo(() => {
    if (isAllSame) return { text: "全体相同（扣2分）", tone: "danger" as const };
    if (isWinner) return { text: "获胜（不扣分）", tone: "success" as const };
    if (isFurthest) return { text: "最远（扣2分）", tone: "danger" as const };
    return { text: "扣1分", tone: "warning" as const };
  }, [isAllSame, isWinner, isFurthest]);

  const phaseBadge = useMemo(() => {
    if (isAllSame) return { text: "全体相同", tone: "danger" as const };
    if (isWinner) return { text: "获胜", tone: "success" as const };
    if (isFurthest) return { text: "最远", tone: "danger" as const };
    return { text: "参与", tone: "neutral" as const };
  }, [isAllSame, isWinner, isFurthest]);

  return (
    <section className="game-surface" aria-labelledby="bv-reveal-title">
      {/* Title area */}
      <div className="section-heading">
        <div>
          <p className="eyebrow">颜值投票</p>
          <h2 id="bv-reveal-title">
            第 {state.round} 回合 · 结果揭晓
          </h2>
        </div>
        <StatusBadge tone={phaseBadge.tone}>{phaseBadge.text}</StatusBadge>
      </div>

      {/* Special event banner */}
      <EventBanner event={state.specialEvent} />

      {/* Settlement panel */}
      <Panel>
        {/* Calculation display */}
        {state.calculation && <CalculationBox calc={state.calculation} />}

        {/* Key facts */}
        <dl className="room-facts">
          <div className="fact-row">
            <dt>T 值</dt>
            <dd>{state.currentT != null ? state.currentT : "—"}</dd>
          </div>
          <div className="fact-row">
            <dt>获胜者</dt>
            <dd>
              {winnerNames.length > 0 ? winnerNames.join("、") : "无"}
            </dd>
          </div>
          <div className="fact-row">
            <dt>你的状态</dt>
            <dd>
              <StatusBadge tone={playerStatus.tone}>
                {playerStatus.text}
              </StatusBadge>
            </dd>
          </div>
        </dl>
      </Panel>

      {/* ScoreBoard with winners highlighted */}
      <ScoreBoard players={state.players} highlightIds={state.winnerIds} />

      {/* Current rules */}
      {state.rulesDisplay !== null && (
        <RulePanel
          rules={state.rulesDisplay}
          hasHiddenRule={state.hasHiddenRule}
        />
      )}

      {/* Rule change toast */}
      <RuleChangeToast log={state.ruleLog} currentRound={state.round} />

      {/* Next round button — only shown during reveal phase */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <Button
          variant="primary"
          onClick={() => onAction({ type: "next_round" })}
        >
          进入下一回合
        </Button>
      </div>
    </section>
  );
}
