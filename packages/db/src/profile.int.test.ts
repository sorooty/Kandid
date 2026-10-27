import { randomUUID } from "node:crypto";
import type { ProfileInput } from "@kandid/core";
import { eq, sql } from "drizzle-orm";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { createDb, withUser } from "./client";
import { getProfile, getUserExport, upsertProfile } from "./profile";
import { profile } from "./schema";
import { LOCAL_DATABASE_URL } from "./test-env";

const db = createDb(process.env.DATABASE_URL ?? LOCAL_DATABASE_URL);
const alice = randomUUID();
const bob = randomUUID();

const claims = (sub: string) => ({ sub, role: "authenticated" });
const input = (firstName: string): ProfileInput => ({
  firstName,
  searchType: "work_study",
  school: null,
  startDate: null,
  workStudyRhythm: null,
});

async function createAuthUser(id: string) {
  await db.execute(sql`insert into auth.users (id, email) values (${id}, ${`${id}@example.test`})`);
}

beforeAll(async () => {
  await createAuthUser(alice);
  await createAuthUser(bob);
  await withUser(db, claims(alice), (tx) => upsertProfile(tx, alice, input("Alice")));
  await withUser(db, claims(bob), (tx) => upsertProfile(tx, bob, input("Bob")));
});

afterAll(async () => {
  await db.execute(sql`delete from auth.users where id in (${alice}, ${bob})`);
  await db.$client.end();
});

describe("profile RLS", () => {
  it("only returns the signed-in user's rows, even without a filter", async () => {
    const rows = await withUser(db, claims(alice), (tx) => tx.select().from(profile));
    expect(rows.map((row) => row.userId)).toEqual([alice]);
  });

  it("hides another user's profile", async () => {
    const row = await withUser(db, claims(alice), (tx) => getProfile(tx, bob));
    expect(row).toBeNull();
  });

  it("cannot update another user's profile", async () => {
    const updated = await withUser(db, claims(alice), (tx) =>
      tx.update(profile).set({ firstName: "Pirate" }).where(eq(profile.userId, bob)).returning(),
    );
    expect(updated).toEqual([]);
    const row = await withUser(db, claims(bob), (tx) => getProfile(tx, bob));
    expect(row?.firstName).toBe("Bob");
  });

  it("cannot write a profile for another user", async () => {
    await expect(
      withUser(db, claims(alice), (tx) => upsertProfile(tx, bob, input("Pirate"))),
    ).rejects.toThrow();
  });

  it("updates the signed-in user's profile", async () => {
    await withUser(db, claims(alice), (tx) => upsertProfile(tx, alice, input("Alicia")));
    const row = await withUser(db, claims(alice), (tx) => getProfile(tx, alice));
    expect(row?.firstName).toBe("Alicia");
  });
});

describe("account export and deletion", () => {
  it("exports the user's data and nothing from others", async () => {
    const own = await withUser(db, claims(alice), (tx) => getUserExport(tx, alice));
    expect(own.profile?.userId).toBe(alice);
    const other = await withUser(db, claims(alice), (tx) => getUserExport(tx, bob));
    expect(other.profile).toBeNull();
  });

  it("removes the profile when the auth user is deleted", async () => {
    const carol = randomUUID();
    await createAuthUser(carol);
    await withUser(db, claims(carol), (tx) => upsertProfile(tx, carol, input("Carol")));
    await db.execute(sql`delete from auth.users where id = ${carol}`);
    const rows = await db.select().from(profile).where(eq(profile.userId, carol));
    expect(rows).toEqual([]);
  });
});
