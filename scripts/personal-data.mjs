// Spots user data that must never reach the public repository: data files by name, and email addresses or phone
// numbers in content. Fictional fixtures under examples/ and tests/ are allowed.

const FIXTURES = /^(examples|tests)\//;
// Lock files hold hashes, which look like numbers.
const LOCKS = /(^|\/)(uv\.lock|pnpm-lock\.yaml)$/;
// Case-insensitive: Windows does not care whether a file is called Profile.YAML. PDFs and Word files are CVs and
// letters until proven otherwise; repository images and docs use other formats.
const DATA_FILE =
  /(^|\/)(profile\.ya?ml|config\.ya?ml|letter\.ya?ml|spec\.ya?ml|\.env(\..*)?)$|\.(db|db-wal|db-shm|db-journal|sqlite3?|pdf|docx?|log)$|(^|\/)(\.kandid|applications|offres|import|logs)\//i;
const EMAIL = /[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}/g;
// Domains reserved for documentation (RFC 2606) and addresses that identify no one.
const SAFE_EMAIL = /@(example\.(com|org|net)|users\.noreply\.github\.com)$|^no-?reply@/i;
// French numbers, national or international form, with optional separators.
const PHONE = /(?<![\w+])(?:\+33[ .-]?|0)[1-9](?:[ .-]?\d{2}){4}(?!\w)/g;

export function isDataFile(path) {
  const normalized = path.replaceAll("\\", "/");
  return !FIXTURES.test(normalized) && DATA_FILE.test(normalized);
}

export function findPersonalData(path, content) {
  const normalized = path.replaceAll("\\", "/");
  if (FIXTURES.test(normalized) || LOCKS.test(normalized)) return [];
  const found = [];
  const searchable = normalized.toLowerCase().endsWith(".svg")
    ? content.replace(/\s+d=(["'])[\s\S]*?\1/g, "")
    : content;
  const lines = searchable.split("\n");
  lines.forEach((text, index) => {
    for (const [email] of text.matchAll(EMAIL)) {
      if (!SAFE_EMAIL.test(email)) found.push({ line: index + 1, kind: "adresse email" });
    }
    for (const _ of text.matchAll(PHONE))
      found.push({ line: index + 1, kind: "numéro de téléphone" });
  });
  return found;
}
