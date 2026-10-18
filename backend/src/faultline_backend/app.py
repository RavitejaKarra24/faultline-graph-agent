import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from . import configure_logging
from .config import Settings, workspace_slug
from .planner import investigate, new_id, timestamp
from .schemas import (
    Action,
    DependencyInput,
    ErrorResponse,
    GraphResponse,
    Health,
    Identifier,
    Investigation,
    InvestigationInput,
    InvestigationsResponse,
    MemoriesResponse,
    Memory,
    MemoryInput,
    SeedResponse,
    ServicesResponse,
    SessionId,
)
from .storage import APIError, Database, Store

logger = logging.getLogger(__name__)
MAX_BODY_BYTES = 16384


def error_response(status, code, message):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


class BoundedBodyMiddleware:
    """Cap even chunked requests before parsing JSON, without trusting Content-Length."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > MAX_BODY_BYTES:
                return await error_response(
                    413, "PAYLOAD_TOO_LARGE", "Request body must not exceed 16384 bytes."
                )(scope, receive, send)
            if not message.get("more_body", False):
                break
        sent = False

        async def replay():
            nonlocal sent
            if sent:
                return await receive()
            sent = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, replay, send)


def create_app(settings: Settings | None = None, database: Database | None = None):
    configure_logging()
    settings = settings or Settings()
    database = database or Database(settings)

    @asynccontextmanager
    async def lifespan(app):
        yield
        database.close()

    app = FastAPI(
        title="Faultline",
        version="0.1.0",
        lifespan=lifespan,
        description="Fictional local demo. Deterministic graph-tools planner; simulated approval only.",
        responses={code: {"model": ErrorResponse} for code in (400, 404, 413, 422, 500, 503)},
    )
    app.state.database = database
    app.add_middleware(BoundedBodyMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|\[::1\])(:[0-9]{1,5})?",
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "X-Workspace"],
        allow_credentials=False,
    )

    @app.exception_handler(APIError)
    async def api_error(request: Request, exc: APIError):
        return error_response(exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        details = "; ".join(".".join(map(str, e["loc"])) + ": " + e["msg"] for e in exc.errors())
        return error_response(422, "VALIDATION_ERROR", details[:1000])

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return error_response(
            exc.status_code,
            "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR",
            str(exc.detail),
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logger.exception("Unhandled backend error", exc_info=exc)
        return error_response(
            500, "INTERNAL_ERROR", "Unexpected backend error; inspect server logs."
        )

    def slug(x_workspace: Annotated[str, Header()] = "demo"):
        try:
            return workspace_slug(x_workspace)
        except ValueError as exc:
            raise APIError("INVALID_WORKSPACE", str(exc), 400) from exc

    def store(workspace: Annotated[str, Depends(slug)]):
        return database.workspace(workspace)

    WorkspaceStore = Annotated[Store, Depends(store)]

    @app.get("/api/health", response_model=Health, responses={503: {"model": Health}})
    def health(workspace: Annotated[str, Depends(slug)]):
        try:
            database.health()
        except APIError:
            return JSONResponse(
                status_code=503, content=Health(status="unavailable").model_dump(by_alias=True)
            )
        # Configuring a key does not make the planner an LLM. Each investigation
        # reports llm only if its optional summary synthesis actually succeeds.
        return Health(status="ok")

    @app.post("/api/seed", response_model=SeedResponse)
    def seed(db: WorkspaceStore):
        return db.seed()

    @app.get("/api/graph", response_model=GraphResponse, response_model_exclude_none=True)
    def graph(db: WorkspaceStore):
        db.ensure_seeded()
        return db.graph()

    @app.get("/api/services", response_model=ServicesResponse, response_model_exclude_none=True)
    def services(db: WorkspaceStore):
        db.ensure_seeded()
        return {"services": db.services()}

    @app.post("/api/investigations", response_model=Investigation)
    def create_investigation(body: InvestigationInput, db: WorkspaceStore):
        db.ensure_seeded()
        return investigate(db, body, settings)

    @app.get("/api/investigations", response_model=InvestigationsResponse)
    def investigations(
        db: WorkspaceStore, session_id: Annotated[SessionId | None, Query(alias="sessionId")] = None
    ):
        db.ensure_seeded()
        return {"investigations": db.investigations(session_id)}

    @app.post("/api/memories", response_model=Memory)
    def create_memory(body: MemoryInput, db: WorkspaceStore):
        db.ensure_seeded()
        return db.save_memory(Memory(**body.model_dump(), id=new_id("mem"), created_at=timestamp()))

    @app.get("/api/memories", response_model=MemoriesResponse)
    def memories(db: WorkspaceStore):
        db.ensure_seeded()
        return {"memories": db.memories()}

    @app.post("/api/actions/{id}/approve", response_model=Action)
    def approve_action(id: Annotated[Identifier, Path()], db: WorkspaceStore):
        db.ensure_seeded()
        return db.approve_action(id)

    @app.patch("/api/dependencies", response_model=DependencyInput)
    def toggle(body: DependencyInput, db: WorkspaceStore):
        db.ensure_seeded()
        return db.toggle_dependency(body.source, body.target, body.enabled)

    return app


app = create_app()
