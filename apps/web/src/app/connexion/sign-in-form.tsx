"use client";

import { useActionState } from "react";
import { Button } from "@/components/ui/button";
import { describedBy, Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { initialFormState } from "@/lib/form";
import { requestSignInLink } from "./actions";

export function SignInForm() {
  const [state, formAction, pending] = useActionState(requestSignInLink, initialFormState);
  const error = state.fieldErrors?.email;

  return (
    <form action={formAction} className="flex flex-col gap-4" noValidate>
      <Field id="email" label="Ton adresse email" error={error}>
        <Input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          required
          defaultValue={state.values?.email}
          {...describedBy("email", { error })}
        />
      </Field>
      {state.message && (
        <p
          role={state.status === "error" ? "alert" : "status"}
          className={state.status === "error" ? "text-destructive" : "text-foreground"}
        >
          {state.message}
        </p>
      )}
      <Button type="submit" disabled={pending}>
        {pending ? "Envoi..." : "Recevoir mon lien"}
      </Button>
    </form>
  );
}
