"""`kandid veille`, `kandid offres` and `kandid offre ...`: the offer watch and its inbox."""

import json
from pathlib import Path
from typing import Annotated

import typer
from sqlmodel import col, select

from kandid_tools.cli_common import ConfigOpt, JsonOpt, fail, new_app, user_errors
from kandid_tools.config import Config, ContractKind, default_data_dir, load_config
from kandid_tools.db import Application, Event, Offer, now, open_db, session
from kandid_tools.dedup import fingerprint
from kandid_tools.files import read_text
from kandid_tools.profile import load_profile
from kandid_tools.scoring import profile_skills
from kandid_tools.sources.base import RawOffer
from kandid_tools.status import Status, can_transition
from kandid_tools.watch import MANUAL, WatchReport, add_offer, run_watch

offer_app = new_app("Offres une à une : ajout manuel, mise à l'écart.")

ProfileOpt = Annotated[
    Path | None,
    typer.Option(
        "--profile", exists=True, dir_okay=False, help="profile.yaml, pour le score de compétences"
    ),
]
CONFIG_NAME = "config.yaml"
PROFILE_NAME = "profile.yaml"
LIST_LIMIT = 50


def _config(path: Path | None) -> Config:
    """The given file, else the one of the default data folder when it exists."""
    default = default_data_dir() / CONFIG_NAME
    return load_config(path or (default if default.is_file() else None))


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
        config = _config(config_path)
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
        engine = open_db(_config(config_path).paths.data)
        query = (
            select(
                Offer.id,
                Offer.score,
                Offer.company,
                Offer.title,
                Offer.source,
                Offer.url,
                Application.status,
            )
            .join(Application, col(Application.offer_id) == col(Offer.id))
            .order_by(col(Offer.score).desc(), col(Offer.first_seen).desc())
            .limit(limit)
            .offset(offset)
        )
        if status is None:
            query = query.where(Application.status != Status.ARCHIVED)
        else:
            query = query.where(Application.status == status)
        with session(engine) as db:
            rows = db.exec(query).all()
    keys = ("id", "score", "company", "title", "source", "url", "status")
    if as_json:
        typer.echo(
            json.dumps([dict(zip(keys, row, strict=True)) for row in rows], ensure_ascii=False)
        )
        return
    for offer_id, score, company, title, source, _url, row_status in rows:
        typer.echo(
            f"{offer_id:>5} [{score:>3}] {row_status.label} : {company} : {title} ({source})"
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
        config = _config(config_path)
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
        engine = open_db(_config(config_path).paths.data)
        with session(engine) as db:
            application = db.exec(
                select(Application).where(Application.offer_id == offer_id)
            ).first()
            if application is None:
                fail(f"offre {offer_id} introuvable")
            if not can_transition(application.status, Status.ARCHIVED):
                fail(f"offre {offer_id} déjà archivée")
            application.status = Status.ARCHIVED
            application.updated_at = now()
            assert application.id is not None
            db.add(Event(application_id=application.id, kind="discarded", detail=reason))
            db.commit()
    typer.echo(f"offre {offer_id} écartée")
