"use server";

import { redirect } from "next/navigation";
import { z } from "zod";
import { createSessionClient } from "@/lib/supabase/server";

// Only the link types our email templates send.
const confirmSchema = z.object({
  tokenHash: z.string().min(1).max(256),
  type: z.enum(["email", "invite"]),
});

/** Exchanges the emailed token hash for a session cookie. */
export async function confirmSignIn(formData: FormData): Promise<void> {
  const parsed = confirmSchema.safeParse({
    tokenHash: formData.get("tokenHash"),
    type: formData.get("type"),
  });
  if (!parsed.success) redirect("/connexion?erreur=lien");

  const supabase = await createSessionClient();
  const { error } = await supabase.auth.verifyOtp({
    token_hash: parsed.data.tokenHash,
    type: parsed.data.type,
  });
  // The tracking page sends first-time users on to onboarding.
  redirect(error ? "/connexion?erreur=lien" : "/candidatures");
}
