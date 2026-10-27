import type { Metadata } from "next";
import { Suspense } from "react";
import { Button } from "@/components/ui/button";
import { confirmSignIn } from "./actions";

// The URL carries a one-time token: never send it to another site.
export const metadata: Metadata = { title: "Connexion | Kandid", referrer: "no-referrer" };

/**
 * Landing page of the email links. The token is only used when the student clicks: mail scanners
 * that open links ahead of time (common on school mailboxes) would otherwise burn it.
 */
export default function ConfirmPage({ searchParams }: PageProps<"/auth/confirm">) {
  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center gap-6 p-6">
      <h1 className="text-3xl font-semibold tracking-tight">Connexion à Kandid</h1>
      <p className="text-muted">Clique sur le bouton pour terminer ta connexion.</p>
      <Suspense>
        <ConfirmForm searchParams={searchParams} />
      </Suspense>
    </main>
  );
}

async function ConfirmForm({ searchParams }: Pick<PageProps<"/auth/confirm">, "searchParams">) {
  const { token_hash: tokenHash, type } = await searchParams;
  return (
    <form action={confirmSignIn}>
      <input
        type="hidden"
        name="tokenHash"
        value={typeof tokenHash === "string" ? tokenHash : ""}
      />
      <input type="hidden" name="type" value={typeof type === "string" ? type : ""} />
      <Button type="submit">Me connecter</Button>
    </form>
  );
}
