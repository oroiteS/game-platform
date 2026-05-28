import type { HTMLAttributes, ReactNode } from "react";

type PanelProps = HTMLAttributes<HTMLElement> & {
  as?: "section" | "aside" | "div";
  children: ReactNode;
};

export function Panel({ as: Element = "section", className, children, ...props }: PanelProps) {
  const classes = ["ui-panel", className].filter(Boolean).join(" ");

  return (
    <Element className={classes} {...props}>
      {children}
    </Element>
  );
}
