"""Claim binding and bounded transport; synthetic output, never a live quality score."""

import io
import json
import logging
import sqlite3
from contextlib import closing
from unittest import mock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.ask import retrieve
from app.ask_store import migrate
from app.config import ROOT
from app.explanations import (
    Explanation,
    ExplanationDraft,
    ExplanationRejected,
    RejectionCode,
    render_draft,
    validate_explanation,
)
from app.llm import GeminiProvider, LLMSettings
from app.main import create_app
from app.storage import Repository

CONTEXT = [
    {
        "id": "CTX-A",
        "source_ids": ["SRC-A"],
        "support_text": "The table has 469 operating rows. No year is provided.",
    },
    {"id": "CTX-B", "source_ids": ["SRC-B"], "support_text": "Another table has 20 records."},
]
LIMITS = ["Interpretation is bounded to the supplied evidence."]


def claim(text="The table has 469 operating rows.", index=0, **citation_changes):
    item = CONTEXT[index]
    citation = {"context_id": item["id"], "source_id": item["source_ids"][0], "quote": item["support_text"]}
    citation.update(citation_changes)
    return {"text": text, "citation": citation}


def draft(claims, status="generated", limitations=None):
    return ExplanationDraft.model_validate(
        {
            "status": status,
            "claims": claims,
            "limitations": LIMITS if limitations is None else limitations,
        }
    )


def wire(value):
    return io.BytesIO(
        json.dumps(
            {
                "status": "completed",
                "steps": [{"type": "model_output", "content": [{"type": "text", "text": json.dumps(value)}]}],
            }
        ).encode()
    )


def test_claim_structure_renders_each_marker_and_keeps_public_contract():
    result = render_draft(draft([claim(), claim("Another table has 20 records.", 1)]), CONTEXT)
    assert (
        result.answer == "The table has 469 operating rows. [CTX-A]\n\nAnother table has 20 records. [CTX-B]"
    )
    assert [citation.context_id for citation in result.citations] == ["CTX-A", "CTX-B"]
    assert set(result.model_dump()) == {"status", "answer", "citations", "limitations"}
    assert validate_explanation(result, CONTEXT) is None


def test_observed_missing_marker_failure_class_is_prevented_by_claim_binding():
    # Synthetic regression for the reported code; the hidden model response is unavailable.
    old = Explanation.model_validate(
        {
            "status": "generated",
            "answer": "The table has 469 operating rows. [CTX-A]",
            "citations": [claim()["citation"], claim(index=1)["citation"]],
            "limitations": LIMITS,
        }
    )
    with pytest.raises(ExplanationRejected) as error:
        validate_explanation(old, CONTEXT)
    assert error.value.code == RejectionCode.CITATION_MARKER_MISSING
    result = render_draft(draft([claim(), claim("Another table has 20 records.", 1)]), CONTEXT)
    assert all(f"[{citation.context_id}]" in result.answer for citation in result.citations)


def test_repeated_citation_has_one_source_entry_and_a_marker_on_each_claim():
    result = render_draft(draft([claim(), claim("No year is provided.")]), CONTEXT)
    assert len(result.citations) == 1 and result.answer.count("[CTX-A]") == 2


@pytest.mark.parametrize(
    ("value", "code"),
    [
        (claim(context_id="UNKNOWN"), "unknown_context"),
        (claim(source_id="UNKNOWN"), "source_not_in_context"),
        (claim(quote="Invented excerpt that is not present."), "quote_not_exact"),
        (claim("A claim with https://untrusted.invalid/source"), "model_supplied_url"),
        (claim("A claim with [CTX-A] already inserted."), "claim_contains_markers"),
        (claim("A claim with an unmatched [ bracket."), "claim_contains_markers"),
        (claim("A claim with an unmatched ] bracket."), "claim_contains_markers"),
        (claim(" "), "missing_answer"),
    ],
)
def test_bound_claim_still_rejects_invalid_evidence_or_model_markup(value, code):
    with pytest.raises(ExplanationRejected) as error:
        render_draft(draft([value]), CONTEXT)
    assert error.value.code.value == code


def test_a_number_in_another_claims_context_does_not_support_this_claim():
    value = draft([claim("This table has 20 operating rows."), claim("Another table has 20 records.", 1)])
    with pytest.raises(ExplanationRejected) as error:
        render_draft(value, CONTEXT)
    assert error.value.code == RejectionCode.UNSEEN_NUMERIC_TOKEN


@pytest.mark.parametrize(
    ("value", "code"),
    [
        (draft([]), "missing_claims"),
        (draft([claim()], status="insufficient_evidence"), "refusal_contains_content"),
        (draft([claim()], limitations=[]), "missing_limitations"),
    ],
)
def test_refusal_and_generated_states_keep_their_required_boundaries(value, code):
    with pytest.raises(ExplanationRejected) as error:
        render_draft(value, CONTEXT)
    assert error.value.code.value == code


def test_supported_refusal_contains_no_rendered_answer_or_citations():
    value = render_draft(draft([], status="insufficient_evidence"), CONTEXT)
    assert value.answer == "" and value.citations == [] and value.status == "insufficient_evidence"


@pytest.mark.parametrize(
    "claims",
    [
        [{"text": "Unsupported claim without evidence."}],
        [claim("x" * 301)],
        [claim()] * 6,
    ],
)
def test_required_citation_and_output_bounds_are_checked_locally(claims):
    with pytest.raises(ValidationError):
        draft(claims)


def test_long_identifiers_and_five_claims_fit_public_answer_bound():
    context = [{"id": "C" * 160, "source_ids": ["S" * 160], "support_text": "e" * 300}]
    value = {
        "text": "e" * 300,
        "citation": {"context_id": "C" * 160, "source_id": "S" * 160, "quote": "e" * 300},
    }
    result = render_draft(draft([value] * 5), context)
    assert len(result.answer) <= 2500


CASES = json.loads((ROOT / "docs/ai-evaluation-cases.json").read_text())["cases"]


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_all_frozen_questions_keep_unmodified_input_and_bounded_request_bytes(settings, case):
    repository = Repository(settings)
    with repository.connection() as db:
        _, context = retrieve(repository, db, case["question"])
    opener = mock.Mock()
    opener.open.return_value = wire({"status": "insufficient_evidence", "claims": [], "limitations": LIMITS})
    with mock.patch("app.llm.urllib.request.build_opener", return_value=opener):
        GeminiProvider(LLMSettings(key="TEST-ONLY-KEY")).generate(case["question"], context)
    request = opener.open.call_args.args[0]
    payload = json.loads(request.data)
    assert json.loads(payload["input"]) == {"question": case["question"], "context": context}
    assert len(request.data) <= 32768 and opener.open.call_count == 1
    assert "TEST-ONLY-KEY" not in request.data.decode()


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("valid", "generated"),
        ("missing_claims", "missing_claims"),
        ("model_marker", "claim_contains_markers"),
        ("old_output_shape", "invalid_output_schema"),
        ("bad_quote", "quote_not_exact"),
    ],
)
def test_mocked_transport_preserves_one_reservation_and_safe_diagnostics(settings, caplog, mode, expected):
    migrate(settings.database_path)
    repository = Repository(settings)
    with repository.connection() as db:
        _, context = retrieve(repository, db, "SPICE rows GMT")
    item = context[0]
    text = "The supplied source describes operating-condition rows."
    value = {
        "status": "generated",
        "claims": [
            {
                "text": text,
                "citation": {
                    "context_id": item["id"],
                    "source_id": item["source_ids"][0],
                    "quote": item["support_text"][:80],
                },
            }
        ],
        "limitations": LIMITS,
    }
    if mode == "missing_claims":
        value["claims"] = []
    elif mode == "model_marker":
        value["claims"][0]["text"] += " [PRIVATE-MARKER]"
    elif mode == "bad_quote":
        value["claims"][0]["citation"]["quote"] = "PRIVATE-EXCERPT-NOT-IN-CONTEXT"
    elif mode == "old_output_shape":
        value = {
            "status": "generated",
            "answer": "PRIVATE-ORPHAN-ANSWER",
            "citations": [],
            "limitations": LIMITS,
        }
    opener = mock.Mock()
    opener.open.return_value = wire(value)
    config = LLMSettings(enabled=True, key="PRIVATE-KEY", daily=10, minute=3)
    with (
        mock.patch("app.llm.urllib.request.build_opener", return_value=opener),
        caplog.at_level(logging.WARNING, logger="app.ask"),
    ):
        with TestClient(create_app(settings, config)) as client:
            response = client.post("/api/ask", json={"question": "SPICE rows GMT"})
    assert opener.open.call_count == 1
    with closing(sqlite3.connect(settings.database_path)) as db:
        assert db.execute("SELECT COUNT(*), SUM(finished) FROM fl_ask_calls").fetchone() == (1, 1)
    records = [record for record in caplog.records if record.name == "app.ask"]
    if mode == "valid":
        assert response.status_code == 200 and response.json()["status"] == "generated"
        assert response.json()["answer"] == text + f" [{item['id']}]"
        assert not records
    else:
        assert response.status_code == 503 and response.json()["answer"] is None
        assert response.json()["error"]["reason"] == "invalid_model_output"
        assert [record.getMessage() for record in records] == [
            "ASK_VALIDATION stage=explanation code=" + expected
        ]
        assert all(record.exc_info is None for record in records)
        assert "PRIVATE-" not in response.text + "".join(record.getMessage() for record in records)
