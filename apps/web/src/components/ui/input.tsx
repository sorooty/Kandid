import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

export const fieldClassName = cn(
  "h-11 w-full rounded-lg border border-border bg-surface px-3 text-foreground",
  "focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring",
  "aria-invalid:border-destructive",
);

export function Input({ className, ...props }: ComponentProps<"input">) {
  return <input className={cn(fieldClassName, className)} {...props} />;
}

export function Select({ className, ...props }: ComponentProps<"select">) {
  return <select className={cn(fieldClassName, className)} {...props} />;
}
