import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { SignInForm } from "./sign-in-form";

export const metadata: Metadata = { title: "Connexion | Kandid" };

const NOTICES: Record<string, string> = {
  lien: "Ce lien n'est plus valable. Demande-en un nouveau ci-dessous.",
  supprime: "Ton compte et toutes tes données ont été supprimés.",
};

export default function SignInPage({ searchParams }: PageProps<"/connexion">) {
  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center gap-6 p-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold tracking-tight">Connexion</h1>
        <p className="text-muted">
          Kandid est ouvert sur invitation. Entre ton adresse : on t'envoie un lien, sans mot de
          passe.
        </p>
      </div>
      <Suspense>
        <Notice searchParams={searchParams} />
      </Suspense>
      <SignInForm />
      <p className="text-sm text-muted">
        <Link href="/confidentialite" className="underline">
          Ce que Kandid fait de tes données
        </Link>
      </p>
    </main>
  );
}

async function Notice({ searchParams }: Pick<PageProps<"/connexion">, "searchParams">) {
  const { erreur, compte } = await searchParams;
  const key = erreur === "lien" ? "lien" : compte === "supprime" ? "supprime" : null;
  if (!key) return null;
  return (
    <p role="status" className="rounded-lg border border-border bg-surface p-3">
      {NOTICES[key]}
    </p>
  );
}
