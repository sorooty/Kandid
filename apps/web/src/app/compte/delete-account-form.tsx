"use client";

import { ACCOUNT_DELETION_CONFIRMATION } from "@kandid/core/profile/constants";
import { useActionState } from "react";
import { deleteAccount } from "@/app/actions/account";
import { Button } from "@/components/ui/button";
import { describedBy, Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { initialFormState } from "@/lib/form";

export function DeleteAccountForm() {
  const [state, formAction, pending] = useActionState(deleteAccount, initialFormState);
  const error = state.fieldErrors?.confirmation;
  const hint = `Tape ${ACCOUNT_DELETION_CONFIRMATION} pour confirmer. C'est définitif.`;

  return (
    <form action={formAction} className="flex flex-col gap-4" noValidate>
      <Field id="confirmation" label="Supprimer mon compte" hint={hint} error={error}>
        <Input
          id="confirmation"
          name="confirmation"
          autoComplete="off"
          spellCheck={false}
          {...describedBy("confirmation", { hint, error })}
        />
      </Field>
      {state.message && (
        <p role="alert" className="text-destructive">
          {state.message}
        </p>
      )}
      <Button type="submit" variant="destructive" disabled={pending} className="self-start">
        {pending ? "Suppression..." : "Supprimer définitivement"}
      </Button>
    </form>
  );
}
