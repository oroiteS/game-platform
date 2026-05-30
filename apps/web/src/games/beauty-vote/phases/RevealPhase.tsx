import { useMemo } from "react";
import { Panel } from "../../../components/ui/Panel";
import { Button } from "../../../components/ui/Button";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { ScoreBoard } from "../ui/ScoreBoard";
import { RulePanel } from "../ui/RulePanel";
import { SettlementPanel } from "../ui/SettlementPanel";
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
          <p className="eyebrow">美人投票</p>
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
        <SettlementPanel state={state} playerId={playerId} />
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
