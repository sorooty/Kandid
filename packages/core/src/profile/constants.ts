// No zod here: client components import this module, and the schemas must stay server side.

export const SEARCH_TYPES = ["work_study", "internship", "student_job"] as const;

export type SearchType = (typeof SEARCH_TYPES)[number];

export const PROFILE_LIMITS = {
  firstName: 50,
  school: 120,
  workStudyRhythm: 80,
} as const;

// Typed exactly, so a deletion is never triggered by a stray click or autofill.
export const ACCOUNT_DELETION_CONFIRMATION = "SUPPRIMER";
