"""Real frozen evidence and query variants. No model responses are graded here."""

import hashlib
import json
import socket
import zipfile
from unittest import mock

import pytest

from app.config import ROOT
from app.llm import LLMSettings, request_payload
from app.retrieval import docx_paragraphs, retrieve
from app.storage import Repository

CASES = json.loads((ROOT / "docs/ai-evaluation-cases.json").read_text())["cases"]


def selection(settings, question):
    repository = Repository(settings)
    with repository.connection() as db:
        return retrieve(repository, db, question)


def packets(context):
    return {item["id"]: json.loads(item["support_text"]) for item in context}


@pytest.mark.parametrize(
    "question",
    [
        CASES[0]["question"],
        "Find PMMA samples in BASS and BASS-II, including the ReadMe.",
        "Which BASS-II and BASS material cells mention PMMA?",
    ],
)
def test_both_material_tables_and_hash_verified_readme_reach_context(settings, question):
    _, context = selection(settings, question)
    content = packets(context)
    assert {"SRC-TABLE-PSI-25", "SRC-TABLE-PSI-26", "SRC-README-PSI-25"} <= content.keys()
    for source in ("SRC-TABLE-PSI-25", "SRC-TABLE-PSI-26"):
        assert any("PMMA" in " ".join(row["cells_as_reported"]).upper() for row in content[source]["rows"])
    readme = content["SRC-README-PSI-25"]
    text = " ".join(p["text"] for p in readme["paragraphs"])
    assert all(word in text for word in ("films", "slabs", "rods"))
    assert readme["original_sha256"] == "69f32647792f54ab2a561e3cdafc6c87d854564fe487aed2b09265286bd84e1d"
    assert readme["all_paragraphs_included"] is False


@pytest.mark.parametrize(
    "question",
    [
        CASES[11]["question"],
        "Explain the Kapton condition reference in SAME PSI-102.",
        "PSI 102: show definitions 1-4 together with the Kapton row.",
    ],
)
def test_condition_reference_keeps_all_definitions_and_original_units(settings, question):
    _, context = selection(settings, question)
    table = packets(context)["SRC-TABLE-PSI-102"]
    assert table["all_rows_included"] is True and table["total_data_rows"] == 8
    assert [row["normalized_record_type"] for row in table["rows"]] == ["condition_definition"] * 4 + [
        "condition_reference"
    ] * 4
    assert table["rows"][4]["cells_as_reported"] == ["5", "Kapton: same conditions as 1-4", "", "", ""]
    assert table["columns_as_reported"] == [
        "Sample #",
        "Sample Material  ",
        "Air Flow (cm/s)",
        "Weight loss rate (mg/min)",
        "Aging Duration (minutes)",
    ]


@pytest.mark.parametrize(
    "question",
    [
        CASES[12]["question"],
        "Compare the historical contexts of Mir and Apollo 1.",
        "For Apollo 1 and Mir fire, show the historical cards rather than laboratory data.",
    ],
)
def test_explicit_historical_entities_are_not_displaced_by_broad_science_matches(settings, question):
    hits, context = selection(settings, question)
    first = {item["id"] for item in hits[:2]}
    assert first == {"CARD-SRC-APOLLO-1", "CARD-SRC-MIR-FIRE"}
    content = packets(context)
    assert all(content[identifier]["numeric_experiment"] is False for identifier in first)
    assert all(content[identifier]["role"] == "historical_context" for identifier in first)


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_every_frozen_request_is_bounded_and_original_cells_are_unchanged(settings, seed, case):
    with mock.patch.object(socket.socket, "connect", side_effect=AssertionError("No network permitted")):
        hits, context = selection(settings, case["question"])
    assert len(hits) == len(context) <= 5
    assert len(json.dumps(context).encode()) <= 16000
    tables = {table["id"]: table for table in seed["raw_tables"]}
    for item in context:
        assert len(item["support_text"].encode()) <= 5000
        content = json.loads(item["support_text"])
        if "table_id" in content:
            original = tables[content["table_id"]]
            assert item["source_ids"] == [original["source_id"]]
            assert content["columns_as_reported"] == original["columns_as_reported"]
            assert content["total_data_rows"] == original["data_row_count"]
            for row in content["rows"]:
                assert row["cells_as_reported"] == original["rows_as_reported"][row["data_row_number"] - 1]
    payload = request_payload(LLMSettings(key="MUST-NOT-ENTER-INPUT"), case["question"], context)
    assert json.loads(payload["input"]) == {"question": case["question"], "context": context}
    assert "MUST-NOT-ENTER-INPUT" not in json.dumps(payload)
    assert len(json.dumps(payload).encode()) <= 32768


def test_qualifier_sampling_retains_over_range_negative_and_blank_cells(settings):
    _, context = selection(settings, CASES[1]["question"])
    table = packets(context)["SRC-TABLE-PSI-25"]
    cells = [cell for row in table["rows"] for cell in row["cells_as_reported"]]
    assert "OR" in cells and "" in cells
    assert any(cell.strip().startswith("-") for cell in cells)
    assert table["all_rows_included"] is False


def test_trial_scoping_includes_its_actual_testsheet_and_measurement_metadata(settings):
    _, context = selection(settings, CASES[4]["question"])
    content = packets(context)
    assert {
        "SRC-FLEX-002-TESTSHEET",
        "SRC-FLEX-002-DropletData",
        "SERIES-FLEX-002-DropletData",
    } <= content.keys()
    assert content["SERIES-FLEX-002-DropletData"]["point_count"] == 660
    assert "LLUV" in content["SRC-FLEX-002-TESTSHEET"]["text"]
    assert content["SRC-FLEX-002-DropletData"]["data_rows_not_sent"] is True
    assert "DropletDiameter_mm" in content["SRC-FLEX-002-DropletData"]["header_as_reported"]
    assert "SRC-FLEX-003-TESTSHEET" not in content


def test_specific_investigation_name_does_not_expand_into_a_different_experiment(settings):
    hits, _ = selection(settings, "BASS-II PMMA sensor readings")
    assert all(hit["investigation_id"] == "PSI-25" for hit in hits)


def test_retrieval_is_deterministic_read_only_and_out_of_scope_still_has_no_context(settings):
    before = hashlib.sha256(settings.database_path.read_bytes()).hexdigest()
    first = selection(settings, CASES[0]["question"])
    assert selection(settings, CASES[0]["question"]) == first
    assert selection(settings, CASES[14]["question"]) == ([], [])
    assert hashlib.sha256(settings.database_path.read_bytes()).hexdigest() == before


def test_missing_document_does_not_masquerade_as_original_document_text(settings):
    with mock.patch("app.retrieval.docx_paragraphs", return_value=()):
        _, context = selection(settings, CASES[0]["question"])
    assert "SRC-README-PSI-25" not in packets(context)
    assert {"SRC-TABLE-PSI-25", "SRC-TABLE-PSI-26"} <= packets(context).keys()


def test_docx_is_hash_and_size_checked_and_oversized_xml_is_not_decompressed(tmp_path):
    path = tmp_path / "source.docx"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", "x" * 524289)
    raw = path.read_bytes()
    assert docx_paragraphs(str(path), hashlib.sha256(raw).hexdigest(), len(raw)) == ()
    assert docx_paragraphs(str(path), "0" * 64, len(raw)) == ()
    assert docx_paragraphs(str(tmp_path / "absent.docx"), "0" * 64, 1) == ()
