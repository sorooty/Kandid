import "server-only";
import { createServerClient } from "@supabase/ssr";
import { createClient } from "@supabase/supabase-js";
import { cookies } from "next/headers";
import { connection } from "next/server";
import { serverEnv } from "@/lib/env";

/** Supabase client bound to the visitor's session cookies. */
export async function createSessionClient() {
  // The auth client reads the clock when it loads the session: mark the render as request-time
  // first, or Cache Components rejects it during prerendering.
  await connection();
  const cookieStore = await cookies();
  return createServerClient(serverEnv.supabaseUrl, serverEnv.supabasePublishableKey, {
    cookies: {
      getAll: () => cookieStore.getAll(),
      setAll: (cookiesToSet) => {
        try {
          for (const { name, value, options } of cookiesToSet) {
            cookieStore.set(name, value, options);
          }
        } catch {
          // Server Components cannot set cookies; the proxy refreshes the session instead.
        }
      },
    },
  });
}

/** Privileged client for Auth admin calls (account deletion). Never reachable from the browser. */
export function createAdminClient() {
  return createClient(serverEnv.supabaseUrl, serverEnv.supabaseSecretKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
}
