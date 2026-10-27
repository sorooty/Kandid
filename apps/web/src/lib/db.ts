import "server-only";
import { createDb, type Db } from "@kandid/db";
import { serverEnv } from "@/lib/env";

// One connection pool per server instance; dev hot reload would otherwise open a new pool per edit.
const globalForDb = globalThis as unknown as { kandidDb?: Db };

export function getDb(): Db {
  globalForDb.kandidDb ??= createDb(serverEnv.databaseUrl);
  return globalForDb.kandidDb;
}
