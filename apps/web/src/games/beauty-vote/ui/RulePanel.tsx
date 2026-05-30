import type { RuleInfo } from "../types";
import { RuleBadge } from "./RuleBadge";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Props = {
  rules: RuleInfo[] | null;
  hasHiddenRule: boolean;
};

// ---------------------------------------------------------------------------
// RulePanel — displays current rules with hidden-rule indicator
// ---------------------------------------------------------------------------

export function RulePanel({ rules, hasHiddenRule }: Props) {
  const hasVisibleRules = rules !== null && rules.length > 0;

  return (
    <div aria-label="当前规则面板">
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
        {/* Hidden rule badge (always shown when hasHiddenRule is true) */}
        {hasHiddenRule && (
          <span
            aria-label="存在隐藏规则"
            title="存在隐藏规则，暂不可见"
            style={{
              cursor: "not-allowed",
              border: "1px dashed var(--color-border)",
              borderRadius: 12,
              padding: "2px 10px",
              fontSize: "0.85rem",
              color: "var(--color-text-muted)",
              whiteSpace: "nowrap",
              opacity: 0.7,
            }}
          >
            🔒 隐藏规则
          </span>
        )}

        {/* Visible rule badges */}
        {hasVisibleRules &&
          rules.map((r) => <RuleBadge key={r.id} rule={r} />)}

        {/* Empty state: no visible rules and no hidden rule */}
        {!hasVisibleRules && !hasHiddenRule && (
          <p className="state-text">暂无动态规则生效</p>
        )}
      </div>
    </div>
  );
}
