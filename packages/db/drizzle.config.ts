import { defineConfig } from "drizzle-kit";

export default defineConfig({
  dialect: "postgresql",
  schema: "./src/schema.ts",
  // Migrations land where the Supabase CLI applies them, named the way it expects.
  out: "../../supabase/migrations",
  migrations: { prefix: "supabase" },
  entities: { roles: { provider: "supabase" } },
});
