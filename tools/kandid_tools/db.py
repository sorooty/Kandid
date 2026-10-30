"""Local SQLite store of offers, applications and their history, in the user data folder."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, Column, Engine, UniqueConstraint, event
from sqlmodel import Field, Session, SQLModel, create_engine

from kandid_tools.status import Status

DB_NAME = "kandid.db"


def now() -> datetime:
    return datetime.now(UTC)


class Run(SQLModel, table=True):
    """One `kandid veille`: what each source returned and what was kept."""

    id: int | None = Field(default=None, primary_key=True)
    started_at: datetime = Field(default_factory=now, index=True)
    finished_at: datetime | None = None
    dry_run: bool = False
    # {source: {"fetched": n, "kept": n, "duplicates": n, "filtered": n, "error": str | None}}
    counts: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class Offer(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("source", "external_id"),)

    id: int | None = Field(default=None, primary_key=True)
    source: str = Field(index=True)
    external_id: str
    # Normalized company and title, to spot the same offer coming from another source.
    fingerprint: str = Field(index=True)
    company: str
    title: str
    location: str | None = None
    contract: str | None = Field(default=None, index=True)
    url: str | None = None
    description: str = ""
    published_at: datetime | None = Field(default=None, index=True)
    first_seen: datetime = Field(default_factory=now, index=True)
    score: int = Field(default=0, index=True)
    justification: str = ""
    points_to_check: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    # The same offer seen on other sources: [{"source": ..., "url": ...}].
    also_on: list[dict[str, str]] = Field(default_factory=list, sa_column=Column(JSON))
    run_id: int | None = Field(default=None, foreign_key="run.id", index=True)


class Application(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    offer_id: int = Field(foreign_key="offer.id", index=True, unique=True)
    status: Status = Field(default=Status.TO_REVIEW, index=True)
    created_at: datetime = Field(default_factory=now, index=True)
    updated_at: datetime = Field(default_factory=now, index=True)


class Event(SQLModel, table=True):
    """Timeline entry: status change, note, discard reason."""

    id: int | None = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="application.id", index=True)
    at: datetime = Field(default_factory=now, index=True)
    kind: str = Field(index=True)
    detail: str = ""


def _enable_foreign_keys(dbapi_connection: Any, _record: Any) -> None:
    # SQLite ignores foreign keys unless asked, connection by connection.
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def open_db(data_dir: Path) -> Engine:
    data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{(data_dir / DB_NAME).as_posix()}")
    event.listen(engine, "connect", _enable_foreign_keys)
    SQLModel.metadata.create_all(engine)
    return engine


def session(engine: Engine) -> Session:
    return Session(engine, expire_on_commit=False)
