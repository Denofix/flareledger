"""Safe rejection codes; real corpus and quota tables, no live provider calls."""

import logging
import sqlite3
from contextlib import closing
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.ask import ExplanationRejected, validate_explanation
from app.ask_store import migrate
from app.llm import Explanation, LLMSettings, ProviderUnavailable
from app.main import create_app

SECRET = "PRIVATE-INPUT-AND-KEY-MUST-NOT-APPEAR"


def output(context: list[dict[str, Any]]) -> dict[str, Any]:
    item = context[0]
    return {
        "status": "generated",
        "answer": f"This is source-linked context. [{item['id']}]",
        "citations": [
            {"context_id": item["id"], "source_id": item["source_ids"][0], "quote": item["support_text"][:80]}
        ],
        "limitations": ["This interpretation is not an independent scientific review."],
    }


def corrupt(value: dict[str, Any], code: str) -> Explanation:
    if code == "refusal_contains_content":
        value["status"] = "insufficient_evidence"
    elif code == "missing_answer":
        value["answer"] = " "
    elif code == "missing_citations":
        value["citations"] = []
    elif code == "missing_limitations":
        value["limitations"] = []
    elif code == "unknown_context":
        value["citations"][0]["context_id"] = SECRET
    elif code == "source_not_in_context":
        value["citations"][0]["source_id"] = SECRET
    elif code == "quote_not_exact":
        value["citations"][0]["quote"] = SECRET
    elif code == "citation_marker_missing":
        value["answer"] = SECRET
    elif code == "unknown_citation_marker":
        value["answer"] += f" [{SECRET}]"
    elif code == "unseen_numeric_token":
        value["answer"] += " Claimed threshold: 987654321.12345."
    elif code == "model_supplied_url":
        value["answer"] += " https://private.invalid/" + SECRET
    elif code == "oversized_limitation":
        # Simulate an incorrectly constructed provider object beyond schema bounds.
        return Explanation.model_validate(value).model_copy(update={"limitations": [SECRET * 30]})
    elif code == "invalid_output_schema":
        value["unexpected"] = SECRET
    elif code == "unexpected_validation_error":
        raise ValueError(SECRET)
    return Explanation.model_validate(value)


class Provider:
    def __init__(self, code: str | None = None):
        self.code = code
        self.calls = 0

    def generate(self, question: str, context: list[dict[str, Any]]) -> Explanation:
        self.calls += 1
        value = output(context)
        if self.code:
            return corrupt(value, self.code)
        return Explanation.model_validate(value)


@pytest.mark.parametrize(
    "code",
    [
        "refusal_contains_content",
        "missing_answer",
        "missing_citations",
        "missing_limitations",
        "unknown_context",
        "source_not_in_context",
        "quote_not_exact",
        "citation_marker_missing",
        "unknown_citation_marker",
        "unseen_numeric_token",
        "model_supplied_url",
        "oversized_limitation",
        "invalid_output_schema",
        "unexpected_validation_error",
    ],
)
def test_rejection_logs_only_fixed_code_and_preserves_failure_contract(settings, caplog, code):
    migrate(settings.database_path)
    provider = Provider(code)
    config = LLMSettings(enabled=True, key=SECRET, daily=10, minute=3)
    with caplog.at_level(logging.WARNING, logger="app.ask"):
        with TestClient(create_app(settings, config, provider)) as client:
            response = client.post("/api/ask", json={"question": "PMMA " + SECRET})
            assert client.get("/api/health/ready").status_code == 200
    assert response.status_code == 503
    body = response.json()
    assert body["error"] == {
        "code": "llm_unavailable",
        "reason": "invalid_model_output",
        "message": "Generation is unavailable. Retrieved evidence remains available; no answer was generated.",
    }
    assert body["answer"] is None and body["citations"] == [] and body["retrieved_evidence"]
    assert response.headers["cache-control"] == "no-store"
    assert provider.calls == 1
    with closing(sqlite3.connect(settings.database_path)) as db:
        assert db.execute("SELECT COUNT(*), SUM(finished) FROM fl_ask_calls").fetchone() == (1, 1)
    records = [record for record in caplog.records if record.name == "app.ask"]
    assert len(records) == 1
    assert records[0].getMessage() == "ASK_VALIDATION stage=explanation code=" + code
    assert records[0].exc_info is None and records[0].stack_info is None
    assert SECRET not in records[0].getMessage() and SECRET not in response.text


def test_accepted_output_and_no_context_do_not_emit_rejection_diagnostics(settings, caplog):
    migrate(settings.database_path)
    provider = Provider()
    config = LLMSettings(enabled=True, key=SECRET, daily=10, minute=3)
    with caplog.at_level(logging.WARNING, logger="app.ask"):
        with TestClient(create_app(settings, config, provider)) as client:
            assert client.post("/api/ask", json={"question": "PMMA"}).json()["status"] == "generated"
            assert (
                client.post("/api/ask", json={"question": "capital Iceland"}).json()["status"]
                == "insufficient_evidence"
            )
    assert not [record for record in caplog.records if record.name == "app.ask"]
    assert provider.calls == 1


def test_provider_failure_is_not_misclassified_as_explanation_rejection(settings, caplog):
    migrate(settings.database_path)

    class Unavailable:
        def generate(self, question, context):
            raise ProviderUnavailable(SECRET)

    config = LLMSettings(enabled=True, key=SECRET, daily=10, minute=3)
    with caplog.at_level(logging.WARNING, logger="app.ask"):
        with TestClient(create_app(settings, config, Unavailable())) as client:
            response = client.post("/api/ask", json={"question": "PMMA"})
    assert response.status_code == 503
    assert response.json()["error"]["reason"] == "provider_unavailable"
    assert not [record for record in caplog.records if record.name == "app.ask"]
    assert SECRET not in response.text


def test_rejection_constructor_does_not_accept_arbitrary_log_text():
    with pytest.raises(ValueError):
        ExplanationRejected(SECRET)  # type: ignore[arg-type]


def test_correct_literal_refusal_still_passes_validation():
    value = Explanation(status="insufficient_evidence", answer="", citations=[], limitations=[])
    assert validate_explanation(value, []) is None
