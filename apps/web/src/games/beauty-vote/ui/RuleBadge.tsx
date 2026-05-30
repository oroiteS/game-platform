import { useState, useRef, useEffect, useCallback } from "react";
import type { RuleInfo } from "../types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Props = {
  rule: RuleInfo;
};

// ---------------------------------------------------------------------------
// RuleBadge — clickable rule tag with description popover
// ---------------------------------------------------------------------------

export function RuleBadge({ rule }: Props) {
  const [open, setOpen] = useState(false);
  const badgeRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  const toggle = useCallback(() => setOpen((v) => !v), []);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(e.target as Node) &&
        badgeRef.current &&
        !badgeRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open]);

  return (
    <span style={{ position: "relative", display: "inline-block" }}>
      <button
        ref={badgeRef}
        type="button"
        onClick={toggle}
        aria-expanded={open}
        style={{
          cursor: "pointer",
          border: "1px solid var(--color-border)",
          borderRadius: 12,
          padding: "2px 10px",
          fontSize: "0.85rem",
          background: "var(--color-surface)",
          color: "var(--color-text)",
          whiteSpace: "nowrap",
        }}
      >
        R{rule.id} {rule.name}
      </button>
      {open && (
        <div
          ref={popoverRef}
          role="tooltip"
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            marginTop: 4,
            zIndex: 100,
            background: "var(--color-surface-high)",
            border: "1px solid var(--color-border)",
            borderRadius: 8,
            padding: "10px 14px",
            maxWidth: 280,
            boxShadow: "0 4px 16px rgba(0,0,0,0.15)",
            fontSize: "0.9rem",
            lineHeight: 1.5,
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 4 }}>
            R{rule.id} {rule.name}
          </div>
          <div>{rule.description}</div>
        </div>
      )}
    </span>
  );
}
