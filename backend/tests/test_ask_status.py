"""Operator diagnostics read real quota state without writing or contacting Google."""

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from dataclasses import replace

from app.ask_status import inspect_status
from app.ask_store import AskStore, migrate
from app.config import Settings
from app.llm import LLMSettings


def configured(**values):
    return replace(LLMSettings(enabled=True, key="TEST-ONLY-KEY", daily=10, minute=3), **values)


def fingerprint(settings):
    return hashlib.sha256(settings.database_path.read_bytes()).hexdigest()


def test_preflight_does_not_create_missing_ask_state(settings):
    before = fingerprint(settings)
    result = inspect_status(settings, configured(), now=100000)
    assert result["corpus_ready"] is True and result["ask_state_ready"] is False
    assert result["reason"] == "ask_state_unavailable"
    assert result["ready_to_attempt_generation"] is False
    with closing(sqlite3.connect(settings.database_path)) as db:
        assert not db.execute("SELECT name FROM sqlite_master WHERE name LIKE 'fl_ask_%'").fetchall()
    assert fingerprint(settings) == before


def test_ready_and_disabled_diagnostics_preserve_database_and_usage(settings):
    migrate(settings.database_path)
    before = fingerprint(settings)
    result = inspect_status(settings, configured(), now=100000)
    assert result["ready_to_attempt_generation"] is True
    assert result["provider_probed"] is False
    assert result["model"] == "gemini-3.6-flash"
    assert result["quota"]["remaining_24h"] == 10
    assert result["quota"]["remaining_60s"] == 3
    disabled = inspect_status(settings, configured(enabled=False), now=100000)
    assert disabled["ask_state_ready"] is True
    assert disabled["reason"] == "disabled_or_invalid_configuration"
    assert disabled["ready_to_attempt_generation"] is False
    assert fingerprint(settings) == before


def test_active_lease_and_minute_limit_are_reported_without_consuming_a_call(settings):
    migrate(settings.database_path)
    store = AskStore(settings.database_path)
    identifier = store.reserve(100000, 10, 1, 30)
    before = fingerprint(settings)
    active = inspect_status(settings, configured(minute=1), now=100001)
    assert active["reason"] == "shared_limit_reached"
    assert active["quota"]["active_generation"] is True
    assert active["quota"]["retry_after_seconds"] == 90
    assert active["quota"]["last_24h"] == 1
    assert fingerprint(settings) == before
    store.finish(identifier)
    before = fingerprint(settings)
    limited = inspect_status(settings, configured(minute=1), now=100001)
    assert limited["quota"]["active_generation"] is False
    assert limited["quota"]["retry_after_seconds"] == 60
    assert limited["quota"]["remaining_60s"] == 0
    assert fingerprint(settings) == before


def test_rolling_daily_limit_remains_after_model_and_key_changes(settings):
    migrate(settings.database_path)
    store = AskStore(settings.database_path)
    for now in (100000, 100061):
        store.finish(store.reserve(now, 2, 1, 30))
    before = fingerprint(settings)
    for model in ("gemini-3.6-flash", "gemini-4-hydrogen"):
        result = inspect_status(settings, configured(model=model, key="OTHER-TEST-KEY", daily=2), now=100200)
        assert result["reason"] == "shared_limit_reached"
        assert result["quota"]["last_24h"] == 2
        assert result["quota"]["remaining_24h"] == 0
        assert result["quota"]["retry_after_seconds"] == 86201
    assert fingerprint(settings) == before


def test_clock_rollback_is_reported_without_resetting_last_seen(settings):
    migrate(settings.database_path)
    store = AskStore(settings.database_path)
    store.finish(store.reserve(100000, 10, 3, 30))
    before = fingerprint(settings)
    result = inspect_status(settings, configured(), now=99999)
    assert result["reason"] == "server_clock_unavailable"
    assert result["ready_to_attempt_generation"] is False
    assert fingerprint(settings) == before


def test_missing_corpus_does_not_create_a_database(settings, tmp_path):
    missing = tmp_path / "missing.sqlite3"
    result = inspect_status(Settings(missing, settings.data_dir), configured())
    assert result["reason"] == "corpus_unavailable"
    assert result["ready_to_attempt_generation"] is False
    assert not missing.exists()


def test_corrupt_ask_state_is_reported_without_repair_or_usage_reset(settings):
    migrate(settings.database_path)
    with closing(sqlite3.connect(settings.database_path)) as db, db:
        db.execute("DROP TABLE fl_ask_calls")
    before = fingerprint(settings)
    result = inspect_status(settings, configured())
    assert result["reason"] == "ask_state_unavailable"
    assert fingerprint(settings) == before


def test_invalid_clock_state_is_reported_without_exposing_its_value(settings):
    migrate(settings.database_path)
    with closing(sqlite3.connect(settings.database_path)) as db, db:
        db.execute("UPDATE fl_ask_schema SET last_seen='PRIVATE-CORRUPT-VALUE' WHERE id=1")
    before = fingerprint(settings)
    result = inspect_status(settings, configured())
    assert result["reason"] == "ask_state_unavailable"
    assert result["ready_to_attempt_generation"] is False
    assert "PRIVATE-CORRUPT-VALUE" not in json.dumps(result)
    assert fingerprint(settings) == before


def test_cli_reports_safe_flags_without_a_provider_call_or_credentials(settings):
    migrate(settings.database_path)
    before = fingerprint(settings)
    env = {
        **os.environ,
        "DATABASE_PATH": str(settings.database_path),
        "DATA_DIR": str(settings.data_dir),
        "LLM_ENABLED": "false",
        "LLM_PROVIDER": "gemini",
        "LLM_MODEL": "gemini-3.6-flash",
        "GEMINI_API_KEY": "PRIVATE-TEST-CREDENTIAL",
    }
    process = subprocess.run(
        [sys.executable, "-m", "app.ask_status"], env=env, check=True, capture_output=True, text=True
    )
    result = json.loads(process.stdout)
    assert result["key_present"] is True
    assert result["provider_probed"] is False
    assert result["ready_to_attempt_generation"] is False
    assert "PRIVATE-TEST-CREDENTIAL" not in process.stdout + process.stderr
    assert fingerprint(settings) == before
    invalid = inspect_status(
        settings, configured(provider="PRIVATE-TEST-CREDENTIAL", model="PRIVATE-TEST-CREDENTIAL")
    )
    assert "PRIVATE-TEST-CREDENTIAL" not in json.dumps(invalid)
