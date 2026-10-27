import type { ProfileInput } from "@kandid/core";
import { eq, sql } from "drizzle-orm";
import type { Tx } from "./client";
import { profile } from "./schema";

// All functions take a transaction opened by `withUser`, so RLS scopes them to the signed-in user.

export async function getProfile(tx: Tx, userId: string) {
  const [row] = await tx.select().from(profile).where(eq(profile.userId, userId)).limit(1);
  return row ?? null;
}

export async function hasProfile(tx: Tx, userId: string): Promise<boolean> {
  const [row] = await tx
    .select({ userId: profile.userId })
    .from(profile)
    .where(eq(profile.userId, userId))
    .limit(1);
  return row !== undefined;
}

export async function upsertProfile(tx: Tx, userId: string, input: ProfileInput): Promise<void> {
  await tx
    .insert(profile)
    .values({ userId, ...input })
    .onConflictDoUpdate({ target: profile.userId, set: { ...input, updatedAt: sql`now()` } });
}

/** Everything Kandid stores about the user. Later specs add their tables here. */
export async function getUserExport(tx: Tx, userId: string) {
  return {
    exportedAt: new Date().toISOString(),
    profile: await getProfile(tx, userId),
  };
}
