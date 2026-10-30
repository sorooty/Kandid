import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { findPersonalData, isDataFile } from "./personal-data.mjs";

// "--all" checks every tracked file (CI); otherwise the staged files lefthook passes, which includes forced adds.
const all = process.argv[2] === "--all";
const files = all
  ? execFileSync("git", ["ls-files", "-z"], { encoding: "utf8" }).split("\0").filter(Boolean)
  : process.argv.slice(2);

// What the commit will hold, not the working copy, which may have been edited after staging.
function staged(file) {
  try {
    return execFileSync("git", ["show", `:${file}`], { stdio: ["ignore", "pipe", "ignore"] });
  } catch {
    return null;
  }
}

function read(file) {
  return existsSync(file) ? readFileSync(file) : null;
}

let failed = false;

for (const file of files) {
  if (isDataFile(file)) {
    console.error(`${file} : fichier de données utilisateur, il ne va jamais dans le dépôt.`);
    failed = true;
    continue;
  }
  const content = all ? read(file) : (staged(file) ?? read(file));
  if (content === null) continue;
  // Binary files (images) hold no searchable text.
  if (content.includes(0)) continue;
  for (const { line, kind } of findPersonalData(file, content.toString("utf8"))) {
    console.error(`${file}:${line} ${kind} hors des fixtures fictives (examples/, tests/).`);
    failed = true;
  }
}

if (failed) process.exit(1);
