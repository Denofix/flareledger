"""Real corpus/quota state; provider transport is stubbed and consumes no API quota."""

import io
import json
import sqlite3
import subprocess
import sys
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from app.ask import retrieve
from app.ask_store import AskStateUnavailable, AskStore, Limited, migrate
from app.config import Settings
from app.llm import Explanation, GeminiProvider, LLMSettings, ProviderUnavailable
from app.main import create_app
from app.storage import Repository


def configured(**values):
    return replace(LLMSettings(enabled=True, key="TEST-ONLY-KEY", daily=10, minute=3), **values)


def test_default_model_is_flash_and_generation_still_requires_opt_in(monkeypatch):
    for name in ("LLM_MODEL", "LLM_ENABLED", "GEMINI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    assert LLMSettings().model == "gemini-3.6-flash"
    config = LLMSettings.from_env()
    assert config.model == "gemini-3.6-flash"
    assert config.enabled is False and config.configured is False


def supported(context):
    item = context[0]
    return {
        "status": "generated",
        "answer": f"The corpus documents this investigation. [{item['id']}]",
        "citations": [
            {
                "context_id": item["id"],
                "source_id": item["source_ids"][0],
                "quote": item["support_text"][:100],
            }
        ],
        "limitations": ["Source-linked interpretation is not independent scientific review."],
    }


class Stub:
    def __init__(self, mutate=None, failure=None):
        self.calls = 0
        self.mutate = mutate
        self.failure = failure
        self.context = []

    def generate(self, question, context):
        self.calls += 1
        self.context = context
        if self.failure:
            raise ProviderUnavailable(self.failure)
        value = supported(context)
        if self.mutate:
            self.mutate(value)
        return Explanation.model_validate(value)


def count(settings):
    with closing(sqlite3.connect(settings.database_path)) as db:
        return db.execute("SELECT COUNT(*) FROM fl_ask_calls").fetchone()[0]


def test_opt_in_needs_key_positive_limits_and_explicit_migration(settings):
    provider = Stub()
    with TestClient(create_app(settings, configured(), provider)) as client:
        assert client.get("/api/meta").json()["live_generation_available"] is False
        assert (
            client.post("/api/ask", json={"question": "What evidence is available about PMMA?"}).status_code
            == 503
        )
    with closing(sqlite3.connect(settings.database_path)) as db:
        assert not db.execute("SELECT name FROM sqlite_master WHERE name LIKE 'fl_ask_%'").fetchall()
    migrate(settings.database_path)
    for config in (
        configured(enabled=False),
        configured(key=""),
        configured(daily=0),
        configured(minute=4),
        configured(model="unverified-paid-model"),
    ):
        with TestClient(create_app(settings, config, provider)) as client:
            assert client.post("/api/ask", json={"question": "PMMA"}).status_code == 503
            assert client.get("/api/health/ready").status_code == 200
    assert provider.calls == 0


@pytest.mark.parametrize("model", ["gemini-4-hydrogen", "gemini-3.6-flash"])
def test_natural_question_uses_real_sources_and_preserves_original_corpus(settings, model):
    migrate(settings.database_path)
    provider = Stub()
    original = Repository(settings).readiness()
    with TestClient(create_app(settings, configured(model=model), provider)) as client:
        response = client.post(
            "/api/ask", json={"question": "What evidence is available about PMMA in the BASS experiments?"}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "generated" and result["model"] == model
        assert result["scientific_review"] is False
        assert result["citations"][0]["source_id"] in result["retrieved_evidence"][0]["source_ids"]
        assert response.headers["cache-control"] == "no-store"
        assert client.get("/api/health/ready").status_code == 200
    assert Repository(settings).readiness() == original
    assert provider.calls == 1 and count(settings) == 1
    assert "TEST-ONLY-KEY" not in json.dumps(provider.context)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda v: v["citations"][0].update(source_id="INVENTED-DOI"),
        lambda v: v["citations"][0].update(context_id="INVENTED-EVIDENCE"),
        lambda v: v["citations"][0].update(quote="An invented NASA quotation that is absent."),
        lambda v: v.update(answer=v["answer"] + " Safe oxygen is 987654.321 percent."),
        lambda v: v.update(answer=v["answer"] + " [UNKNOWN-CITATION]"),
        lambda v: v.update(answer=v["answer"] + " https://malicious.invalid/source"),
        lambda v: v.update(limitations=[]),
        lambda v: v.update(citations=[]),
        lambda v: v.update(answer=""),
        lambda v: v.update(status="insufficient_evidence"),
    ],
)
def test_invalid_or_unsubstantiated_output_is_never_presented_as_an_answer(settings, mutate):
    migrate(settings.database_path)
    with TestClient(create_app(settings, configured(), Stub(mutate))) as client:
        result = client.post("/api/ask", json={"question": "PMMA"})
        assert result.status_code == 503
        assert result.json()["answer"] is None
        assert result.json()["error"]["reason"] == "invalid_model_output"
        assert result.json()["retrieved_evidence"]
    assert count(settings) == 1


def test_no_context_refuses_without_spending_quota(settings):
    migrate(settings.database_path)
    provider = Stub()
    with TestClient(create_app(settings, configured(), provider)) as client:
        result = client.post("/api/ask", json={"question": "unobtainium_xylophone"})
        assert result.status_code == 200 and result.json()["status"] == "insufficient_evidence"
        assert result.json()["answer"] is None
    assert provider.calls == 0 and count(settings) == 0


def test_unavailable_corpus_never_becomes_a_successful_no_evidence_result(settings, tmp_path):
    migrate(settings.database_path)
    provider = Stub()
    with TestClient(
        create_app(Settings(settings.database_path, tmp_path / "missing-corpus"), configured(), provider)
    ) as client:
        result = client.post("/api/ask", json={"question": "PMMA"})
        assert result.status_code == 503 and result.json()["error"]["reason"] == "corpus_unavailable"
        assert result.json()["answer"] is None
    assert provider.calls == 0 and count(settings) == 0


def test_supported_provider_refusal_is_explicit(settings):
    migrate(settings.database_path)

    def refuse(value):
        value.update(status="insufficient_evidence", answer="", citations=[])

    with TestClient(create_app(settings, configured(), Stub(refuse))) as client:
        response = client.post("/api/ask", json={"question": "PMMA exact safe oxygen threshold"})
        assert response.status_code == 200
        assert response.json()["status"] == "insufficient_evidence" and response.json()["answer"] is None


@pytest.mark.parametrize("reason", ["provider_quota_exhausted", "provider_unavailable", "SECRET-DO-NOT-LOG"])
def test_provider_failure_is_bounded_private_and_does_not_disable_catalogue(settings, reason):
    migrate(settings.database_path)
    with TestClient(create_app(settings, configured(), Stub(failure=reason))) as client:
        result = client.post("/api/ask", json={"question": "PMMA"})
        assert result.status_code == 503 and result.json()["answer"] is None
        assert "SECRET-DO-NOT-LOG" not in result.text
        assert client.get("/api/investigations").json()["total"] == 10
    assert count(settings) == 1


def test_usage_survives_restart_migration_and_sqlite_backup_restore(settings, tmp_path):
    migrate(settings.database_path)
    provider = Stub()
    config = configured(daily=1)
    with TestClient(create_app(settings, config, provider)) as client:
        assert client.post("/api/ask", json={"question": "PMMA"}).status_code == 200
    migrate(settings.database_path)
    restored = tmp_path / "restored.sqlite3"
    with closing(sqlite3.connect(settings.database_path)) as src, closing(sqlite3.connect(restored)) as dst:
        src.backup(dst)
    with TestClient(create_app(Settings(restored, settings.data_dir), config, provider)) as client:
        result = client.post(
            "/api/ask", json={"question": "PMMA"}, headers={"X-Forwarded-For": "random-client"}
        )
        assert result.status_code == 429 and int(result.headers["retry-after"]) > 0
        assert result.json()["retrieved_evidence"]
        assert client.get("/api/health/ready").status_code == 200
    assert provider.calls == 1


def test_rolling_limits_and_clock_rollback_fail_closed(settings):
    migrate(settings.database_path)
    store = AskStore(settings.database_path)
    call = store.reserve(100000, 2, 1, 30)
    store.finish(call)
    with pytest.raises(Limited):
        store.reserve(100001, 2, 1, 30)
    call = store.reserve(100061, 2, 1, 30)
    store.finish(call)
    with pytest.raises(Limited):
        store.reserve(100200, 2, 1, 30)
    with pytest.raises(AskStateUnavailable):
        store.reserve(99999, 2, 1, 30)


def test_corrupt_ask_state_never_sends_an_unaccounted_call(settings):
    migrate(settings.database_path)
    provider = Stub()
    with closing(sqlite3.connect(settings.database_path)) as db, db:
        db.execute("DROP TABLE fl_ask_calls")
    with TestClient(create_app(settings, configured(), provider)) as client:
        assert client.get("/api/meta").json()["live_generation_available"] is False
        assert client.post("/api/ask", json={"question": "PMMA"}).status_code == 503
        assert client.get("/api/health/ready").status_code == 200
    assert provider.calls == 0
    with pytest.raises(AskStateUnavailable):
        migrate(settings.database_path)


@pytest.mark.parametrize("model", ["gemini-4-hydrogen", "gemini-3.6-flash"])
def test_environment_configuration_rejects_custom_hosts_and_unsafe_limits(monkeypatch, model):
    values = {
        "LLM_ENABLED": "true",
        "LLM_PROVIDER": "gemini",
        "LLM_MODEL": model,
        "GEMINI_API_KEY": "TEST-ONLY-KEY",
        "ASK_MAX_REQUESTS_PER_DAY": "10",
        "ASK_MAX_REQUESTS_PER_MINUTE": "3",
        "LLM_TIMEOUT_SECONDS": "30",
        "LLM_MAX_OUTPUT_TOKENS": "2048",
        "LLM_MAX_CONCURRENT_REQUESTS": "1",
        "LLM_BASE_URL": "",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    assert LLMSettings.from_env().configured is True
    for key, value in (
        ("LLM_BASE_URL", "http://127.0.0.1"),
        ("LLM_MAX_CONCURRENT_REQUESTS", "2"),
        ("ASK_MAX_REQUESTS_PER_DAY", "100"),
        ("LLM_TIMEOUT_SECONDS", "invalid"),
        ("LLM_PROVIDER", "openai"),
        ("LLM_MODEL", "gemini-flash-latest"),
        ("LLM_MODEL", "gemini-4-carbon"),
    ):
        monkeypatch.setenv(key, value)
        assert LLMSettings.from_env().configured is False
        monkeypatch.setenv(key, values[key])


def test_cross_process_reservations_allow_one_provider_call(settings):
    migrate(settings.database_path)
    code = """from pathlib import Path
import sys
from app.ask_store import AskStore,Limited
try:
    AskStore(Path(sys.argv[1])).reserve(100000,10,3,30)
    print('reserved')
except Limited:
    print('limited')
"""
    with ThreadPoolExecutor(max_workers=4) as pool:
        outputs = list(
            pool.map(
                lambda _: subprocess.run(
                    [sys.executable, "-c", code, str(settings.database_path)],
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout.strip(),
                range(4),
            )
        )
    assert outputs.count("reserved") == 1 and outputs.count("limited") == 3
    assert count(settings) == 1


def test_large_streamed_bodies_and_user_provider_configuration_are_rejected(settings):
    migrate(settings.database_path)
    provider = Stub()
    with TestClient(create_app(settings, configured(), provider)) as client:
        assert client.post("/api/ask", content=iter([b"x" * 5000, b"x" * 5000])).status_code == 413
        assert (
            client.post("/api/ask", json={"question": "PMMA", "provider_url": "http://127.0.0.1"}).status_code
            == 422
        )
        assert client.post("/api/ask", json={"question": "x" * 1001}).status_code == 422
    assert provider.calls == 0 and count(settings) == 0


@pytest.mark.parametrize("model", ["gemini-4-hydrogen", "gemini-3.6-flash"])
def test_transport_uses_only_configured_official_endpoint_and_validates_complete_response(settings, model):
    with Repository(settings).connection() as db:
        _, context = retrieve(Repository(settings), db, "PMMA")
    explanation = supported(context)
    body = {
        "status": "completed",
        "steps": [{"type": "model_output", "content": [{"type": "text", "text": json.dumps(explanation)}]}],
    }
    opener = mock.Mock()
    opener.open.return_value = io.BytesIO(json.dumps(body).encode())
    with mock.patch("app.llm.urllib.request.build_opener", return_value=opener):
        result = GeminiProvider(configured(model=model)).generate("PMMA", context)
    request = opener.open.call_args.args[0]
    payload = json.loads(request.data)
    assert payload["model"] == model
    assert result.status == "generated" and payload["store"] is False
    assert payload["response_format"]["mime_type"] == "application/json"
    assert payload["generation_config"]["thinking_level"] == "low"
    assert "TEST-ONLY-KEY" not in request.data.decode()
    assert len(request.data) <= 32768 and opener.open.call_count == 1
    assert "TEST-ONLY-KEY" not in repr(configured())
    for invalid in ({"status": "in_progress"}, {"status": "completed", "steps": []}):
        opener.open.return_value = io.BytesIO(json.dumps(invalid).encode())
        with (
            mock.patch("app.llm.urllib.request.build_opener", return_value=opener),
            pytest.raises(ProviderUnavailable),
        ):
            GeminiProvider(configured(model=model)).generate("PMMA", context)


@pytest.mark.parametrize("model", ["gemini-4-hydrogen", "gemini-3.6-flash"])
def test_transport_timeout_does_not_leak_credentials_or_retry(model):
    opener = mock.Mock()
    opener.open.side_effect = TimeoutError("TEST-ONLY-KEY")
    with (
        mock.patch("app.llm.urllib.request.build_opener", return_value=opener),
        pytest.raises(ProviderUnavailable) as caught,
    ):
        GeminiProvider(configured(model=model)).generate("PMMA", [])
    assert "TEST-ONLY-KEY" not in str(caught.value) and opener.open.call_count == 1


@pytest.mark.parametrize("model", ["gemini-4-hydrogen", "gemini-3.6-flash"])
@pytest.mark.parametrize("status", [301, 403, 429, 500, 503])
def test_provider_http_errors_have_no_automatic_retry_or_exposed_error_body(status, model):
    opener = mock.Mock()
    opener.open.side_effect = urllib.error.HTTPError(
        "https://example.invalid", status, "TEST-ONLY-KEY", {}, None
    )
    with (
        mock.patch("app.llm.urllib.request.build_opener", return_value=opener),
        pytest.raises(ProviderUnavailable) as caught,
    ):
        GeminiProvider(configured(model=model)).generate("PMMA", [])
    assert opener.open.call_count == 1
    assert str(caught.value) == ("provider_quota_exhausted" if status == 429 else "provider_unavailable")


def test_model_switch_keeps_existing_quota_and_does_not_fallback(settings):
    migrate(settings.database_path)
    failed = Stub(failure="provider_unavailable")
    with TestClient(create_app(settings, configured(daily=1), failed)) as client:
        assert client.post("/api/ask", json={"question": "PMMA"}).status_code == 503
    flash = Stub()
    with TestClient(create_app(settings, configured(daily=1, model="gemini-3.6-flash"), flash)) as client:
        result = client.post("/api/ask", json={"question": "PMMA"})
        assert result.status_code == 429 and result.json()["retrieved_evidence"]
    assert failed.calls == 1 and flash.calls == 0 and count(settings) == 1
