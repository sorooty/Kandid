import { describe, expect, it } from "vitest";
import { PROFILE_LIMITS } from "./constants";
import { accountDeletionSchema, profileInputSchema } from "./profile";

const valid = { firstName: "Camille", searchType: "work_study" };

describe("profileInputSchema", () => {
  it("accepts the two required fields and nulls the optional ones", () => {
    expect(profileInputSchema.parse(valid)).toEqual({
      firstName: "Camille",
      searchType: "work_study",
      school: null,
      startDate: null,
      workStudyRhythm: null,
    });
  });

  it("turns empty or blank form fields into null", () => {
    const parsed = profileInputSchema.parse({
      ...valid,
      school: "   ",
      startDate: "",
      workStudyRhythm: "",
    });
    expect(parsed.school).toBeNull();
    expect(parsed.startDate).toBeNull();
    expect(parsed.workStudyRhythm).toBeNull();
  });

  it("trims text fields", () => {
    const parsed = profileInputSchema.parse({ ...valid, firstName: "  Camille ", school: " IUT " });
    expect(parsed.firstName).toBe("Camille");
    expect(parsed.school).toBe("IUT");
  });

  it("rejects a blank first name", () => {
    expect(profileInputSchema.safeParse({ ...valid, firstName: "   " }).success).toBe(false);
  });

  it("rejects text over the limits", () => {
    const tooLong = "a".repeat(PROFILE_LIMITS.firstName + 1);
    expect(profileInputSchema.safeParse({ ...valid, firstName: tooLong }).success).toBe(false);
    const longSchool = "a".repeat(PROFILE_LIMITS.school + 1);
    expect(profileInputSchema.safeParse({ ...valid, school: longSchool }).success).toBe(false);
  });

  it("rejects an unknown search type", () => {
    expect(profileInputSchema.safeParse({ ...valid, searchType: "cdi" }).success).toBe(false);
  });

  it("accepts an ISO date and rejects anything else", () => {
    expect(profileInputSchema.parse({ ...valid, startDate: "2027-09-01" }).startDate).toBe(
      "2027-09-01",
    );
    expect(profileInputSchema.safeParse({ ...valid, startDate: "01/09/2027" }).success).toBe(false);
    expect(profileInputSchema.safeParse({ ...valid, startDate: "2027-02-30" }).success).toBe(false);
  });
});

describe("accountDeletionSchema", () => {
  it("only accepts the exact confirmation word", () => {
    expect(accountDeletionSchema.safeParse({ confirmation: "SUPPRIMER" }).success).toBe(true);
    expect(accountDeletionSchema.safeParse({ confirmation: "supprimer" }).success).toBe(false);
    expect(accountDeletionSchema.safeParse({ confirmation: "" }).success).toBe(false);
  });
});
