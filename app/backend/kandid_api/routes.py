"""Routes of the CRM. Each one delegates to `kandid_tools`; none holds business logic."""

import asyncio
from collections.abc import AsyncIterable
from datetime import datetime, timedelta
from typing import Annotated

from anyio import to_thread
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, Field
from sqlalchemy import Engine
from sqlmodel import col, select

from kandid_tools.bridge import Action, BridgeError, Busy, Limits, RunStatus, start, stop
from kandid_tools.config import Config, TaskName
from kandid_tools.db import ClaudeEvent, ClaudeRun, now, session
from kandid_tools.status import Status, allowed_transitions
from kandid_tools.tracking import (
    FollowUp,
    NotFound,
    OfferRow,
    OfferView,
    Review,
    change_status,
    follow_up,
    list_offers,
    offer_view,
    review,
)

router = APIRouter()
# The journal page polls the database: a run writes a few events per second at most.
POLL_S = 0.5
PageLimit = Annotated[int, Query(ge=1, le=200)]
PageOffset = Annotated[int, Query(ge=0)]


def _engine(request: Request) -> Engine:
    return request.app.state.engine


def _config(request: Request) -> Config:
    return request.app.state.config


class StatusColumn(BaseModel):
    value: Status
    label: str
    next: list[Status]


class StatusMove(BaseModel):
    statut: Status
    note: str = Field(default="", max_length=2000)


class RunView(BaseModel):
    id: int
    action: str
    offer_id: int | None
    origin: str
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None
    cost_usd: float | None
    duration_ms: int | None
    turns: int | None


class EventView(BaseModel):
    seq: int
    at: datetime
    kind: str
    text: str
    tool: str | None


class TaskView(BaseModel):
    name: TaskName
    enabled: bool
    at: str
    last_run: RunView | None


class RunRequest(BaseModel):
    action: Action
    offer_id: int | None = Field(default=None, ge=1)


class Stopped(BaseModel):
    stopped: bool


def _run_view(run: ClaudeRun) -> RunView:
    return RunView.model_validate(run, from_attributes=True)


@router.get("/statuts")
def statuses() -> list[StatusColumn]:
    return [
        StatusColumn(
            value=s, label=s.label, next=sorted(allowed_transitions(s), key=list(Status).index)
        )
        for s in Status
    ]


@router.get("/offres")
def offers(
    request: Request,
    statut: Status | None = None,
    limit: PageLimit = 50,
    offset: PageOffset = 0,
) -> list[OfferRow]:
    return list_offers(_engine(request), statut, limit, offset)


@router.get("/offres/{offer_id}")
def offer(request: Request, offer_id: int) -> OfferView:
    try:
        return offer_view(_engine(request), offer_id)
    except NotFound as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from None


@router.post("/offres/{offer_id}/statut")
def move(request: Request, offer_id: int, body: StatusMove) -> OfferView:
    engine = _engine(request)
    try:
        change_status(engine, offer_id, body.statut, body.note)
    except NotFound as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from None
    except ValueError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None
    return offer_view(engine, offer_id)


@router.get("/suivi")
def tracking(request: Request) -> list[FollowUp]:
    return follow_up(_engine(request), now())


@router.get("/bilan")
def weekly(request: Request, jours: Annotated[int, Query(ge=1, le=365)] = 7) -> Review:
    return review(_engine(request), now() - timedelta(days=jours))


@router.get("/taches")
def tasks(request: Request) -> list[TaskView]:
    config = _config(request)
    views = []
    with session(_engine(request)) as db:
        for task in TaskName:
            last = db.exec(
                select(ClaudeRun)
                .where(ClaudeRun.origin == task.value)
                .order_by(col(ClaudeRun.started_at).desc())
                .limit(1)
            ).first()
            settings = config.tasks.settings(task)
            views.append(
                TaskView(
                    name=task,
                    enabled=settings.enabled,
                    at=settings.at,
                    last_run=_run_view(last) if last else None,
                )
            )
    return views


@router.get("/runs")
def runs(request: Request, limit: PageLimit = 50, offset: PageOffset = 0) -> list[RunView]:
    with session(_engine(request)) as db:
        rows = db.exec(
            select(ClaudeRun).order_by(col(ClaudeRun.started_at).desc()).limit(limit).offset(offset)
        ).all()
    return [_run_view(row) for row in rows]


def _get_run(engine: Engine, run_id: int) -> ClaudeRun:
    with session(engine) as db:
        run = db.get(ClaudeRun, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"run {run_id} introuvable")
    return run


@router.get("/runs/{run_id}")
def run(request: Request, run_id: int) -> RunView:
    return _run_view(_get_run(_engine(request), run_id))


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
def start_run(request: Request, body: RunRequest) -> RunView:
    config = _config(request)
    limits = Limits(max_turns=config.ui.max_turns, max_budget_usd=config.ui.max_budget_usd)
    try:
        started, _ = start(
            body.action,
            body.offer_id,
            config,
            _engine(request),
            limits,
            claude=request.app.state.claude,
            plugin_dir=request.app.state.plugin_dir,
        )
    except Busy as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None
    except BridgeError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from None
    return _run_view(started)


@router.post("/runs/{run_id}/stop")
def stop_run(request: Request, run_id: int) -> Stopped:
    _get_run(_engine(request), run_id)
    return Stopped(stopped=stop(run_id))


def _events_after(engine: Engine, run_id: int, seq: int) -> tuple[list[ClaudeEvent], bool]:
    """New events, and whether the run is over (read after them, so none is missed)."""
    with session(engine) as db:
        events = db.exec(
            select(ClaudeEvent)
            .where(ClaudeEvent.run_id == run_id, col(ClaudeEvent.seq) > seq)
            .order_by(col(ClaudeEvent.seq))
        ).all()
        current = db.get(ClaudeRun, run_id)
    return list(events), current is None or current.status != RunStatus.RUNNING


def _existing_run(request: Request, run_id: int) -> int:
    """Checked before the stream opens: once it has, the status code is already sent."""
    _get_run(_engine(request), run_id)
    return run_id


@router.get("/runs/{run_id}/events", response_class=EventSourceResponse)
async def run_events(
    request: Request,
    run_id: Annotated[int, Depends(_existing_run)],
    last_event_id: Annotated[int | None, Header()] = None,
) -> AsyncIterable[ServerSentEvent]:
    engine = _engine(request)
    seq = last_event_id if last_event_id is not None else -1
    while True:
        events, over = await to_thread.run_sync(_events_after, engine, run_id, seq)
        for event in events:
            seq = event.seq
            view = EventView.model_validate(event, from_attributes=True)
            yield ServerSentEvent(data=view, event=event.kind, id=str(event.seq))
        if over and not events:
            final = await to_thread.run_sync(_get_run, engine, run_id)
            yield ServerSentEvent(data=_run_view(final), event="end")
            return
        if await request.is_disconnected():
            return
        await asyncio.sleep(POLL_S)
