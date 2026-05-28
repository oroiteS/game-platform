import type { HTMLAttributes, ReactNode } from "react";

type StatusTone = "neutral" | "success" | "warning" | "danger";

type StatusBadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: StatusTone;
  children: ReactNode;
};

export function StatusBadge({
  className,
  tone = "neutral",
  children,
  ...props
}: StatusBadgeProps) {
  const classes = ["status-badge", `status-badge--${tone}`, className].filter(Boolean).join(" ");

  return (
    <span className={classes} {...props}>
      {children}
    </span>
  );
}
