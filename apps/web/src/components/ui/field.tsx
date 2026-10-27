import type { ReactNode } from "react";

type FieldProps = {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  children: ReactNode;
};

/** Label, optional hint and error message wired to the control through `id`-based ids. */
export function Field({ id, label, hint, error, children }: FieldProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="font-medium">
        {label}
      </label>
      {hint && (
        <p id={`${id}-hint`} className="text-sm text-muted">
          {hint}
        </p>
      )}
      {children}
      {error && (
        <p id={`${id}-error`} className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}

/** Props that link a control to its Field hint and error. */
export function describedBy(id: string, { hint, error }: { hint?: string; error?: string }) {
  const ids = [hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(" ");
  return { "aria-describedby": ids || undefined, "aria-invalid": error ? true : undefined };
}
