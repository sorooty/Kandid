// Characters banned from every written deliverable (see CLAUDE.md, Writing).
// Built from code points so this file never contains the characters it bans
// (Biome rewrites \u escapes in regex literals into the raw characters).
const BANNED_RANGES = [
  [0x2013, 0x2014], // en dash, em dash
  [0x2190, 0x21ff], // arrows
  [0x27f0, 0x27ff], // supplemental arrows A
  [0x2900, 0x297f], // supplemental arrows B
  [0x25b2, 0x25b2], // triangles used as arrows
  [0x25b6, 0x25b6],
  [0x25ba, 0x25ba],
  [0x25bc, 0x25bc],
  [0x25c0, 0x25c0],
  [0x00b7, 0x00b7], // middle dot
  [0x2026, 0x2026], // ellipsis
  [0x2500, 0x257f], // box drawing
];

const toClass = ([from, to]) => `${String.fromCodePoint(from)}-${String.fromCodePoint(to)}`;

export const BANNED_CHARS = new RegExp(`[${BANNED_RANGES.map(toClass).join("")}]`, "u");

export function findBannedChars(text) {
  const hits = [];
  for (const [index, line] of text.split("\n").entries()) {
    const match = line.match(BANNED_CHARS);
    if (match) hits.push({ line: index + 1, char: match[0] });
  }
  return hits;
}
