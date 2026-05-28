import type { ComponentPropsWithRef, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost";

type ButtonProps = ComponentPropsWithRef<"button"> & {
  variant?: ButtonVariant;
  children: ReactNode;
};

export function Button({ className, variant = "primary", children, ...props }: ButtonProps) {
  const classes = ["ui-button", `ui-button--${variant}`, className].filter(Boolean).join(" ");

  return (
    <button className={classes} {...props}>
      {children}
    </button>
  );
}
