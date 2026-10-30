"""`kandid` command line. Every command can print JSON for skills and the app; a failed check
exits with code 1 so a skill can stop on it."""

import io
import json
import sys
from datetime import date
from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel

from kandid_tools import ats, cli_setup, cli_ui, cli_watch, honesty, wrapcheck
from kandid_tools.cli_common import ConfigOpt, JsonOpt, fail, new_app, user_errors
from kandid_tools.config import user_config
from kandid_tools.files import is_inside, read_text
from kandid_tools.latex import compile_pdf
from kandid_tools.naming import document_folder, document_name
from kandid_tools.profile import Profile, load_profile
from kandid_tools.render_cv import render_cv
from kandid_tools.render_lm import load_letter, render_lm
from kandid_tools.spec import Spec, load_spec, spec_errors
from kandid_tools.status import Status, allowed_transitions, can_transition

app = new_app("Outils Kandid : rendu CV et lettre, ATS, contrôles.")
render_app = new_app("Génère un CV ou une lettre en .tex et .pdf.")
status_app = new_app("Statuts de candidature.")
app.add_typer(render_app, name="render")
app.add_typer(status_app, name="status")
app.add_typer(cli_watch.offer_app, name="offre")
app.command("veille")(cli_watch.veille)
app.command("offres")(cli_watch.offers)
app.command("suivi")(cli_watch.tracking_command)
app.command("bilan")(cli_watch.review_command)
app.command("chemins")(cli_watch.paths_command)
app.command("importer")(cli_setup.importer)
app.add_typer(cli_setup.setup_app, name="setup")
app.add_typer(cli_setup.tasks_app, name="taches")
app.command("ui")(cli_ui.ui)


@app.callback()
def _utf8_output() -> None:
    # Windows consoles and pipes default to a legacy code page; skills and the app read UTF-8.
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")


ProfileArg = Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="profile.yaml")]
SpecArg = Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="spec.yaml de l'offre")]
PdfArg = Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="PDF à contrôler")]
OutOpt = Annotated[Path, typer.Option("--out", file_okay=False, help="Dossier de sortie")]
DayOpt = Annotated[
    str | None, typer.Option("--date", help="Date du document (AAAA-MM-JJ), aujourd'hui par défaut")
]
TexOnlyOpt = Annotated[bool, typer.Option("--tex-only", help="Ne compile pas le PDF")]


def _day(value: str | None) -> date:
    try:
        return date.fromisoformat(value) if value else date.today()
    except ValueError:
        fail(f"date invalide : {value} (attendu AAAA-MM-JJ)")


def _print(report: BaseModel, as_json: bool, text: str) -> None:
    typer.echo(report.model_dump_json(indent=2) if as_json else text)


def _name(config: Path | None, doc: str, profile: Profile, spec: Spec, day: date) -> str:
    return document_name(
        user_config(config).naming,
        doc=doc,
        first_name=profile.identity.first_name,
        last_name=profile.identity.last_name,
        company=spec.offer.company,
        contract=spec.contract,
        role=spec.offer.role,
        lang=spec.lang,
        month=day,
    )


def _render(
    tex: str, *, doc: str, profile: Profile, spec: Spec, out: Path, day: date,
    config: Path | None, tex_only: bool, as_json: bool,
) -> None:  # fmt: skip
    """Check honesty on the generated text, then write the .tex and compile it."""
    report = honesty.check_text(honesty.untex(tex), profile, letter=doc == "LM")
    if not report.ok:
        # Same JSON shape as a success, so a skill parses one schema whatever the exit code.
        failure = {"tex": None, "pdf": None, "honesty": report.model_dump(mode="json")}
        typer.echo(json.dumps(failure, ensure_ascii=False) if as_json else honesty.to_text(report))
        raise typer.Exit(1)
    master = user_config(config).paths.master
    # The hook only sees the command line; the CLI refuses on its own, whatever spelling is used.
    if master is not None and is_inside(out, master):
        typer.echo(f"Le dossier maître ({master}) est en lecture seule pour Kandid.", err=True)
        raise typer.Exit(1)
    tex_path = out / f"{_name(config, doc, profile, spec, day)}.tex"
    tex_path.parent.mkdir(parents=True, exist_ok=True)
    tex_path.write_text(tex, encoding="utf-8")
    pdf_path = None if tex_only else compile_pdf(tex_path)
    result = {
        "tex": str(tex_path),
        "pdf": str(pdf_path) if pdf_path else None,
        "honesty": report.model_dump(mode="json"),
    }
    if as_json:
        typer.echo(json.dumps(result, ensure_ascii=False))
        return
    typer.echo("\n".join(str(p) for p in (tex_path, pdf_path) if p))
    if report.issues:
        typer.echo(honesty.to_text(report))


@render_app.command("cv")
def render_cv_command(
    profile_path: ProfileArg, spec_path: SpecArg, out: OutOpt, config: ConfigOpt = None,
    day: DayOpt = None, tex_only: TexOnlyOpt = False, as_json: JsonOpt = False,
) -> None:  # fmt: skip
    """CV de l'offre décrite par spec.yaml. Refusé si le contrôle d'honnêteté bloque."""
    with user_errors():
        profile, spec = load_profile(profile_path), load_spec(spec_path)
        _render(render_cv(profile, spec), doc="CV", profile=profile, spec=spec, out=out,
                day=_day(day), config=config, tex_only=tex_only, as_json=as_json)  # fmt: skip


@render_app.command("lm")
def render_lm_command(
    profile_path: ProfileArg, spec_path: SpecArg,
    letter_path: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="letter.yaml")],
    out: OutOpt, config: ConfigOpt = None, day: DayOpt = None, tex_only: TexOnlyOpt = False,
    as_json: JsonOpt = False,
) -> None:  # fmt: skip
    """Lettre de motivation, datée du jour. Refusée si le contrôle d'honnêteté bloque."""
    with user_errors():
        profile, spec = load_profile(profile_path), load_spec(spec_path)
        tex = render_lm(profile, load_letter(letter_path), spec.lang, _day(day))
        _render(tex, doc="LM", profile=profile, spec=spec, out=out, day=_day(day),
                config=config, tex_only=tex_only, as_json=as_json)  # fmt: skip


@app.command()
def validate(
    profile_path: ProfileArg,
    spec_path: Annotated[
        Path | None, typer.Argument(exists=True, dir_okay=False, help="spec.yaml (facultatif)")
    ] = None,
) -> None:
    """Vérifie le profil seul, ou qu'une spec ne cite que des éléments du profil."""
    with user_errors():
        profile = load_profile(profile_path)
        errors = spec_errors(load_spec(spec_path), profile) if spec_path else []
    if errors:
        fail("\n".join(errors))
    typer.echo("OK")


@app.command()
def name(
    profile_path: ProfileArg, spec_path: SpecArg,
    doc: Annotated[str, typer.Option(help="Type de document : CV, LM, Offre, ATS...")] = "CV",
    config: ConfigOpt = None, day: DayOpt = None, as_json: JsonOpt = False,
) -> None:  # fmt: skip
    """Nom de fichier et dossier de rangement d'un document."""
    with user_errors():
        profile, spec = load_profile(profile_path), load_spec(spec_path)
        file_name = _name(config, doc, profile, spec, _day(day))
        folder = document_folder(user_config(config).naming, doc=doc, contract=spec.contract)
    result = {"name": file_name, "folder": folder.as_posix()}
    typer.echo(json.dumps(result) if as_json else f"{folder.as_posix()}/{file_name}")


@app.command("ats")
def ats_command(
    pdf: PdfArg,
    offer: Annotated[
        Path | None, typer.Option(exists=True, dir_okay=False, help="Texte de l'offre")
    ] = None,
    company: Annotated[str | None, typer.Option(help="Entreprise, exclue des mots-clés")] = None,
    profile_path: Annotated[
        Path | None,
        typer.Option("--profile", exists=True, dir_okay=False, help="Pour vérifier la ville"),
    ] = None,
    as_json: JsonOpt = False,
) -> None:
    """Score ATS du CV, et correspondance avec l'offre si elle est fournie."""
    with user_errors():
        cities = [load_profile(profile_path).identity.city] if profile_path else []
        offer_text = read_text(offer) if offer else None
        report = ats.analyze(pdf, offer_text, company=company, cities=cities)
    _print(report, as_json, ats.to_text(report))


@app.command("wrapcheck")
def wrapcheck_command(pdf: PdfArg, as_json: JsonOpt = False) -> None:
    """Signale les lignes « Libellé : ... » qui passent à la ligne."""
    with user_errors():
        wrapped = wrapcheck.check(pdf)
    if as_json:
        typer.echo(json.dumps({"ok": not wrapped, "wrapped": wrapped}, ensure_ascii=False))
    else:
        typer.echo("OK : une ligne par libellé" if not wrapped else "Débordements :")
        for line in wrapped:
            typer.echo(f"  {line}")
    if wrapped:
        raise typer.Exit(1)


@app.command("honesty")
def honesty_command(
    profile_path: ProfileArg,
    document: Annotated[
        Path, typer.Argument(exists=True, dir_okay=False, help=".tex, .pdf, texte")
    ],
    letter: Annotated[
        bool, typer.Option("--letter", help="Lettre : un outil non pratiqué peut y être nommé")
    ] = False,
    as_json: JsonOpt = False,
) -> None:
    """Vérifie que le document ne cite rien d'absent du profil. Seuls les noms connus sont
    repérés : la liste d'outils fournie et unconfirmed_skills."""
    with user_errors():
        report = honesty.check_text(
            honesty.read_document(document), load_profile(profile_path), letter=letter
        )
    _print(report, as_json, honesty.to_text(report))
    if not report.ok:
        raise typer.Exit(1)


@status_app.command("check")
def status_check(current: Status, target: Status) -> None:
    """Vérifie qu'un passage d'un statut à l'autre est permis."""
    if not can_transition(current, target):
        fail(f"passage interdit : {current.label} vers {target.label}")
    typer.echo("OK")


@status_app.command("list")
def status_list(as_json: JsonOpt = False) -> None:
    """Statuts et passages permis."""
    rows = {
        s.value: {"label": s.label, "next": sorted(t.value for t in allowed_transitions(s))}
        for s in Status
    }
    if as_json:
        typer.echo(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    for key, row in rows.items():
        typer.echo(f"{key} ({row['label']}) : {', '.join(row['next']) or 'aucun'}")
