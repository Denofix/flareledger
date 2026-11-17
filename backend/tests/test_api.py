import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import zlib
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import ROOT, Settings
from app.corpus import ImportRejected
from app.ingest import import_corpus
from app.main import create_app
from app.storage import Repository


def test_process_lives_without_creating_or_importing_database(tmp_path):
    settings = Settings(tmp_path / "absent/state.sqlite3", ROOT / "data")
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/health/live").json() == {"status": "ok"}
        ready = client.get("/api/health/ready")
        assert ready.status_code == 503
        assert ready.json()["error"]["code"] == "corpus_unavailable"
        assert client.get("/api/investigations").status_code == 503
    assert not settings.database_path.exists()
    assert not settings.database_path.parent.exists()


def test_ready_and_metadata_identify_the_required_corpus(client, seed):
    assert client.get("/api/health/ready").status_code == 200
    meta = client.get("/api/meta").json()
    assert meta["statistics"] == seed["statistics"]
    assert (
        meta["seed_sha256"]
        == hashlib.sha256((ROOT / "data/demo/FlareLedger_NASA_Demo_Data.json").read_bytes()).hexdigest()
    )
    assert meta["live_generation_available"] is False
    assert "GEMINI_API_KEY" not in json.dumps(meta)


def test_complete_source_bytes_are_preserved(settings):
    with Repository(settings).connection() as connection:
        compressed = connection.execute("SELECT seed_zlib FROM fl_corpus WHERE id=1").fetchone()[0]
    assert zlib.decompress(compressed) == settings.seed_path.read_bytes()


def test_repeat_import_is_idempotent(settings):
    before = Repository(settings).readiness()
    result = import_corpus(settings)
    assert result["status"] == "already_present"
    assert Repository(settings).readiness() == before


def test_catalog_and_record_types_remain_distinct(client, seed):
    assert client.get("/api/investigations").json()["items"] == seed["investigations"]
    assert client.get("/api/records").json()["total"] == 1132
    trials = client.get("/api/trials").json()
    assert trials["total"] == 647
    assert all(record["record_type"] == "trial_row" for record in trials["items"])
    conditions = client.get("/api/records", params={"record_type": "operating_condition_row"}).json()
    assert conditions["total"] == 469
    assert all(item["record_type"] == "operating_condition_row" for item in conditions["items"])
    assert client.get("/api/files").json()["total"] == 8369


def test_record_preserves_nulls_quantities_and_evidence(client, seed):
    original = seed["trial_records"][0]
    response = client.get("/api/records/" + original["id"]).json()
    assert response["item"] == original
    assert response["item"]["pressure_kpa"] is None
    assert response["evidence"] == [e for e in seed["evidence"] if e["id"] in original["evidence_ids"]]
    assert response["sources"] == [s for s in seed["sources"] if s["id"] in original["source_ids"]]
    assert response["evidence"][0]["independent_human_review"] is False


def test_every_measured_series_preserves_all_values_units_and_limitations(client, seed):
    assert client.get("/api/series").json()["total"] == 6
    assert all("points" not in s for s in client.get("/api/series").json()["items"])
    points = 0
    for original in seed["time_series"]:
        response = client.get("/api/series/" + original["id"])
        assert response.status_code == 200
        assert response.json()["item"] == original
        assert response.json()["sources"]
        assert response.json()["evidence"]
        assert original["uncertainty"] is None
        points += len(response.json()["item"]["points"])
    assert points == 1844


def test_raw_table_and_knowledge_cards_keep_attribution(client, seed):
    table = seed["raw_tables"][0]
    assert client.get("/api/raw-tables/" + table["id"]).json()["item"] == table
    assert client.get("/api/knowledge-cards").json()["items"] == seed["knowledge_cards"]
    assert client.get("/api/graph-presets").json()["items"] == seed["graph_presets"]


def test_filters_pagination_and_json_404(client, seed):
    records = [r for r in seed["trial_records"] if r["investigation_id"] == "PSI-25"]
    result = client.get("/api/records", params={"investigation_id": "PSI-25", "offset": 2, "limit": 3})
    assert result.json()["items"] == records[2:5]
    assert result.json()["total"] == len(records)
    missing = client.get("/api/investigations/__infra_unknown_id__")
    assert missing.status_code == 404
    assert missing.headers["content-type"].startswith("application/json")
    assert client.get("/api/records", params={"investigation_id": "unknown"}).status_code == 404


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_pagination_is_bounded(client, params):
    assert client.get("/api/records", params=params).status_code == 422


def test_lexical_search_returns_citations_and_literal_input_is_not_sql(client):
    response = client.get("/api/search", params={"q": "PMMA", "limit": 5})
    assert response.status_code == 200
    result = response.json()
    assert result["method"] == "lexical_keywords"
    assert result["items"]
    assert all(item["sources"] for item in result["items"])
    assert client.get("/api/search", params={"q": "' OR 1=1 --"}).json()["items"] == []
    assert client.get("/api/search", params={"q": "a" * 241}).status_code == 422
    assert client.get("/api/investigations").json()["total"] == 10


def test_comparison_preserves_source_time_and_rejects_different_quantities(client, seed):
    first, second = seed["time_series"][:2]
    result = client.get("/api/compare", params={"ids": first["id"] + "," + second["id"]})
    assert result.status_code == 200
    assert result.json()["transformations"] == []
    assert [item["item"] for item in result.json()["series"]] == [first, second]
    flame = next(s for s in seed["time_series"] if s["y"]["name"] == "ColorCamFlameDiameter_mm")
    assert client.get("/api/compare", params={"ids": first["id"] + "," + flame["id"]}).status_code == 422
    assert client.get("/api/compare", params={"ids": first["id"] + "," + first["id"]}).status_code == 422


@pytest.mark.parametrize("requested_flag", ["false", "true"])
def test_ask_stays_unavailable_with_source_search_and_no_generated_answer(
    client, monkeypatch, requested_flag
):
    monkeypatch.setenv("LLM_ENABLED", requested_flag)
    response = client.post("/api/ask", json={"question": "PMMA"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "llm_unavailable"
    assert response.json()["answer"] is None
    assert response.json()["retrieved_evidence"]
    assert response.headers["cache-control"] == "no-store"
    assert client.get("/api/health/ready").status_code == 200
    assert client.post("/api/ask", json={"question": "  "}).status_code == 422


def test_readiness_detects_incomplete_corpus(client, settings):
    with closing(sqlite3.connect(settings.database_path)) as connection:
        connection.execute("DELETE FROM fl_entities WHERE kind='series' AND ordinal=0")
        connection.commit()
    assert client.get("/api/health/ready").status_code == 503
    assert client.get("/api/health/live").status_code == 200


def test_checksum_failure_preserves_existing_database(settings, tmp_path):
    before = Repository(settings).readiness()
    folder = tmp_path / "bad-data/demo"
    folder.mkdir(parents=True)
    (folder / settings.seed_path.name).write_bytes(settings.seed_path.read_bytes() + b" ")
    shutil.copyfile(settings.manifest_path, folder / settings.manifest_path.name)
    with pytest.raises(ImportRejected, match="checksum"):
        import_corpus(Settings(settings.database_path, folder.parent))
    assert Repository(settings).readiness() == before


def test_duplicate_identifier_is_rejected_before_database_creation(seed, tmp_path):
    data = json.loads(json.dumps(seed))
    data["investigations"][1]["id"] = data["investigations"][0]["id"]
    folder = tmp_path / "bad-data/demo"
    folder.mkdir(parents=True)
    raw = json.dumps(data).encode()
    manifest = json.loads((ROOT / "data/demo/seed-reference.json").read_text())
    manifest.update(sha256=hashlib.sha256(raw).hexdigest(), byte_length=len(raw))
    (folder / "FlareLedger_NASA_Demo_Data.json").write_bytes(raw)
    (folder / "seed-reference.json").write_text(json.dumps(manifest))
    settings = Settings(tmp_path / "untouched/state.sqlite3", folder.parent)
    with pytest.raises(ImportRejected, match="duplicate"):
        import_corpus(settings)
    assert not settings.database_path.exists()


def test_importer_refuses_unrelated_database(tmp_path):
    settings = Settings(tmp_path / "unrelated.sqlite3", ROOT / "data")
    with closing(sqlite3.connect(settings.database_path)) as connection:
        connection.execute("CREATE TABLE unrelated (value TEXT)")
        connection.execute("INSERT INTO unrelated VALUES ('preserve-me')")
        connection.commit()
    with pytest.raises(ImportRejected, match="unrelated"):
        import_corpus(settings)
    with closing(sqlite3.connect(settings.database_path)) as connection:
        assert connection.execute("SELECT value FROM unrelated").fetchone() == ("preserve-me",)


def test_backup_restore_and_new_app_instance_retain_real_corpus(settings, tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/backup_sqlite.py")],
        env={**os.environ, "DATABASE_PATH": str(settings.database_path)},
        capture_output=True,
        text=True,
        check=True,
    )
    backup = Path(result.stdout.splitlines()[0])
    restored = tmp_path / "restored/state.sqlite3"
    restored.parent.mkdir()
    shutil.copyfile(backup, restored)
    with TestClient(create_app(Settings(restored, settings.data_dir))) as client:
        assert client.get("/api/health/ready").status_code == 200
        assert client.get("/api/records").json()["total"] == 1132
        assert client.get("/api/series").json()["total"] == 6
        assert (
            client.get("/api/meta").json()["seed_sha256"] == Repository(settings).readiness()["seed_sha256"]
        )


def test_openapi_and_interactive_docs_are_available_without_corpus(tmp_path):
    with TestClient(create_app(Settings(tmp_path / "absent.sqlite3", ROOT / "data"))) as client:
        assert client.get("/api/docs").status_code == 200
        schema = client.get("/api/openapi.json").json()
        assert "/api/records" in schema["paths"]
        assert "/api/compare" in schema["paths"]
