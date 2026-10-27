import { sql } from "drizzle-orm";
import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "./schema";

export type Db = ReturnType<typeof createDb>;
export type Tx = Parameters<Parameters<Db["transaction"]>[0]>[0];

// Verified JWT claims of the signed-in user, as returned by Supabase Auth.
export type UserClaims = { sub: string } & Record<string, unknown>;

export function createDb(url: string) {
  // The Supabase pooler runs in transaction mode, which does not support prepared statements.
  const client = postgres(url, { prepare: false });
  return drizzle({ client, schema });
}

/**
 * Runs `fn` as the signed-in user: inside one transaction, with the `authenticated` role and the
 * user's JWT claims, so every RLS policy applies to every query (ADR 0010).
 */
export function withUser<T>(db: Db, claims: UserClaims, fn: (tx: Tx) => Promise<T>): Promise<T> {
  return db.transaction(async (tx) => {
    await tx.execute(
      sql`select set_config('request.jwt.claims', ${JSON.stringify(claims)}, true), set_config('role', 'authenticated', true)`,
    );
    return fn(tx);
  });
}
