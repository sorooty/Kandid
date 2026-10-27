import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

const VARIANTS = {
  primary: "bg-primary text-primary-foreground hover:opacity-90",
  secondary: "border border-border bg-surface text-foreground hover:bg-background",
  destructive: "bg-destructive text-destructive-foreground hover:opacity-90",
} as const;

type ButtonProps = ComponentProps<"button"> & { variant?: keyof typeof VARIANTS };

export function Button({ variant = "primary", className, type = "button", ...props }: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        "inline-flex h-11 items-center justify-center rounded-lg px-5 font-medium transition",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
        "disabled:cursor-not-allowed disabled:opacity-60",
        VARIANTS[variant],
        className,
      )}
      {...props}
    />
  );
}
