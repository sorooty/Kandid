"""Application factory and the guards that keep the API to the user's own browser (ADR 0015)."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Engine

from kandid_api.routes import router
from kandid_tools.bridge import mark_interrupted
from kandid_tools.config import Config
from kandid_tools.db import open_db

LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost"})
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def _refuse(status: int, message: str) -> JSONResponse:
    return JSONResponse({"detail": message}, status_code=status)


async def _local_only(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    host = request.headers.get("host", "")
    # A name other than localhost means DNS rebinding: a site whose domain now points here.
    if host.rsplit(":", 1)[0] not in LOCAL_HOSTS:
        return _refuse(400, "hôte refusé : l'API Kandid ne répond qu'en local")
    if request.method not in SAFE_METHODS:
        # A page from another site can post a form here, but not JSON without a CORS preflight,
        # which this API never answers; the Origin check covers browsers that send one anyway.
        if not request.headers.get("content-type", "").startswith("application/json"):
            return _refuse(415, "corps JSON attendu")
        origin = request.headers.get("origin")
        if origin is not None and origin != f"{request.url.scheme}://{host}":
            return _refuse(403, "origine refusée")
    return await call_next(request)


def create_app(
    config: Config,
    engine: Engine | None = None,
    claude: list[str] | None = None,
    plugin_dir: Path | None = None,
) -> FastAPI:
    """`claude` replaces the real binary in tests; `plugin_dir` loads a local plugin copy."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        mark_interrupted(app.state.engine)
        yield

    app = FastAPI(
        title="Kandid", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json"
    )
    app.state.config = config
    app.state.engine = engine or open_db(config.paths.data)
    app.state.claude = claude
    app.state.plugin_dir = plugin_dir
    app.middleware("http")(_local_only)
    app.include_router(router, prefix="/api")
    if FRONTEND_DIST.is_dir():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
    else:

        @app.get("/", include_in_schema=False)
        def home() -> dict[str, str]:
            return {
                "detail": "API Kandid en marche ; interface pas encore installée (voir /api/docs)."
            }

    return app
