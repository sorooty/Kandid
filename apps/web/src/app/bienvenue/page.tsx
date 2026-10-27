import { hasProfile } from "@kandid/db";
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Suspense } from "react";
import { completeOnboarding } from "@/app/actions/account";
import { FormSkeleton } from "@/components/form-skeleton";
import { ProfileForm } from "@/components/forms/profile-form";
import { PrivacyNotice } from "@/components/privacy-notice";
import { asCurrentUser } from "@/lib/auth";

export const metadata: Metadata = { title: "Bienvenue | Kandid" };

export default function WelcomePage() {
  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col gap-6 p-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold tracking-tight">Bienvenue sur Kandid</h1>
        <p className="text-muted">Dis-nous ce que tu cherches, ça prend moins d'une minute.</p>
      </div>
      <PrivacyNotice />
      <Suspense fallback={<FormSkeleton />}>
        <OnboardingForm />
      </Suspense>
    </main>
  );
}

async function OnboardingForm() {
  const done = await asCurrentUser((tx, user) => hasProfile(tx, user.id));
  if (done) redirect("/candidatures");
  return <ProfileForm action={completeOnboarding} submitLabel="C'est parti" />;
}
