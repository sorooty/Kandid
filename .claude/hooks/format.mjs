// PostToolUse hook: formats the file Claude just edited (Biome for web files, Ruff for Python). Never blocks.
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { extname, join } from "node:path";

const BIOME_FORMATTABLE = new Set([
  ".js",
  ".mjs",
  ".cjs",
  ".ts",
  ".tsx",
  ".jsx",
  ".json",
  ".jsonc",
  ".css",
]);

const input = JSON.parse(readFileSync(0, "utf8"));
const file = input.tool_response?.filePath ?? input.tool_input?.file_path;
const root = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
const ext = file ? extname(file) : "";

if (BIOME_FORMATTABLE.has(ext)) {
  // Node launcher instead of the .cmd shim: no shell, so the path is never re-parsed.
  const biome = join(root, "node_modules", "@biomejs", "biome", "bin", "biome");
  spawnSync(process.execPath, [biome, "check", "--write", "--no-errors-on-unmatched", file], {
    cwd: root,
    stdio: "ignore",
  });
} else if (ext === ".py") {
  spawnSync("uv", ["run", "ruff", "format", file], { cwd: root, stdio: "ignore" });
}
