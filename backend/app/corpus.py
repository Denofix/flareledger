"""Validate provenance before deriving any searchable SQLite records."""

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

SEED_FORMAT = "flareledger.nasa_demo.v2"
SCHEMA_VERSION = 1
COLLECTIONS = {
    "investigations": "investigation",
    "trial_records": "record",
    "time_series": "series",
    "sources": "source",
    "evidence": "evidence",
    "quality_issues": "quality_issue",
    "knowledge_cards": "knowledge_card",
    "graph_presets": "graph_preset",
    "raw_tables": "raw_table",
}


class ImportRejected(ValueError):
    """The input cannot become a verified corpus."""


def encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":"))


def reject_constant(value: str) -> None:
    raise ImportRejected(f"Non-finite JSON number: {value}")


def load_verified_seed(seed: Path, manifest_path: Path) -> tuple[bytes, dict, dict]:
    raw = seed.read_bytes()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(raw).hexdigest()
    if digest != manifest.get("sha256") or len(raw) != manifest.get("byte_length"):
        raise ImportRejected("Seed checksum or byte length does not match its manifest.")
    data = json.loads(raw, parse_constant=reject_constant)
    if (
        data.get("format") != SEED_FORMAT
        or manifest.get("seed_format") != SEED_FORMAT
        or data.get("language") != "en"
        or manifest.get("language") != "en"
    ):
        raise ImportRejected("Expected the English flareledger.nasa_demo.v2 corpus.")
    validate(data, manifest)
    return raw, data, manifest


def validate(data: dict, manifest: dict) -> None:
    identifiers = {}
    for collection, kind in COLLECTIONS.items():
        values = data.get(collection)
        if not isinstance(values, list):
            raise ImportRejected(f"Missing collection: {collection}")
        ids = [value.get("id") for value in values]
        if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
            raise ImportRejected(f"Missing or duplicate identifiers in {collection}.")
        identifiers[kind] = set(ids)

    references = {
        "source_id": "source",
        "source_ids": "source",
        "evidence_id": "evidence",
        "evidence_ids": "evidence",
        "investigation_id": "investigation",
        "investigation_ids": "investigation",
        "related_investigation_ids": "investigation",
        "trial_record_id": "record",
        "quality_issue_ids": "quality_issue",
        "series_ids": "series",
        "embedded_raw_table_id": "raw_table",
    }

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in references:
                    refs = child if isinstance(child, list) else [child]
                    if any(ref is not None and ref not in identifiers[references[key]] for ref in refs):
                        raise ImportRejected(f"Unresolved {key} reference.")
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(data)
    series = data["time_series"]
    if any(s.get("synthetic") is not False or len(s["points"]) != s["point_count"] for s in series):
        raise ImportRejected("Series must retain their non-synthetic points and point counts.")
    actual = {
        "investigations": len(data["investigations"]),
        "experimental_tables": len(data["raw_tables"]),
        "normalized_table_records_including_non_trials": len(data["trial_records"]),
        "original_table_data_rows_including_notes": len(data["trial_records"]),
        "record_types": dict(Counter(r["record_type"] for r in data["trial_records"])),
        "numerical_time_series": len(series),
        "time_series_points": sum(len(s["points"]) for s in series),
        "source_records": len(data["sources"]),
        "knowledge_cards": len(data["knowledge_cards"]),
        "quality_issues": len(data["quality_issues"]),
        "external_public_file_catalog_entries": len(data["download_catalog"]),
    }
    for key, value in actual.items():
        if data["statistics"].get(key) != value or manifest["statistics"].get(key) != value:
            raise ImportRejected(f"Corpus statistics do not match: {key}")
    catalog_ids = [catalog_id(row) for row in data["download_catalog"]]
    if len(set(catalog_ids)) != len(catalog_ids):
        raise ImportRejected("Duplicate public-file catalog key.")


def catalog_id(item: dict) -> str:
    """Technical lookup key, never an experimental trial identifier."""
    return f"{item['investigation_id']}:{item['nasa_file_id']}:{item['file_version']}"


def search_text(item: dict) -> str:
    """Lexical discovery indexes only text, never numeric curve points or raw files."""
    fields = (
        "id",
        "title",
        "title_en",
        "acronym",
        "summary_en",
        "text_en",
        "material",
        "original_test_id",
        "original_trial_label",
        "record_type",
        "fuel_phase",
        "gravity_regime",
        "description_en",
        "quality_note_en",
        "document_type",
        "tags",
    )
    return " ".join(str(item[key]) for key in fields if item.get(key) is not None).casefold()
