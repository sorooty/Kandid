export const APPLICATION_STATUSES = [
  "to_apply",
  "applied",
  "followed_up",
  "interview",
  "offer",
  "rejected",
  "no_response",
] as const;

export type ApplicationStatus = (typeof APPLICATION_STATUSES)[number];

// Terminal statuses can still be reopened: recruiters often come back after a silence or a "no".
const TRANSITIONS: Record<ApplicationStatus, readonly ApplicationStatus[]> = {
  to_apply: ["applied"],
  applied: ["followed_up", "interview", "offer", "rejected", "no_response"],
  followed_up: ["interview", "offer", "rejected", "no_response"],
  interview: ["interview", "offer", "rejected", "no_response"],
  offer: ["rejected"],
  rejected: ["interview", "offer"],
  no_response: ["followed_up", "interview", "offer", "rejected"],
};

export function canTransition(from: ApplicationStatus, to: ApplicationStatus): boolean {
  return TRANSITIONS[from].includes(to);
}
