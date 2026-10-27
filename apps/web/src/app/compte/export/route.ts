import { getUserExport } from "@kandid/db";
import { asCurrentUser } from "@/lib/auth";

/** Downloads everything Kandid stores about the signed-in user (GDPR right of access). */
export async function GET() {
  const data = await asCurrentUser(async (tx, user) => ({
    // The email lives in Supabase Auth, not in our tables, but it is the user's data too.
    account: { email: typeof user.claims.email === "string" ? user.claims.email : null },
    ...(await getUserExport(tx, user.id)),
  }));
  const day = data.exportedAt.slice(0, 10);
  return new Response(JSON.stringify(data, null, 2), {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Content-Disposition": `attachment; filename="kandid-export-${day}.json"`,
      "Cache-Control": "private, no-store",
    },
  });
}
