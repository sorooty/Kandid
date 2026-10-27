import { createServerClient } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";

const PROTECTED_PREFIXES = ["/bienvenue", "/candidatures", "/compte"];

/**
 * Refreshes the Supabase session cookies on every request and sends signed-out visitors of
 * protected pages to sign-in. This is an optimistic check: pages verify the session again.
 */
export async function proxy(request: NextRequest) {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  // A misconfigured deployment should break the pages that need a session, not the public ones.
  if (!url || !key) return NextResponse.next({ request });

  let response = NextResponse.next({ request });

  const supabase = createServerClient(url, key, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll: (cookiesToSet, headers) => {
        for (const { name, value } of cookiesToSet) request.cookies.set(name, value);
        response = NextResponse.next({ request });
        for (const { name, value, options } of cookiesToSet) {
          response.cookies.set(name, value, options);
        }
        for (const [key, value] of Object.entries(headers)) response.headers.set(key, value);
      },
    },
  });

  const { data } = await supabase.auth.getClaims();
  const { pathname } = request.nextUrl;
  const isProtected = PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );

  if (isProtected && !data?.claims.sub) {
    return NextResponse.redirect(new URL("/connexion", request.url));
  }
  return response;
}

export const config = {
  // Skip static assets and images: they never need the session.
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};
