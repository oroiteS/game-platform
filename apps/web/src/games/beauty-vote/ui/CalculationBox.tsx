import type { Calculation } from "../types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Props = {
  calc: Calculation;
};

// ---------------------------------------------------------------------------
// CalculationBox — displays calculation label + detail formula
// ---------------------------------------------------------------------------

export function CalculationBox({ calc }: Props) {
  return (
    <div
      aria-label="计算方式"
      style={{
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: 8,
        padding: "12px 16px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
        {/* Small colored circle representing the role */}
        <span
          style={{
            display: "inline-block",
            width: 12,
            height: 12,
            borderRadius: "50%",
            backgroundColor: "var(--color-primary)",
            flexShrink: 0,
          }}
        />
        <span style={{ fontWeight: 600, fontSize: "0.95rem" }}>{calc.label}</span>
      </div>
      <div
        style={{
          fontSize: "0.85rem",
          color: "var(--color-text-muted)",
          fontFamily: "monospace",
        }}
      >
        {calc.detail}
      </div>
    </div>
  );
}
