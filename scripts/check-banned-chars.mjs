import { readFileSync } from "node:fs";
import { findBannedChars } from "./banned-chars.mjs";

let failed = false;

for (const file of process.argv.slice(2)) {
  for (const { line, char } of findBannedChars(readFileSync(file, "utf8"))) {
    console.error(`${file}:${line} caractère interdit "${char}" (voir CLAUDE.md, Writing).`);
    failed = true;
  }
}

if (failed) process.exit(1);
