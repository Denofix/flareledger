"""NASA corpus browsing with optional bounded, source-linked Gemini explanations."""

import sqlite3
from collections.abc import Iterator
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.ask import AskService
from app.ask_body import AskBodyLimit
from app.config import Settings
from app.llm import LLMSettings, Provider
from app.storage import CorpusUnavailable, Repository

RecordType = Literal[
    "trial_row",
    "flow_visualization_record",
    "source_note",
    "condition_definition",
    "condition_reference",
    "operating_condition_row",
]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


class Page(BaseModel):
    items: list[dict[str, Any]]
    total: int
    limit: int
    offset: int


class Detail(BaseModel):
    item: dict[str, Any]
    sources: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    quality_issues: list[dict[str, Any]]


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=1000)


def create_app(
    settings: Settings | None = None,
    llm_settings: LLMSettings | None = None,
    provider: Provider | None = None,
) -> FastAPI:
    repository = Repository(settings or Settings.from_env())
    ask_service = AskService(repository, llm_settings or LLMSettings.from_env(), provider)
    api = FastAPI(
        title="FlareLedger API",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    api.add_middleware(AskBodyLimit)

    @api.exception_handler(CorpusUnavailable)
    async def unavailable(_request: Request, exc: CorpusUnavailable) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "error": {"code": "corpus_unavailable", "message": str(exc)},
            },
        )

    @api.middleware("http")
    async def disable_api_cache(request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    def connection() -> Iterator[sqlite3.Connection]:
        with repository.connection() as value:
            yield value

    Database = Annotated[sqlite3.Connection, Depends(connection)]

    def find(database: sqlite3.Connection, kind: str, identifier: str) -> dict:
        item = repository.item(database, kind, identifier)
        if item is None:
            raise HTTPException(404, detail={"code": "not_found", "kind": kind, "id": identifier})
        return item

    def check_scope(database: sqlite3.Connection, identifier: str | None) -> None:
        if identifier is not None:
            find(database, "investigation", identifier)

    @api.get("/api/health/live")
    def live() -> dict:
        return {"status": "ok"}

    @api.get("/api/health/ready")
    def ready() -> dict:
        metadata = repository.readiness()
        return {"status": "ready", "corpus_version": metadata["corpus_version"]}

    @api.get("/api/meta")
    def meta(database: Database) -> dict:
        return {**repository.metadata(database), "live_generation_available": ask_service.available}

    @api.get("/api/investigations", response_model=Page)
    def investigations(database: Database, limit: Limit = 20, offset: Offset = 0) -> dict:
        return repository.page(database, "investigation", limit, offset)

    @api.get("/api/investigations/{identifier}", response_model=Detail)
    def investigation(identifier: str, database: Database) -> dict:
        return repository.detail(database, "investigation", find(database, "investigation", identifier))

    @api.get("/api/records", response_model=Page)
    def records(
        database: Database,
        investigation_id: str | None = None,
        record_type: RecordType | None = None,
        limit: Limit = 20,
        offset: Offset = 0,
    ) -> dict:
        check_scope(database, investigation_id)
        return repository.page(database, "record", limit, offset, investigation_id, record_type)

    @api.get("/api/trials", response_model=Page)
    def trials(
        database: Database, investigation_id: str | None = None, limit: Limit = 20, offset: Offset = 0
    ) -> dict:
        check_scope(database, investigation_id)
        return repository.page(database, "record", limit, offset, investigation_id, "trial_row")

    @api.get("/api/records/{identifier}", response_model=Detail)
    def record(identifier: str, database: Database) -> dict:
        return repository.detail(database, "record", find(database, "record", identifier))

    @api.get("/api/series", response_model=Page)
    def series(
        database: Database, investigation_id: str | None = None, limit: Limit = 20, offset: Offset = 0
    ) -> dict:
        check_scope(database, investigation_id)
        return repository.page(database, "series", limit, offset, investigation_id)

    @api.get("/api/series/{identifier}", response_model=Detail)
    def measured_series(identifier: str, database: Database) -> dict:
        return repository.detail(database, "series", find(database, "series", identifier))

    @api.get("/api/sources", response_model=Page)
    def sources(database: Database, limit: Limit = 20, offset: Offset = 0) -> dict:
        return repository.page(database, "source", limit, offset)

    @api.get("/api/sources/{identifier}", response_model=Detail)
    def source(identifier: str, database: Database) -> dict:
        return repository.detail(database, "source", find(database, "source", identifier))

    @api.get("/api/evidence/{identifier}", response_model=Detail)
    def evidence(identifier: str, database: Database) -> dict:
        return repository.detail(database, "evidence", find(database, "evidence", identifier))

    @api.get("/api/raw-tables/{identifier}", response_model=Detail)
    def raw_table(identifier: str, database: Database) -> dict:
        return repository.detail(database, "raw_table", find(database, "raw_table", identifier))

    @api.get("/api/knowledge-cards", response_model=Page)
    def cards(database: Database, limit: Limit = 20, offset: Offset = 0) -> dict:
        return repository.page(database, "knowledge_card", limit, offset)

    @api.get("/api/graph-presets", response_model=Page)
    def presets(database: Database, limit: Limit = 20, offset: Offset = 0) -> dict:
        return repository.page(database, "graph_preset", limit, offset)

    @api.get("/api/files", response_model=Page)
    def files(
        database: Database, investigation_id: str | None = None, limit: Limit = 20, offset: Offset = 0
    ) -> dict:
        check_scope(database, investigation_id)
        return repository.page(database, "file", limit, offset, investigation_id)

    @api.get("/api/search")
    def search(
        database: Database, q: Annotated[str, Query(min_length=1, max_length=240)], limit: Limit = 10
    ) -> dict:
        return {"query": q, "method": "lexical_keywords", "items": repository.search(database, q, limit)}

    @api.get("/api/compare")
    def compare(database: Database, ids: Annotated[str, Query(min_length=1, max_length=500)]) -> dict:
        identifiers = [part.strip() for part in ids.split(",")]
        if not 2 <= len(identifiers) <= 4 or len(set(identifiers)) != len(identifiers):
            raise HTTPException(422, detail="Select two to four distinct measured series.")
        items = [find(database, "series", i) for i in identifiers]
        signatures = {(s["x"]["name"], s["x"]["unit"], s["y"]["name"], s["y"]["unit"]) for s in items}
        if len(signatures) != 1:
            raise HTTPException(422, detail="Series measure different quantities or use incompatible axes.")
        return {
            "series": [repository.detail(database, "series", s) for s in items],
            "transformations": [],
            "limitations": [
                "Original source time coordinates are retained; time origins are not independently aligned.",
                "Measurement similarity does not establish matched experimental conditions or causality.",
                "No smoothing, interpolation, extinction inference or numerical safety recommendation is performed.",
            ],
        }

    @api.post("/api/ask")
    def ask(body: AskRequest) -> JSONResponse:
        status, content, headers = ask_service.answer(body.question)
        return JSONResponse(status_code=status, content=content, headers=headers)

    return api


app = create_app()
