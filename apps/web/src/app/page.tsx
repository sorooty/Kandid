import Link from "next/link";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 p-6 text-center">
      <h1 className="text-4xl font-semibold tracking-tight text-primary">Kandid</h1>
      <p className="max-w-md text-lg">
        Stage, alternance ou job étudiant : Kandid prépare tes candidatures, tu gardes la main.
      </p>
      <Link
        href="/connexion"
        className="rounded-lg bg-primary px-5 py-2.5 font-medium text-primary-foreground hover:opacity-90"
      >
        Me connecter
      </Link>
    </main>
  );
}
