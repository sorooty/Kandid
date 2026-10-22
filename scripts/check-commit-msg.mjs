import { readFileSync } from "node:fs";
import { findBannedChars } from "./banned-chars.mjs";

const TYPES = [
  "feat",
  "fix",
  "docs",
  "style",
  "refactor",
  "perf",
  "test",
  "build",
  "ci",
  "chore",
  "revert",
];
const pattern = new RegExp(`^(${TYPES.join("|")})(\\([a-z0-9-]+\\))?!?: .{1,100}$`);

// Lines starting with "#" are git's own template comments, not part of the message.
const message = readFileSync(process.argv[2], "utf8")
  .split("\n")
  .filter((line) => !line.startsWith("#"))
  .join("\n")
  .trim();
const firstLine = message.split("\n")[0];
const errors = [];

if (!pattern.test(firstLine) && !firstLine.startsWith("Merge ")) {
  errors.push(
    `Format Conventional Commits attendu, ex. "feat(web): ajoute le tableau de suivi". Reçu : "${firstLine}"`,
  );
}
if (/^co-authored-by:/im.test(message) || /generated with/i.test(message)) {
  errors.push(
    "Pas de co-auteur ni de mention d'outil : les commits sont signés par l'auteur seul.",
  );
}
for (const { line, char } of findBannedChars(message)) {
  errors.push(`Caractère interdit "${char}" ligne ${line} (voir CLAUDE.md, Writing).`);
}

if (errors.length > 0) {
  for (const error of errors) console.error(error);
  process.exit(1);
}
