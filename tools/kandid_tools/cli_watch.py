"""`kandid veille`, `kandid offres` and `kandid offre ...`: the offer watch and its inbox."""

import json
from datetime import timedelta
from pathlib import Path
from typing import Annotated

import typer

from kandid_tools.cli_common import ConfigOpt, JsonOpt, new_app, parse_day, user_errors
from kandid_tools.config import (
    CONFIG_NAME,
    PROFILE_NAME,
    WORK_DIR,
    Config,
    ContractKind,
    user_config,
)
from kandid_tools.db import now, open_db
from kandid_tools.dedup import fingerprint
from kandid_tools.files import read_text
from kandid_tools.profile import load_profile
from kandid_tools.scoring import profile_skills
from kandid_tools.sources.base import RawOffer
from kandid_tools.status import Status
from kandid_tools.tracking import (
    attach_document,
    change_status,
    follow_up,
    list_offers,
    offer_view,
    review,
)
from kandid_tools.watch import MANUAL, WatchReport, add_offer, run_watch

offer_app = new_app("Offres une à une : ajout manuel, mise à l'écart.")

ProfileOpt = Annotated[
    Path | None,
    typer.Option(
        "--profile", exists=True, dir_okay=False, help="profile.yaml, pour le score de compétences"
    ),
]
LIST_LIMIT = 50


def _skills(path: Path | None, config: Config) -> list[str]:
    path = path or config.paths.data / PROFILE_NAME
    if not path.is_file():
        typer.echo("profil introuvable : score sans les compétences", err=True)
        return []
    return profile_skills(load_profile(path))


def _report_text(report: WatchReport) -> str:
    lines = ["Simulation : rien n'est enregistré."] if report.dry_run else []
    for name, source in report.sources.items():
        if source.skipped or source.error:
            state = "ignorée" if source.skipped else "en erreur"
            lines.append(f"{name} : {state}, {source.skipped or source.error}")
        else:
            lines.append(
                f"{name} : {source.fetched} lues, {source.kept} gardées, "
                f"{source.duplicates} déjà vues, {source.filtered} écartées"
            )
    lines.append(f"{len(report.new)} nouvelle(s) offre(s)")
    lines += [
        f"  [{o.score}] {o.company} : {o.title} ({o.source}) {o.url or ''}".rstrip()
        for o in sorted(report.new, key=lambda o: -o.score)
    ]
    return "\n".join(lines)


def veille(
    source: Annotated[str | None, typer.Option(help="Une seule source")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="N'enregistre rien")] = False,
    config_path: ConfigOpt = None,
    profile_path: ProfileOpt = None,
    as_json: JsonOpt = False,
) -> None:
    """Interroge les sources activées et range les nouvelles offres dans « À voir »."""
    with user_errors():
        config = user_config(config_path)
        skills = _skills(profile_path, config)
        engine = open_db(config.paths.data)
        report = run_watch(config, engine, skills, only=source, dry_run=dry_run)
    typer.echo(report.model_dump_json(indent=2) if as_json else _report_text(report))


def offers(
    status: Annotated[
        Status | None,
        typer.Option(help="Filtre sur le statut ; sans lui, les archivées sont masquées"),
    ] = None,
    limit: Annotated[int, typer.Option(min=1, max=500)] = LIST_LIMIT,
    offset: Annotated[int, typer.Option(min=0, help="Offres à sauter (page suivante)")] = 0,
    config_path: ConfigOpt = None,
    as_json: JsonOpt = False,
) -> None:
    """Offres enregistrées, les mieux notées d'abord."""
    with user_errors():
        engine = open_db(user_config(config_path).paths.data)
        rows = list_offers(engine, status, limit, offset)
    if as_json:
        typer.echo(json.dumps([row.model_dump() for row in rows], ensure_ascii=False))
        return
    for row in rows:
        typer.echo(
            f"{row.id:>5} [{row.score:>3}] {row.status.label} : {row.company} : {row.title} "
            f"({row.source})"
        )


@offer_app.command("ajouter")
def add(
    company: Annotated[str, typer.Option("--entreprise", help="Entreprise")],
    title: Annotated[str, typer.Option("--titre", help="Intitulé du poste")],
    url: Annotated[str | None, typer.Option(help="Lien de l'offre")] = None,
    text: Annotated[
        Path | None,
        typer.Option("--texte", exists=True, dir_okay=False, help="Fichier du texte de l'offre"),
    ] = None,
    contract: Annotated[ContractKind | None, typer.Option("--contrat")] = None,
    location: Annotated[str | None, typer.Option("--lieu")] = None,
    config_path: ConfigOpt = None,
    profile_path: ProfileOpt = None,
    as_json: JsonOpt = False,
) -> None:
    """Ajoute une offre trouvée ailleurs, notée comme les autres."""
    with user_errors():
        config = user_config(config_path)
        offer = RawOffer(
            source=MANUAL,
            external_id=url or fingerprint(company, title),
            company=company,
            title=title,
            location=location,
            contract=contract,
            url=url,
            description=read_text(text) if text else "",
        )
        added = add_offer(open_db(config.paths.data), offer, config.watch,
                          _skills(profile_path, config))  # fmt: skip
    typer.echo(
        added.model_dump_json() if as_json else f"offre {added.id} ajoutée, score {added.score}"
    )


@offer_app.command("ecarter")
def discard(
    offer_id: Annotated[int, typer.Argument(help="Numéro de l'offre")],
    reason: Annotated[str, typer.Option("--raison", help="Pourquoi elle est écartée")],
    config_path: ConfigOpt = None,
) -> None:
    """Archive une offre ; la raison reste dans son historique."""
    with user_errors():
        engine = open_db(user_config(config_path).paths.data)
        change_status(engine, offer_id, Status.ARCHIVED, note=reason)
    typer.echo(f"offre {offer_id} écartée")


@offer_app.command("statut")
def set_status(
    offer_id: Annotated[int, typer.Argument(help="Numéro de l'offre")],
    target: Annotated[Status, typer.Argument(help="Nouveau statut")],
    note: Annotated[str, typer.Option("--note", help="Note pour l'historique")] = "",
    day: Annotated[
        str | None,
        typer.Option("--date", help="Jour du changement (AAAA-MM-JJ), aujourd'hui sinon"),
    ] = None,
    config_path: ConfigOpt = None,
) -> None:
    """Change le statut d'une candidature, si le passage est permis."""
    with user_errors():
        engine = open_db(user_config(config_path).paths.data)
        at = parse_day(day) if day else None
        previous = change_status(engine, offer_id, target, note=note, at=at)
    typer.echo(f"offre {offer_id} : {previous.label} puis {target.label}")


@offer_app.command("voir")
def show(
    offer_id: Annotated[int, typer.Argument(help="Numéro de l'offre")],
    config_path: ConfigOpt = None,
) -> None:
    """Offre, statut et historique, en JSON."""
    with user_errors():
        view = offer_view(open_db(user_config(config_path).paths.data), offer_id)
    typer.echo(view.model_dump_json(indent=2))


@offer_app.command("document")
def document(
    offer_id: Annotated[int, typer.Argument(help="Numéro de l'offre")],
    path: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="Fichier généré")],
    config_path: ConfigOpt = None,
) -> None:
    """Rattache un document généré (CV, lettre, rapport) à la candidature."""
    with user_errors():
        paths = user_config(config_path).paths
        attach_document(open_db(paths.data), offer_id, path, [paths.data, paths.applications_dir])
    typer.echo(f"document rattaché à l'offre {offer_id}")


def tracking_command(config_path: ConfigOpt = None, as_json: JsonOpt = False) -> None:
    """Candidatures en cours et prochaine action, les plus anciennes d'abord."""
    with user_errors():
        items = follow_up(open_db(user_config(config_path).paths.data), now())
    if as_json:
        typer.echo(json.dumps([i.model_dump(mode="json") for i in items], ensure_ascii=False))
        return
    for item in items:
        typer.echo(f"{item.id:>5} {item.status.label} depuis {item.days} j : {item.company}")
        typer.echo(f"      {item.title}\n      {item.action}")


def review_command(
    days: Annotated[int, typer.Option("--jours", min=1, help="Période, en jours")] = 7,
    config_path: ConfigOpt = None,
    as_json: JsonOpt = False,
) -> None:
    """Bilan de la période : offres trouvées, candidatures envoyées, réponses."""
    with user_errors():
        report = review(open_db(user_config(config_path).paths.data), now() - timedelta(days=days))
    if as_json:
        typer.echo(report.model_dump_json(indent=2))
        return
    rate = f"{report.answer_rate:.0%}" if report.answer_rate is not None else "sans objet"
    typer.echo(f"Sur {days} jours : {report.found} offres trouvées, {report.sent} candidatures "
               f"envoyées, {report.answered} réponses (taux {rate}).")  # fmt: skip


def paths_command(config_path: ConfigOpt = None) -> None:
    """Dossiers et fichiers de Kandid, en JSON : les skills s'en servent pour ne rien deviner."""
    with user_errors():
        config = user_config(config_path)
    paths = config.paths
    result = {
        "data": paths.data,
        "config": paths.data / CONFIG_NAME,
        "profile": paths.data / PROFILE_NAME,
        "work": paths.data / WORK_DIR,
        "applications": paths.applications_dir,
        "master": paths.master,
    }
    typer.echo(json.dumps({k: str(v) if v else None for k, v in result.items()}, indent=2))
