import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Confidentialité | Kandid" };

export default function PrivacyPage() {
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-5 p-6">
      <h1 className="text-3xl font-semibold tracking-tight">Tes données sur Kandid</h1>
      <p>
        Kandid est un outil personnel, ouvert sur invitation à un petit groupe d'étudiants. Voici ce
        qu'il garde, pourquoi, et comment tu en restes maître.
      </p>
      <h2 className="text-xl font-semibold">Ce qui est stocké</h2>
      <p>
        Ton adresse email pour te connecter, et ce que tu renseignes : prénom, type de recherche,
        école, date de début, rythme d'alternance. Plus tard s'y ajouteront ton CV, les offres que
        tu importes, tes candidatures et tes lettres.
      </p>
      <h2 className="text-xl font-semibold">Où et qui y a accès</h2>
      <p>
        Les données sont hébergées dans l'Union européenne. Chaque utilisateur ne voit que ses
        propres données. La personne qui gère Kandid peut techniquement y accéder et ne le fait que
        pour corriger un problème. Rien n'est vendu ni partagé.
      </p>
      <h2 className="text-xl font-semibold">Tes droits</h2>
      <p>
        Depuis « Mon compte », tu peux exporter toutes tes données dans un fichier ou supprimer ton
        compte. La suppression est immédiate et définitive.
      </p>
      <Link href="/" className="self-start underline">
        Retour à l'accueil
      </Link>
    </main>
  );
}
