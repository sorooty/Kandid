"use server";

import { accountDeletionSchema, profileInputSchema } from "@kandid/core";
import { upsertProfile } from "@kandid/db";
import { redirect, unstable_rethrow } from "next/navigation";
import { asCurrentUser, getCurrentUser } from "@/lib/auth";
import { type FormState, firstFieldErrors, formValues } from "@/lib/form";
import { createAdminClient, createSessionClient } from "@/lib/supabase/server";

async function saveProfile(formData: FormData): Promise<FormState | null> {
  const values = formValues(formData);
  const parsed = profileInputSchema.safeParse(values);
  if (!parsed.success) {
    return {
      status: "error",
      message: "Vérifie les champs en rouge.",
      fieldErrors: firstFieldErrors(parsed.error),
      values,
    };
  }
  try {
    await asCurrentUser((tx, user) => upsertProfile(tx, user.id, parsed.data));
  } catch (error) {
    // Keeps the sign-in redirect working.
    unstable_rethrow(error);
    // Typically an account deleted from another device: its session token stays valid until expiry,
    // but the foreign key to the deleted user rejects the write.
    return {
      status: "error",
      message: "Impossible d'enregistrer. Reconnecte-toi puis réessaie.",
      values,
    };
  }
  return null;
}

export async function completeOnboarding(_: FormState, formData: FormData): Promise<FormState> {
  const failure = await saveProfile(formData);
  if (failure) return failure;
  redirect("/candidatures");
}

export async function updateProfile(_: FormState, formData: FormData): Promise<FormState> {
  const failure = await saveProfile(formData);
  return (
    failure ?? {
      status: "success",
      message: "Modifications enregistrées.",
      values: formValues(formData),
    }
  );
}

export async function signOut(): Promise<void> {
  const supabase = await createSessionClient();
  await supabase.auth.signOut();
  redirect("/connexion");
}

export async function deleteAccount(_: FormState, formData: FormData): Promise<FormState> {
  const parsed = accountDeletionSchema.safeParse(formValues(formData));
  if (!parsed.success) {
    return { status: "error", fieldErrors: firstFieldErrors(parsed.error) };
  }

  const user = await getCurrentUser();
  // Deleting the auth user cascades to every table keyed on it (ADR 0010).
  const { error } = await createAdminClient().auth.admin.deleteUser(user.id);
  if (error) {
    return { status: "error", message: "La suppression a échoué. Réessaie dans un instant." };
  }

  // The user no longer exists on the Auth server: only clear the local session cookies.
  const supabase = await createSessionClient();
  await supabase.auth.signOut({ scope: "local" });
  redirect("/connexion?compte=supprime");
}
