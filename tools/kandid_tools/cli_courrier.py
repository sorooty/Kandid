"""`kandid courrier ...` and `kandid historique`: recruiter mails, past applications."""

from pathlib import Path
from typing import Annotated

import typer
from pydantic import TypeAdapter

from kandid_tools.cli_common import ConfigOpt, JsonOpt, new_app, user_errors
from kandid_tools.config import user_config
from kandid_tools.db import open_db
from kandid_tools.files import read_text
from kandid_tools.history import import_history, load_history
from kandid_tools.mail import Analysis, Kind, Mail, suggest

mail_app = new_app("Réponses des recruteurs lues dans ta boîte mail.")

KIND_LABELS = {
    Kind.REJECTION: "refus",
    Kind.INTERVIEW: "entretien",
    Kind.ACKNOWLEDGEMENT: "accusé de réception",
    Kind.OTHER: "autre",
}


def _analysis_text(analysis: Analysis) -> str:
    lines = [
        f"{len(analysis.suggestions)} mails, {analysis.ignored} alertes et newsletters ignorées"
    ]
    for item in analysis.suggestions:
        day = item.mail.date.date().isoformat() if item.mail.date else "date inconnue"
        what = KIND_LABELS[item.kind]
        if item.offer_id is None:
            lines.append(f"- {day} {what}, aucune candidature reconnue : {item.mail.subject}")
        elif item.target is None:
            lines.append(f"- {day} {what}, {item.company} (offre {item.offer_id}) : rien à changer")
        else:
            lines.append(
                f"- {day} {what}, {item.company} (offre {item.offer_id}) : "
                f"proposer {item.current.label if item.current else '?'} puis {item.target.label}"
            )
    return "\n".join(lines)


@mail_app.command("analyser")
def analyse(
    mails_path: Annotated[
        Path, typer.Argument(exists=True, dir_okay=False, help="mails.json écrit par le skill")
    ],
    config_path: ConfigOpt = None,
    as_json: JsonOpt = False,
) -> None:
    """Classe les mails (refus, entretien, accusé) et propose les statuts, sans rien changer."""
    with user_errors():
        config = user_config(config_path)
        mails = TypeAdapter(list[Mail]).validate_json(read_text(mails_path))
        analysis = suggest(open_db(config.paths.data), mails, config.mail)
    typer.echo(analysis.model_dump_json(indent=2) if as_json else _analysis_text(analysis))


def import_command(
    history_path: Annotated[
        Path, typer.Argument(exists=True, dir_okay=False, help="Candidatures passées, en JSON")
    ],
    config_path: ConfigOpt = None,
    as_json: JsonOpt = False,
) -> None:
    """Importe les candidatures envoyées avant Kandid ; une candidature déjà connue est ignorée."""
    with user_errors():
        items = load_history(history_path)
        report = import_history(open_db(user_config(config_path).paths.data), items)
    if as_json:
        typer.echo(report.model_dump_json(indent=2))
        return
    typer.echo(
        f"{len(report.added)} candidatures importées, {len(report.updated)} mises à jour, "
        f"{len(report.skipped)} déjà connues"
    )
    for label in report.skipped:
        typer.echo(f"  déjà connue : {label}")
