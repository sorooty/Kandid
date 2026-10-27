import { getProfile } from "@kandid/db";
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Suspense } from "react";
import { AppHeader } from "@/components/app-header";
import { asCurrentUser } from "@/lib/auth";

export const metadata: Metadata = { title: "Mes candidatures | Kandid" };

export default function ApplicationsPage() {
  return (
    <>
      <AppHeader />
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 p-6">
        <Suspense fallback={<h1 className="text-3xl font-semibold tracking-tight">Bonjour</h1>}>
          <Greeting />
        </Suspense>
        <p className="text-muted">Le suivi de tes candidatures arrive très bientôt.</p>
      </main>
    </>
  );
}

async function Greeting() {
  const profile = await asCurrentUser((tx, user) => getProfile(tx, user.id));
  if (!profile) redirect("/bienvenue");
  return <h1 className="text-3xl font-semibold tracking-tight">Bonjour {profile.firstName}</h1>;
}
