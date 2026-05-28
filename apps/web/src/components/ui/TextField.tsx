import type { InputHTMLAttributes } from "react";
import { FieldError } from "./FieldError";

type TextFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string | null;
  helpText?: string;
};

export function TextField({ id, label, error, helpText, className, ...props }: TextFieldProps) {
  const inputId = id ?? props.name;
  const errorId = inputId ? `${inputId}-error` : undefined;
  const helpId = inputId && helpText ? `${inputId}-hint` : undefined;
  const describedBy = [props["aria-describedby"], error ? errorId : null, helpId]
    .filter(Boolean)
    .join(" ");
  const classes = ["text-field__input", className].filter(Boolean).join(" ");

  return (
    <label className="text-field" htmlFor={inputId}>
      <span className="text-field__label">{label}</span>
      <input
        id={inputId}
        className={classes}
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy || undefined}
        {...props}
      />
      {helpText ? (
        <span className="text-field__help" id={helpId}>
          {helpText}
        </span>
      ) : null}
      <FieldError id={errorId} message={error} />
    </label>
  );
}
