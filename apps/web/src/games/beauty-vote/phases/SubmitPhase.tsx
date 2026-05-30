import { useState, useEffect } from "react";
import { Button } from "../../../components/ui/Button";
import { Panel } from "../../../components/ui/Panel";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { NumberInput } from "../ui/NumberInput";
import { ScoreBoard } from "../ui/ScoreBoard";
import { RulePanel } from "../ui/RulePanel";
import { EventBanner } from "../ui/EventBanner";
import { Timer } from "../ui/Timer";
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
// SubmitPhase
// ---------------------------------------------------------------------------

export function SubmitPhase({ state, playerId, onAction }: Props) {
  const isSubmitted = state.mySubmission !== null;

  // Rule checks
  const hasRule5 = state.activeRules.target_value === 5;
  const hasRule6 = state.activeRules.independent.includes(6);
  const hasRule9 = state.activeRules.independent.includes(9);

  // Form state
  const [number, setNumber] = useState(50);
  const [reverseNumber, setReverseNumber] = useState(50);
  const [useLeverage, setUseLeverage] = useState(false);
  const [betrayTarget, setBetrayTarget] = useState<string>("");

  // Alive players excluding self (for betray target)
  const aliveOthers = state.players.filter(
    (p) => p.alive && p.playerId !== playerId,
  );

  // Set initial betray target to first alive other player
  useEffect(() => {
    if (hasRule9 && betrayTarget === "" && aliveOthers.length > 0) {
      setBetrayTarget(aliveOthers[0].playerId);
    }
  }, [hasRule9, aliveOthers, betrayTarget]);

  const handleSubmit = () => {
    const payload: Record<string, unknown> = {
      number,
      use_leverage: hasRule6 ? useLeverage : false,
    };
    if (hasRule5) {
      payload.reverse_number = reverseNumber;
    }
    if (hasRule9) {
      payload.betray_target = betrayTarget;
    }
    onAction({ type: "submit_number", payload });
  };

  const SUBMIT_TIMEOUT_SECONDS = 90;

  return (
    <section className="game-surface" aria-labelledby="bv-submit-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">美人投票</p>
          <h2 id="bv-submit-title">
            第 {state.round} 回合 — 提交阶段
          </h2>
        </div>
        <StatusBadge tone={isSubmitted ? "success" : "warning"}>
          {isSubmitted ? "已提交" : "未提交"}
        </StatusBadge>
      </div>

      {/* Special event banner */}
      <EventBanner event={state.specialEvent} />

      {/* Score board */}
      <div>
        <h3 style={{ marginBottom: 10 }}>当前分数</h3>
        <ScoreBoard players={state.players} />
      </div>

      {isSubmitted ? (
        /* Already submitted */
        <Panel>
          <p className="state-text" style={{ textAlign: "center", fontSize: "0.95rem" }}>
            已提交，等待其他玩家...
          </p>
          <p
            className="state-text"
            style={{ textAlign: "center", fontSize: "0.85rem" }}
          >
            请等待所有存活玩家提交
          </p>
        </Panel>
      ) : (
        /* Submission form */
        <div className="form-stack">
          {/* Forbidden / Inherited reminders */}
          {state.forbiddenNumber !== null && (
            <div
              style={{
                padding: "8px 12px",
                borderRadius: 6,
                border: "1px solid var(--color-danger)",
                background: "var(--color-danger-soft)",
                color: "var(--color-danger)",
                fontSize: "0.85rem",
                fontWeight: 600,
              }}
            >
              本轮禁区数字：{state.forbiddenNumber}（选择将被扣3分）
            </div>
          )}
          {state.inheritedNumber !== null && (
            <div
              style={{
                padding: "8px 12px",
                borderRadius: 6,
                border: "1px solid var(--color-primary)",
                background: "var(--color-primary-soft)",
                color: "var(--color-primary)",
                fontSize: "0.85rem",
                fontWeight: 600,
              }}
            >
              本轮继承数字：{state.inheritedNumber}（获胜+2分，失败固定-1分）
            </div>
          )}

          {/* Main number input */}
          <NumberInput
            value={number}
            onChange={setNumber}
            min={0}
            max={100}
            forbiddenNumber={state.forbiddenNumber}
            inheritedNumber={state.inheritedNumber}
          />

          {/* Rule 5: Reverse number */}
          {hasRule5 && (
            <NumberInput
              value={reverseNumber}
              onChange={setReverseNumber}
              min={0}
              max={100}
              forbiddenNumber={state.forbiddenNumber}
              inheritedNumber={state.inheritedNumber}
            />
          )}

          {/* Rule 6: Use leverage */}
          {hasRule6 && (
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "10px 0",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                checked={useLeverage}
                onChange={(e) => setUseLeverage(e.target.checked)}
                style={{ width: 18, height: 18, accentColor: "var(--color-primary)" }}
              />
              使用杠杆（获胜+2 / 失败-1）
            </label>
          )}

          {/* Rule 9: Betray target */}
          {hasRule9 && aliveOthers.length > 0 && (
            <div className="select-field">
              <label className="text-field__label">背叛目标</label>
              <select
                value={betrayTarget}
                onChange={(e) => setBetrayTarget(e.target.value)}
              >
                {aliveOthers.map((p) => (
                  <option key={p.playerId} value={p.playerId}>
                    {p.nickname}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Submit button */}
          <Button variant="primary" onClick={handleSubmit}>
            提交
          </Button>
        </div>
      )}

      {/* Current rules */}
      <div>
        <h3 style={{ marginBottom: 10 }}>当前规则</h3>
        <RulePanel
          rules={state.rulesDisplay}
          hasHiddenRule={state.hasHiddenRule}
        />
      </div>

      {/* Timer */}
      <Timer seconds={SUBMIT_TIMEOUT_SECONDS} />
    </section>
  );
}
