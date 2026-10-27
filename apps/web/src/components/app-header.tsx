import Link from "next/link";

export function AppHeader() {
  return (
    <header className="border-b border-border bg-surface">
      <nav className="mx-auto flex max-w-3xl items-center justify-between p-4">
        <Link href="/candidatures" className="text-xl font-semibold text-primary">
          Kandid
        </Link>
        <Link href="/compte" className="underline-offset-4 hover:underline">
          Mon compte
        </Link>
      </nav>
    </header>
  );
}
