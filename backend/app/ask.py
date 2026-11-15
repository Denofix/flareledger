"""Source-linked Ask orchestration; network generation is opt-in and fail-closed."""

import json
import logging
import re
import sqlite3
import time
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from app.ask_store import AskStateUnavailable, AskStore, Limited
from app.explanations import ExplanationRejected as ExplanationRejected
from app.explanations import RejectionCode as RejectionCode
from app.explanations import validate_explanation as validate_explanation
from app.llm import GeminiProvider, LLMSettings, Provider, ProviderUnavailable
from app.storage import CorpusUnavailable, Repository

STOP = set(
    "a an and are as at be can compare could data describe do does explain evidence experiment experiments find for from how i in is it know me of on or research show tell than that the their these this to two use using what which with would about available between".split()
)
NOTICE = "FlareLedger-generated interpretation; citation and excerpt checks do not establish scientific correctness. Verify the original source and experimental conditions."
LOGGER = logging.getLogger(__name__)


def log_rejection(code: RejectionCode) -> None:
    # Only a closed enum is logged: never exception text, model output or input.
    LOGGER.warning("ASK_VALIDATION stage=explanation code=%s", RejectionCode(code).value)


def retrieve(repository: Repository, db: sqlite3.Connection, question: str) -> tuple[list[dict], list[dict]]:
    tokens = list(
        dict.fromkeys(t for t in re.findall(r"[\w-]+", question.casefold()) if len(t) >= 3 and t not in STOP)
    )[:8]
    if not tokens:
        return [], []
    terms = ["%" + t.replace("\\", "\\\\").replace("_", "\\_") + "%" for t in tokens]
    clauses = ["search_text LIKE ? ESCAPE '\\'" for _ in terms]
    score = "+".join(f"CASE WHEN {c} THEN 1 ELSE 0 END" for c in clauses)
    rows = db.execute(
        f"SELECT kind, payload_json FROM fl_entities WHERE kind IN ('investigation','record','knowledge_card','series','source') AND ({' OR '.join(clauses)}) "
        f"ORDER BY ({score}) DESC, CASE kind WHEN 'investigation' THEN 0 WHEN 'series' THEN 1 WHEN 'knowledge_card' THEN 2 WHEN 'record' THEN 3 ELSE 4 END, ordinal LIMIT 20",
        [*terms, *terms],
    )
    hits: list[dict] = []
    context: list[dict] = []
    used = 0
    for kind, raw in rows:
        item = json.loads(raw)
        detail = repository.detail(db, kind, item)
        sources = [s for s in detail["sources"] if s]
        if not sources:
            continue
        # Keep complete fields; omit oversized items rather than truncating numbers or quotes.
        content = {
            k: v
            for k, v in item.items()
            if k
            not in {
                "points",
                "source_rows",
                "file_catalog_retrieval",
                "file_catalog",
                "original_bytes_base64",
            }
        }
        content["quality_issues"] = detail["quality_issues"]
        support = json.dumps(content, ensure_ascii=False, sort_keys=True)
        if len(support.encode()) > 5000:
            continue
        entry = {
            "id": item["id"],
            "kind": kind,
            "source_ids": [s["id"] for s in sources],
            "support_text": support,
            "evidence": detail["evidence"],
            "source_titles": [
                {"id": s["id"], "title": s.get("title", ""), "doi": s.get("doi")} for s in sources
            ],
        }
        size = len(json.dumps(entry).encode())
        if used + size > 16000:
            continue
        used += size
        context.append(entry)
        hits.append(
            {
                "kind": kind,
                "id": item["id"],
                "investigation_id": item.get("investigation_id"),
                "title": item.get("title_en")
                or item.get("title")
                or item.get("original_trial_label")
                or item.get("material")
                or item["id"],
                "excerpt": (
                    item.get("text_en")
                    or item.get("summary_en")
                    or item.get("quality_note_en")
                    or item.get("material")
                    or ""
                )[:500],
                "source_ids": entry["source_ids"],
                "evidence_ids": item.get("evidence_ids", []),
                "sources": sources,
            }
        )
        if len(hits) == 5:
            break
    return hits, context


class AskService:
    def __init__(
        self,
        repository: Repository,
        config: LLMSettings,
        provider: Provider | None = None,
        clock: Callable[[], float] = time.time,
    ):
        self.repository = repository
        self.config = config
        self.provider = provider or GeminiProvider(config)
        self.store = AskStore(repository.settings.database_path)
        self.clock = clock

    @property
    def available(self) -> bool:
        return self.config.configured and self.store.ready()

    def answer(self, question: str) -> tuple[int, dict[str, Any], dict[str, str]]:
        try:
            with self.repository.connection() as db:
                metadata = self.repository.metadata(db)
                hits, context = retrieve(self.repository, db, question)
        except CorpusUnavailable:
            hits, context, metadata = [], [], {}
        base: dict[str, Any] = {
            "answer": None,
            "retrieved_evidence": hits,
            "retrieval_method": "lexical_keywords",
            "live_generation_available": self.available,
            "corpus_version": metadata.get("corpus_version"),
            "citations": [],
            "limitations": [],
            "status": "unavailable",
        }

        def unavailable(reason: str) -> tuple[int, dict[str, Any], dict[str, str]]:
            return (
                503,
                {
                    **base,
                    "status": "unavailable",
                    "error": {
                        "code": "llm_unavailable",
                        "reason": reason,
                        "message": "Generation is unavailable. Retrieved evidence remains available; no answer was generated.",
                    },
                },
                {},
            )

        if not metadata:
            return unavailable("corpus_unavailable")
        if not self.available:
            return unavailable("not_configured_or_not_migrated")
        if not context:
            return (
                200,
                {
                    **base,
                    "status": "insufficient_evidence",
                    "limitations": ["No supporting corpus context was found. No model call was made."],
                },
                {},
            )
        try:
            identifier = self.store.reserve(
                self.clock(), self.config.daily, self.config.minute, self.config.timeout
            )
        except Limited as error:
            return (
                429,
                {
                    **base,
                    "status": "rate_limited",
                    "retry_after_seconds": error.retry_after,
                    "error": {
                        "code": "rate_limited",
                        "message": "The shared generation limit is reached. Use the source links or try later.",
                    },
                },
                {"Retry-After": str(error.retry_after)},
            )
        except AskStateUnavailable:
            return unavailable("quota_state_unavailable")
        try:
            explanation = self.provider.generate(question, context)
            validate_explanation(explanation, context)
            return (
                200,
                {
                    **base,
                    **explanation.model_dump(),
                    "answer": explanation.answer or None,
                    "provider": self.config.provider,
                    "model": self.config.model,
                    "generated_by": "FlareLedger",
                    "validation": "context_membership_exact_excerpt_and_numeric_token_checks",
                    "scientific_review": False,
                    "notice": NOTICE,
                },
                {},
            )
        except ProviderUnavailable as error:
            reason = str(error)
            return unavailable(
                reason
                if reason in {"provider_quota_exhausted", "context_too_large"}
                else "provider_unavailable"
            )
        except ExplanationRejected as error:
            log_rejection(error.code)
            return unavailable("invalid_model_output")
        except ValidationError:
            log_rejection(RejectionCode.INVALID_OUTPUT_SCHEMA)
            return unavailable("invalid_model_output")
        except (ValueError, KeyError, TypeError):
            log_rejection(RejectionCode.UNEXPECTED_VALIDATION_ERROR)
            return unavailable("invalid_model_output")
        finally:
            self.store.finish(identifier)
