"""Explicit, checksum-verified corpus import. No network calls or automatic startup import."""

import argparse
import hashlib
import json
import sqlite3
import zlib
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone

from app.config import Settings
from app.corpus import (
    COLLECTIONS,
    SCHEMA_VERSION,
    ImportRejected,
    catalog_id,
    encode,
    load_verified_seed,
    search_text,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS fl_corpus (
    id INTEGER PRIMARY KEY CHECK(id=1), metadata_json TEXT NOT NULL, seed_zlib BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS fl_entities (
    kind TEXT NOT NULL, identifier TEXT NOT NULL, ordinal INTEGER NOT NULL,
    investigation_id TEXT, record_type TEXT, search_text TEXT NOT NULL,
    payload_json TEXT NOT NULL, PRIMARY KEY(kind, identifier)
);
CREATE INDEX IF NOT EXISTS fl_entities_scope ON fl_entities(kind, investigation_id, ordinal);
"""


def import_corpus(settings: Settings, replace: bool = False) -> dict:
    raw, data, manifest = load_verified_seed(settings.seed_path, settings.manifest_path)
    records = []
    for collection, kind in COLLECTIONS.items():
        for ordinal, item in enumerate(data[collection]):
            records.append(
                (
                    kind,
                    item["id"],
                    ordinal,
                    item.get("investigation_id"),
                    item.get("record_type"),
                    search_text(item),
                    encode(item),
                )
            )
    for ordinal, item in enumerate(data["download_catalog"]):
        records.append(("file", catalog_id(item), ordinal, item["investigation_id"], None, "", encode(item)))
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "seed_format": data["format"],
        "language": data["language"],
        "seed_sha256": hashlib.sha256(raw).hexdigest(),
        "seed_byte_length": len(raw),
        "corpus_version": f"{data['assembled_on']}:{manifest['sha256']}",
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "statistics": data["statistics"],
        "entity_counts": dict(Counter(row[0] for row in records)),
        "license_note": manifest["license_note"],
        "independent_scientific_review": False,
    }
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(settings.database_path, timeout=30)) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if version not in (0, SCHEMA_VERSION) or (tables and "fl_corpus" not in tables):
            raise ImportRejected("Refusing to modify an unrelated or unsupported database.")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript(SCHEMA)
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            old = connection.execute("SELECT metadata_json FROM fl_corpus WHERE id=1").fetchone()
            if old:
                previous = json.loads(old[0])
                if previous["seed_sha256"] == metadata["seed_sha256"]:
                    counts = dict(connection.execute("SELECT kind, COUNT(*) FROM fl_entities GROUP BY kind"))
                    if counts != metadata["entity_counts"]:
                        raise ImportRejected("Existing corpus is incomplete; restore a verified backup.")
                    return {"status": "already_present", **previous}
                if not replace:
                    raise ImportRejected(
                        "A different corpus is installed; back it up before using --replace."
                    )
            connection.execute("DELETE FROM fl_entities")
            connection.executemany("INSERT INTO fl_entities VALUES (?, ?, ?, ?, ?, ?, ?)", records)
            connection.execute(
                "INSERT OR REPLACE INTO fl_corpus VALUES (1, ?, ?)", (encode(metadata), zlib.compress(raw))
            )
            connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    return {"status": "imported", **metadata}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--replace", action="store_true", help="Replace a different corpus after taking a backup"
    )
    arguments = parser.parse_args()
    try:
        print(json.dumps(import_corpus(Settings.from_env(), replace=arguments.replace), indent=2))
    except (ImportRejected, OSError, KeyError, TypeError, sqlite3.Error, ValueError) as exc:
        parser.exit(1, f"Import rejected: {exc}\n")


if __name__ == "__main__":
    main()
