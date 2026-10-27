"use server";

import { z } from "zod";
import type { FormState } from "@/lib/form";
import { createSessionClient } from "@/lib/supabase/server";

const signInSchema = z.object({
  email: z.email({ error: "Adresse email invalide." }).trim().toLowerCase(),
});

// Same answer whether or not the address was invited, so the form cannot be used to probe accounts.
const NEUTRAL_MESSAGE =
  "Si ton adresse est invitée, tu vas recevoir un lien de connexion. Pense à regarder tes spams.";

export async function requestSignInLink(_: FormState, formData: FormData): Promise<FormState> {
  const email = formData.get("email");
  const parsed = signInSchema.safeParse({ email });
  if (!parsed.success) {
    return {
      status: "error",
      fieldErrors: { email: "Adresse email invalide." },
      values: { email: typeof email === "string" ? email : "" },
    };
  }

  const supabase = await createSessionClient();
  // Sign-ups are closed (ADR 0008): only invited users get a link.
  const { error } = await supabase.auth.signInWithOtp({
    email: parsed.data.email,
    options: { shouldCreateUser: false },
  });

  // Only the per-IP limit is surfaced. The per-address limit (`over_email_send_rate_limit`) only
  // hits invited addresses, so showing it would reveal who is invited.
  if (error?.code === "over_request_rate_limit") {
    return { status: "error", message: "Trop de demandes. Réessaie dans une minute." };
  }
  return { status: "success", message: NEUTRAL_MESSAGE };
}
