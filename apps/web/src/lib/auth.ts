import "server-only";
import { type Tx, type UserClaims, withUser } from "@kandid/db";
import { redirect } from "next/navigation";
import { cache } from "react";
import { getDb } from "@/lib/db";
import { createSessionClient } from "@/lib/supabase/server";

export type CurrentUser = { id: string; claims: UserClaims };

/**
 * Data Access Layer entry point: verifies the session JWT and redirects to sign-in when it is
 * missing or expired. Deduplicated per request.
 */
export const getCurrentUser = cache(async (): Promise<CurrentUser> => {
  const supabase = await createSessionClient();
  const { data } = await supabase.auth.getClaims();
  const sub = data?.claims.sub;
  if (!sub) redirect("/connexion");
  return { id: sub, claims: { ...data.claims, sub } };
});

/** Runs `fn` against the database as the signed-in user, under RLS (ADR 0010). */
export async function asCurrentUser<T>(fn: (tx: Tx, user: CurrentUser) => Promise<T>): Promise<T> {
  const user = await getCurrentUser();
  return withUser(getDb(), user.claims, (tx) => fn(tx, user));
}
