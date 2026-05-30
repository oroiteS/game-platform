import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type RuleLogEntry = {
  unlocked: number;
  replaced: number | null;
  message: string;
  round: number;
};

type Props = {
  log: RuleLogEntry[];
  currentRound: number;
};

// ---------------------------------------------------------------------------
// RuleChangeToast — shows recent rule change, auto-dismisses after 5 seconds
// ---------------------------------------------------------------------------

export function RuleChangeToast({ log, currentRound }: Props) {
  const [visible, setVisible] = useState(false);
  const [message, setMessage] = useState("");
  const prevLogLength = useRef(log.length);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    // Detect new log entries
    if (log.length > prevLogLength.current) {
      const latest = log[log.length - 1];
      // Show if the log is for the current round or the previous round
      if (Math.abs(latest.round - currentRound) <= 1) {
        setMessage(latest.message);
        setVisible(true);

        // Auto-dismiss after 5 seconds
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => {
          setVisible(false);
        }, 5000);
      }
    }
    prevLogLength.current = log.length;

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [log, currentRound]);

  if (!visible) return null;

  return createPortal(
    <div
      role="status"
      aria-live="polite"
      style={{
        position: "fixed",
        top: 16,
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 1000,
        background: "var(--color-surface-high)",
        border: "1px solid var(--color-primary)",
        borderRadius: 12,
        padding: "12px 24px",
        boxShadow: "0 4px 24px rgba(0,0,0,0.2)",
        fontSize: "0.95rem",
        fontWeight: 600,
        textAlign: "center",
        maxWidth: "90vw",
        animation: "fadeIn 0.3s ease",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span>📜</span>
        <span>{message}</span>
      </div>
    </div>,
    document.body,
  );
}
