import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { findBannedChars } from "./banned-chars.mjs";

const CHECKED = [
  "*.md",
  "*.py",
  "*.toml",
  "*.ts",
  "*.tsx",
  "*.js",
  "*.mjs",
  "*.json",
  "*.css",
  "*.yml",
  "*.yaml",
  "*.tmpl",
  "*.j2",
  "*.tex",
  "*.html",
  "*.txt",
];
const SKIPPED = [":!pnpm-lock.yaml", ":!uv.lock"];

// "--all" checks every tracked file, so CI and `pnpm check` need no shell-specific file listing.
// -z keeps accented paths unquoted; existsSync skips tracked files deleted but not yet staged.
const files =
  process.argv[2] === "--all"
    ? execFileSync("git", ["ls-files", "-z", "--", ...CHECKED, ...SKIPPED], { encoding: "utf8" })
        .split("\0")
        .filter((file) => file && existsSync(file))
    : process.argv.slice(2);

let failed = false;

for (const file of files) {
  for (const { line, char } of findBannedChars(readFileSync(file, "utf8"))) {
    console.error(`${file}:${line} caractère interdit "${char}" (voir CLAUDE.md, Writing).`);
    failed = true;
  }
}

if (failed) process.exit(1);
