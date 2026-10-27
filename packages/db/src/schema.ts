import { PROFILE_LIMITS, SEARCH_TYPES } from "@kandid/core";
import { sql } from "drizzle-orm";
import { check, date, pgEnum, pgPolicy, pgTable, text, timestamp, uuid } from "drizzle-orm/pg-core";
import { authenticatedRole, authUid, authUsers } from "drizzle-orm/supabase";

export const searchType = pgEnum("search_type", SEARCH_TYPES);

// No delete policy: accounts are deleted through the Auth admin API, and the cascade removes the profile.
export const profile = pgTable(
  "profile",
  {
    userId: uuid("user_id")
      .primaryKey()
      .references(() => authUsers.id, { onDelete: "cascade" }),
    firstName: text("first_name").notNull(),
    searchType: searchType("search_type").notNull().default("work_study"),
    school: text("school"),
    startDate: date("start_date"),
    workStudyRhythm: text("work_study_rhythm"),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [
    // Mirrors the zod limits, in case a row is written by anything other than the app.
    check(
      "profile_first_name_length",
      sql`char_length(${t.firstName}) between 1 and ${sql.raw(String(PROFILE_LIMITS.firstName))}`,
    ),
    check(
      "profile_school_length",
      sql`char_length(${t.school}) <= ${sql.raw(String(PROFILE_LIMITS.school))}`,
    ),
    check(
      "profile_work_study_rhythm_length",
      sql`char_length(${t.workStudyRhythm}) <= ${sql.raw(String(PROFILE_LIMITS.workStudyRhythm))}`,
    ),
    pgPolicy("profile_select_own", {
      for: "select",
      to: authenticatedRole,
      using: sql`${t.userId} = ${authUid}`,
    }),
    pgPolicy("profile_insert_own", {
      for: "insert",
      to: authenticatedRole,
      withCheck: sql`${t.userId} = ${authUid}`,
    }),
    pgPolicy("profile_update_own", {
      for: "update",
      to: authenticatedRole,
      using: sql`${t.userId} = ${authUid}`,
      withCheck: sql`${t.userId} = ${authUid}`,
    }),
  ],
);

export type Profile = typeof profile.$inferSelect;
