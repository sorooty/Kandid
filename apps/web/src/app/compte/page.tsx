import { getProfile } from "@kandid/db";
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Suspense } from "react";
import { signOut, updateProfile } from "@/app/actions/account";
import { AppHeader } from "@/components/app-header";
import { FormSkeleton } from "@/components/form-skeleton";
import { ProfileForm } from "@/components/forms/profile-form";
import { Button } from "@/components/ui/button";
import { asCurrentUser } from "@/lib/auth";
import { DeleteAccountForm } from "./delete-account-form";

export const metadata: Metadata = { title: "Mon compte | Kandid" };

const sectionClassName = "flex flex-col gap-4 rounded-lg border border-border bg-surface p-5";

export default function AccountPage() {
  return (
    <>
      <AppHeader />
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-6">
        <h1 className="text-3xl font-semibold tracking-tight">Mon compte</h1>

        <section className={sectionClassName} aria-labelledby="profile-title">
          <h2 id="profile-title" className="text-xl font-semibold">
            Ce que tu cherches
          </h2>
          <Suspense fallback={<FormSkeleton />}>
            <ProfileSection />
          </Suspense>
        </section>

        <section className={sectionClassName} aria-labelledby="data-title">
          <h2 id="data-title" className="text-xl font-semibold">
            Tes données
          </h2>
          <p className="text-muted">
            Télécharge tout ce que Kandid garde sur toi, dans un fichier JSON.
          </p>
          <a
            href="/compte/export"
            className="self-start rounded-lg border border-border px-5 py-2.5 font-medium hover:bg-background"
          >
            Exporter mes données
          </a>
        </section>

        <section className={sectionClassName} aria-labelledby="session-title">
          <h2 id="session-title" className="text-xl font-semibold">
            Session
          </h2>
          <form action={signOut}>
            <Button type="submit" variant="secondary">
              Me déconnecter
            </Button>
          </form>
        </section>

        <section className={sectionClassName} aria-labelledby="danger-title">
          <h2 id="danger-title" className="text-xl font-semibold text-destructive">
            Zone sensible
          </h2>
          <p className="text-muted">
            La suppression efface ton profil, tes candidatures et tes fichiers. On ne peut pas les
            récupérer ensuite.
          </p>
          <DeleteAccountForm />
        </section>
      </main>
    </>
  );
}

async function ProfileSection() {
  const profile = await asCurrentUser((tx, user) => getProfile(tx, user.id));
  if (!profile) redirect("/bienvenue");
  return (
    <ProfileForm
      action={updateProfile}
      submitLabel="Enregistrer"
      defaultValues={{
        firstName: profile.firstName,
        searchType: profile.searchType,
        school: profile.school ?? "",
        startDate: profile.startDate ?? "",
        workStudyRhythm: profile.workStudyRhythm ?? "",
      }}
    />
  );
}
