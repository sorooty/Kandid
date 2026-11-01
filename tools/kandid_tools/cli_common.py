"""What every `kandid` command module shares: app factory, options, user-facing errors."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Annotated, NoReturn

import typer
import yaml
from pydantic import ValidationError

from kandid_tools.latex import LatexError
from kandid_tools.pdftools import PopplerError


def new_app(help_text: str) -> typer.Typer:
    # Locals in a traceback would print the whole profile.
    return typer.Typer(no_args_is_help=True, help=help_text, pretty_exceptions_show_locals=False)


JsonOpt = Annotated[bool, typer.Option("--json", help="Sortie JSON")]
ConfigOpt = Annotated[
    Path | None, typer.Option("--config", exists=True, dir_okay=False, help="config.yaml")
]


def parse_day(value: str) -> datetime:
    """A calendar day typed by the user, at noon UTC so that it stays the same day in France."""
    try:
        return datetime.combine(date.fromisoformat(value), time(12), tzinfo=UTC)
    except ValueError:
        raise ValueError(f"date invalide : {value} (attendu AAAA-MM-JJ)") from None


def fail(message: str) -> NoReturn:
    typer.echo(message, err=True)
    raise typer.Exit(1)


def validation_message(error: ValidationError) -> str:
    # Field path and reason only: pydantic's default message quotes the input, i.e. CV text.
    rows = error.errors(include_input=False, include_url=False)
    return "fichier invalide :\n" + "\n".join(
        f"- {'.'.join(str(part) for part in row['loc'])} : {row['msg']}" for row in rows
    )


def yaml_message(error: yaml.YAMLError) -> str:
    mark = getattr(error, "problem_mark", None)
    where = f" ligne {mark.line + 1}, colonne {mark.column + 1}" if mark else ""
    return f"YAML illisible{where} : {getattr(error, 'problem', None) or 'syntaxe invalide'}"


@contextmanager
def user_errors() -> Iterator[None]:
    """Turn every expected failure into a one-line message and exit code 1, never a traceback."""
    try:
        yield
    except ValidationError as error:
        fail(validation_message(error))
    except yaml.YAMLError as error:
        fail(yaml_message(error))
    except (LatexError, PopplerError, ValueError, OSError) as error:
        fail(str(error))
