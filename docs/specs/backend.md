# Spec: local API and `claude -p` bridge

## Problem

Everything Kandid knows lives in SQLite and files, and every action goes through the `kandid` CLI or a slash command.
The CRM (phase 7) needs an HTTP layer over the same data, and a way to start a Claude run from a button and watch it
live. Scheduled tasks already run `claude -p`, but with a single JSON answer at the end: nothing shows while they run.

## User story

As a student, I run `kandid ui` (or double-click `Ouvrir Kandid.bat` in my data folder); my browser opens on the local
CRM. When I click "Préparer la candidature" on an offer, a Claude run starts and its steps show live in the journal;
when it ends I see its cost and duration, and the application has moved to "Prêt". Morning and evening tasks show in
the same journal.

## Scope

In:

- **Bridge** (`kandid_tools/bridge.py`), shared by the API and the scheduled tasks:
  - Runs `claude -p "<slash command>" --output-format stream-json --verbose` (the CLI refuses `stream-json` without
    `--verbose`), `--permission-mode dontAsk --permission-prompts none` (nobody answers prompts, `AskUserQuestion` is
    removed), `--max-turns`, `--max-budget-usd`, `--no-session-persistence`, from the data folder with `KANDID_HOME`
    set. No partial messages: one event per message is enough for a journal. Caps: `tasks` section of `config.yaml`
    for scheduled runs, new `ui` section (port, 80 turns, 3 $) for CRM runs, which prepare whole applications.
  - Only fixed actions, never free text: `veille`, `relance`, `digest`, `bilan` (no argument) and `postuler`, `cv`,
    `lm`, `prep-entretien` (one offer id, validated as an integer present in the database). The prompt is built from
    the action name and that integer only.
  - Allowed tools per action: `Bash(kandid *)` always; the offer actions also get `Edit(./**)` (the working folder,
    i.e. the data folder; Edit rules cover Write) and read access to the applications folder. Permission syntax to be
    checked in the docs before use.
  - Each stream line is parsed with pydantic, reduced and stored: assistant text, tool name with a short input
    summary (the `kandid` command line, a file path), tool error flag, permission denials, final result (status, cost,
    duration, turns, final text). Tool results are never stored: they carry profile and CV content (ADR 0005). The raw
    stream goes to `<data>/logs/` like today.
  - One run at a time: a second start is refused while one is running. A run can be stopped (process terminated, run
    marked `stopped`). On API start, runs left `running` by a crash are marked `interrupted`.
- **Database**: `TaskRun` (phase 5, not merged yet) becomes `ClaudeRun`: action, offer id, origin (`ui` or the task
  name), status (`running`, `ok`, `error`, `stopped`, `interrupted`), started/finished, cost, duration, turns, report
  path. New `ClaudeEvent` (run id, sequence, kind, text, tool, at), indexed on `(run_id, seq)`. The scheduler moves to
  the bridge, so its runs stream into the same tables; its report file and behavior stay the same.
- **API** (`app/backend/kandid_api`, FastAPI, thin over `kandid_tools`), JSON, French error messages:

  | Route | Use |
  |---|---|
  | `GET /api/statuts` | columns, labels, allowed moves (Kanban) |
  | `GET /api/offres?statut&limit&offset` | offer list (query moved from `kandid offres` to `tracking`, shared) |
  | `GET /api/offres/{id}` | offer sheet with timeline (`offer_view`) |
  | `POST /api/offres/{id}/statut` | move with optional note (`change_status`), 409 on a forbidden move |
  | `GET /api/suivi` | next actions (`follow_up`) |
  | `GET /api/bilan?jours=7` | review (`review`) |
  | `GET /api/taches` | task settings and the last run of each |
  | `GET /api/runs?limit&offset`, `GET /api/runs/{id}` | journal |
  | `POST /api/runs` `{action, offer_id?}` | start a run, 409 when one is running |
  | `GET /api/runs/{id}/events` | SSE (`fastapi.sse`, FastAPI 0.135+), resumes from `Last-Event-ID` |
  | `POST /api/runs/{id}/stop` | stop |

  Lists are paginated and select only the columns they show.
- **Local only**: uvicorn bound to `127.0.0.1`. Host header limited to `127.0.0.1`/`localhost` (blocks DNS rebinding);
  state-changing requests need `Content-Type: application/json` and, when an `Origin` header is present, the same
  origin (a web page the user visits cannot start a run or move an application). No CORS.
- **`kandid ui [--port 8765] [--no-browser]`**: starts the server, opens the browser once it listens. Serves the
  built frontend when it exists (phase 7), a short JSON pointer otherwise. `kandid ui --raccourci` writes
  `<data>/Ouvrir Kandid.bat` (same uv command as the scheduled tasks).
- Dependencies: `fastapi` and `uvicorn` (no `standard` extra), versions at least 14 days old.
- ADR 0015: local API security model and the event journal stored in SQLite.

Out (phase 7, added with the page that needs them): dashboard aggregates (weekly sends, funnel, heatmap, ATS
average), PDF preview and "open folder", profile and config editing, task hour editing, connector state.

## Acceptance criteria

- `pnpm check` green.
- Bridge tested with a fake `claude` (a Python script replaying a recorded, fictional `stream-json` file): events
  reduced and stored in order, tool results absent, cost and status recorded, refusal of a second run, stop,
  malformed lines, missing binary.
- API tested with FastAPI's `TestClient`: each route, pagination, forbidden move, Host and Origin checks, SSE replay
  from `Last-Event-ID`.
- Scheduler tests still pass on the bridge.
- By hand: `kandid ui` opens the browser; `POST /api/runs {"action": "bilan"}` shows its events live with `curl -N`.
