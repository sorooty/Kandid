import { z } from "zod";

export type FormState = {
  status: "idle" | "error" | "success";
  message?: string;
  fieldErrors?: Partial<Record<string, string>>;
  // Echoed back so React's automatic form reset keeps what the user typed.
  values?: Record<string, string>;
};

export const initialFormState: FormState = { status: "idle" };

export function formValues(formData: FormData): Record<string, string> {
  const values: Record<string, string> = {};
  for (const [key, value] of formData) {
    if (typeof value === "string") values[key] = value;
  }
  return values;
}

export function firstFieldErrors(error: z.ZodError): Partial<Record<string, string>> {
  const { fieldErrors } = z.flattenError(error);
  const result: Partial<Record<string, string>> = {};
  for (const [field, messages] of Object.entries(fieldErrors)) {
    if (Array.isArray(messages) && messages[0]) result[field] = messages[0];
  }
  return result;
}
