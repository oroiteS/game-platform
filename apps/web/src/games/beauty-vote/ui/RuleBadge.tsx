import { useState, useRef, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import type { RuleInfo } from "../types";

type Props = {
  rule: RuleInfo;
};

export function RuleBadge({ rule }: Props) {
  const [open, setOpen] = useState(false);
  const badgeRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  const onClose = useCallback(() => {
    setOpen(false);
    window.requestAnimationFrame(() => badgeRef.current?.focus());
  }, []);

  // Focus trap and Escape
  useEffect(() => {
    if (!open) return;

    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", handler);
    window.requestAnimationFrame(() => closeRef.current?.focus());
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  return (
    <span style={{ position: "relative", display: "inline-block" }}>
      <button
        ref={badgeRef}
        type="button"
        onClick={() => setOpen(true)}
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

      {open &&
        createPortal(
          <div
            className="modal-backdrop"
            role="presentation"
            onMouseDown={(e) => {
              if (e.target === e.currentTarget) onClose();
            }}
          >
            <div
              className="modal-dialog"
              role="dialog"
              aria-modal="true"
              aria-label={rule.name}
            >
              <section className="game-detail-modal">
                <div className="modal-heading">
                  <div>
                    <p className="eyebrow">
                      规则 {rule.id}
                    </p>
                    <h2>{rule.name}</h2>
                  </div>
                  <button
                    ref={closeRef}
                    type="button"
                    className="ui-link-button"
                    onClick={onClose}
                  >
                    关闭
                  </button>
                </div>

                <div className="game-detail-body">
                  <div className="rules-text">
                    <p>{rule.description}</p>
                  </div>
                </div>
              </section>
            </div>
          </div>,
          document.body,
        )}
    </span>
  );
}
