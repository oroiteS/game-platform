import type { SpecialEvent } from "../types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Props = {
  event: SpecialEvent | null;
};

// ---------------------------------------------------------------------------
// Event type → Chinese description mapping
// ---------------------------------------------------------------------------

const EVENT_LABELS: Record<SpecialEvent["type"], string> = {
  number_storm: "数字风暴：所有数字随机±5",
  score_reset: "分数重置：全员分数调整为平均值",
  anonymity_break: "匿名失效：本轮数字将公开",
  double_points: "双倍积分：所有扣分得分翻倍",
  lucky_exemption: "幸运豁免：随机一名玩家不扣分",
};

// ---------------------------------------------------------------------------
// EventBanner — special event announcement banner
// ---------------------------------------------------------------------------

export function EventBanner({ event }: Props) {
  if (event === null) return null;

  const label = EVENT_LABELS[event.type] ?? `未知事件: ${event.type}`;

  return (
    <div
      role="alert"
      aria-label="特殊事件"
      style={{
        background: "var(--color-primary-soft)",
        border: "1px solid var(--color-primary)",
        borderRadius: 8,
        padding: "10px 16px",
        textAlign: "center",
        fontWeight: 600,
        fontSize: "0.95rem",
        color: "var(--color-primary)",
      }}
    >
      ⚡ {label}
    </div>
  );
}
