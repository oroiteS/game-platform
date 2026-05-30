import { useEffect, useRef } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Props = {
  seconds: number;
  onExpire?: () => void;
};

// ---------------------------------------------------------------------------
// Timer — 90-second countdown with progress bar
// ---------------------------------------------------------------------------

const TOTAL_SECONDS = 90;

export function Timer({ seconds, onExpire }: Props) {
  const expiredRef = useRef(false);

  // Notify parent when timer hits zero
  useEffect(() => {
    if (seconds <= 0 && !expiredRef.current) {
      expiredRef.current = true;
      onExpire?.();
    }
    // Reset the ref if timer restarts
    if (seconds > 0) {
      expiredRef.current = false;
    }
  }, [seconds, onExpire]);

  const isDanger = seconds <= 10 && seconds > 0;
  const isExpired = seconds <= 0;
  const progress = Math.max(0, Math.min(1, seconds / TOTAL_SECONDS));

  const barColor = isExpired
    ? "var(--color-danger)"
    : isDanger
      ? "var(--color-danger)"
      : "var(--color-primary)";

  return (
    <div aria-label={`剩余时间 ${seconds} 秒`} aria-live="polite">
      {/* Progress bar */}
      <div
        style={{
          width: "100%",
          height: 8,
          borderRadius: 4,
          backgroundColor: "var(--color-border)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${progress * 100}%`,
            height: "100%",
            borderRadius: 4,
            backgroundColor: barColor,
            transition: "width 0.3s linear, background-color 0.3s",
          }}
        />
      </div>

      {/* Seconds display */}
      <div
        style={{
          textAlign: "center",
          marginTop: 6,
          fontSize: "1.5rem",
          fontWeight: 700,
          fontVariantNumeric: "tabular-nums",
          color: isDanger || isExpired ? "var(--color-danger)" : "var(--color-text)",
        }}
      >
        {isExpired ? "时间到" : `${seconds}s`}
      </div>
    </div>
  );
}
