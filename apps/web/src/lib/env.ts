import "server-only";

function required(name: string, value: string | undefined): string {
  if (!value) throw new Error(`Missing environment variable ${name} (see .env.example).`);
  return value;
}

// Read lazily so a missing variable fails the request that needs it, not the build.
export const serverEnv = {
  get supabaseUrl() {
    return required("NEXT_PUBLIC_SUPABASE_URL", process.env.NEXT_PUBLIC_SUPABASE_URL);
  },
  get supabasePublishableKey() {
    return required(
      "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
      process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY,
    );
  },
  get supabaseSecretKey() {
    return required("SUPABASE_SECRET_KEY", process.env.SUPABASE_SECRET_KEY);
  },
  get databaseUrl() {
    return required("DATABASE_URL", process.env.DATABASE_URL);
  },
};
