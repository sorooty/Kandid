import Link from "next/link";

export function PrivacyNotice() {
  return (
    <aside className="rounded-lg border border-border bg-surface p-4 text-sm">
      <p className="font-medium">Tes données, en bref</p>
      <p className="mt-1 text-muted">
        Kandid garde ton profil et tes candidatures pour t'aider dans ta recherche, rien d'autre. La
        personne qui gère Kandid peut techniquement les voir, et ne le fait que pour corriger un
        problème. Tu peux tout exporter ou tout supprimer à tout moment depuis « Mon compte ».{" "}
        <Link href="/confidentialite" className="underline">
          En savoir plus
        </Link>
      </p>
    </aside>
  );
}
