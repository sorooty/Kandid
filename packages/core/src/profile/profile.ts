import { z } from "zod";
import { ACCOUNT_DELETION_CONFIRMATION, PROFILE_LIMITS, SEARCH_TYPES } from "./constants";

// HTML forms send "" for an untouched optional field; the database stores NULL.
const emptyToNull = (value: unknown) =>
  typeof value === "string" && value.trim() === "" ? null : value;

const optionalText = (max: number) =>
  z.preprocess(
    emptyToNull,
    z
      .string()
      .trim()
      .max(max, { error: `${max} caractères maximum.` })
      .nullable()
      .default(null),
  );

export const profileInputSchema = z.object({
  firstName: z
    .string({ error: "Indique ton prénom." })
    .trim()
    .min(1, { error: "Indique ton prénom." })
    .max(PROFILE_LIMITS.firstName, { error: `${PROFILE_LIMITS.firstName} caractères maximum.` }),
  searchType: z.enum(SEARCH_TYPES, { error: "Choisis ce que tu cherches." }),
  school: optionalText(PROFILE_LIMITS.school),
  startDate: z.preprocess(
    emptyToNull,
    z.iso.date({ error: "Date invalide." }).nullable().default(null),
  ),
  workStudyRhythm: optionalText(PROFILE_LIMITS.workStudyRhythm),
});

export type ProfileInput = z.infer<typeof profileInputSchema>;

export const accountDeletionSchema = z.object({
  confirmation: z.literal(ACCOUNT_DELETION_CONFIRMATION, {
    error: `Tape ${ACCOUNT_DELETION_CONFIRMATION} pour confirmer.`,
  }),
});
