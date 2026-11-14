"""Test snapshot verification and retention with small synthetic databases.

The fixtures contain no NASA data. They only reproduce the table layout that the
backend importer writes, so the checks run without Docker or backend dependencies.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import snapshot_tools as tools  # noqa: E402

RESTORE = Path(__file__).with_name("restore_snapshot.py")


def make_database(path: Path) -> dict:
    points = [{"x": 0, "y": 1}, {"x": 1, "y": 2}, {"x": 2, "y": 3}]
    entities = (
        [("investigation", f"inv{i}", i, {"id": f"inv{i}"}) for i in range(2)]
        + [("record", "r0", 0, {"record_type": "trial_row"}),
           ("record", "r1", 1, {"record_type": "trial_row"}),
           ("record", "r2", 2, {"record_type": "operating_condition_row"})]
        + [("series", "s0", 0, {"id": "s0", "points": points})]
    )
    counts = {"investigation": 2, "record": 3, "series": 1}
    metadata = {
        "corpus_version": "synthetic-test",
        "seed_sha256": "a" * 64,
        "entity_counts": counts,
        "statistics": {"time_series_points": len(points)},
    }
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE fl_corpus (id INTEGER PRIMARY KEY, metadata_json TEXT)")
        connection.execute(
            "CREATE TABLE fl_entities (kind TEXT, identifier TEXT, ordinal INTEGER, payload_json TEXT)"
        )
        connection.execute("INSERT INTO fl_corpus VALUES (1, ?)", (json.dumps(metadata),))
        connection.executemany(
            "INSERT INTO fl_entities VALUES (?, ?, ?, ?)",
            [(k, i, o, json.dumps(p)) for k, i, o, p in entities],
        )
        connection.execute(f"PRAGMA user_version={tools.SCHEMA_VERSION}")
        connection.commit()
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    return {
        "corpus_version": "synthetic-test",
        "seed_sha256": "a" * 64,
        "investigations": 2,
        "records": 3,
        "trial_rows": 2,
        "series": 1,
        "points": 3,
    }


def make_snapshot(root: Path, name: str) -> Path:
    directory = root / name
    directory.mkdir(parents=True)
    facts = make_database(directory / tools.DATABASE_NAME)
    (directory / tools.SEED_REFERENCE_NAME).write_text('{"sha256": "' + "a" * 64 + '"}\n', encoding="utf-8")
    manifest = {
        "format": tools.MANIFEST_FORMAT,
        "project": "flareledger",
        "kind": "daily",
        "application": {"image_tag": "flareledger-api:test", "image_id": "sha256:test"},
        "corpus": facts,
    }
    (directory / tools.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    tools.write_checksums(directory)
    return directory


class SnapshotTests(unittest.TestCase):
    def test_complete_snapshot_verifies(self):
        with tempfile.TemporaryDirectory() as folder:
            snapshot = make_snapshot(Path(folder), "flareledger-daily-20261114T031000Z-aaaaaaaa")
            self.assertEqual(tools.verify_snapshot(snapshot)["corpus"]["points"], 3)

    def test_altered_database_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            snapshot = make_snapshot(Path(folder), "flareledger-daily-20261114T031000Z-aaaaaaaa")
            with (snapshot / tools.DATABASE_NAME).open("ab") as handle:
                handle.write(b"x")
            with self.assertRaisesRegex(tools.SnapshotError, "Checksum mismatch"):
                tools.verify_snapshot(snapshot)

    def test_missing_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            snapshot = make_snapshot(Path(folder), "flareledger-daily-20261114T031000Z-aaaaaaaa")
            (snapshot / tools.SEED_REFERENCE_NAME).unlink()
            with self.assertRaisesRegex(tools.SnapshotError, "incomplete"):
                tools.verify_snapshot(snapshot)

    def test_manifest_that_misdescribes_the_database_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            snapshot = make_snapshot(Path(folder), "flareledger-daily-20261114T031000Z-aaaaaaaa")
            manifest = json.loads((snapshot / tools.MANIFEST_NAME).read_text(encoding="utf-8"))
            manifest["corpus"]["points"] = 99
            (snapshot / tools.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
            tools.write_checksums(snapshot)
            with self.assertRaisesRegex(tools.SnapshotError, "does not describe"):
                tools.verify_snapshot(snapshot)

    def test_database_missing_points_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            snapshot = make_snapshot(Path(folder), "flareledger-daily-20261114T031000Z-aaaaaaaa")
            with closing(sqlite3.connect(snapshot / tools.DATABASE_NAME)) as connection:
                connection.execute("UPDATE fl_entities SET payload_json='{\"points\": []}' WHERE kind='series'")
                connection.commit()
                connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            tools.write_checksums(snapshot)
            with self.assertRaisesRegex(tools.SnapshotError, "Measured points"):
                tools.verify_snapshot(snapshot)

    def test_retention_keeps_newest_of_one_kind_and_ignores_other_names(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            daily = [f"flareledger-daily-2026111{day}T031000Z-aaaaaaa{day}" for day in range(1, 10)]
            for name in daily:
                (root / name).mkdir()
            pre = root / "flareledger-pre-update-20261101T000000Z-bbbbbbbb"
            pre.mkdir()
            foreign = root / "notes-do-not-delete"
            foreign.mkdir()
            removed = tools.prune(root, "daily", 7)
            self.assertEqual(sorted(removed), sorted(daily[:2]))
            remaining = sorted(path.name for path in root.iterdir())
            self.assertEqual(len([n for n in remaining if "-daily-" in n]), 7)
            self.assertTrue(pre.exists() and foreign.exists())

    def test_retention_requires_at_least_one_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                tools.prune(Path(folder), "daily", 0)

    def test_restore_refuses_project_names_that_could_hit_the_live_stack(self):
        result = subprocess.run(
            [sys.executable, str(RESTORE), "missing", "--project", "flareledger"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("must start with flareledger-restore", result.stderr)


if __name__ == "__main__":
    unittest.main()
