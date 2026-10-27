import { randomUUID } from "node:crypto";
import { sql } from "drizzle-orm";
import { afterAll, describe, expect, it } from "vitest";
import { createDb } from "./client";
import { LOCAL_DATABASE_URL } from "./test-env";

const db = createDb(process.env.DATABASE_URL ?? LOCAL_DATABASE_URL);
const authUrl = `${process.env.SUPABASE_URL ?? "http://127.0.0.1:54321"}/auth/v1`;

afterAll(() => db.$client.end());

describe("closed sign-up (ADR 0008)", () => {
  it("refuses a sign-in link to an address that was not invited, even through the raw Auth API", async () => {
    const key = process.env.SUPABASE_PUBLISHABLE_KEY;
    if (!key) throw new Error("Set SUPABASE_PUBLISHABLE_KEY, see the database job in ci.yml.");
    const email = `${randomUUID()}@example.test`;

    // Asks for account creation on purpose: an attacker would not send shouldCreateUser: false.
    const response = await fetch(`${authUrl}/otp`, {
      method: "POST",
      headers: { apikey: key, "Content-Type": "application/json" },
      body: JSON.stringify({ email, create_user: true }),
    });

    expect(response.ok).toBe(false);
    const users = await db.execute(sql`select 1 from auth.users where email = ${email}`);
    expect(users).toHaveLength(0);
  });
});
