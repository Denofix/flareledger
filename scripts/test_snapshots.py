"""Test snapshot verification and retention with small synthetic databases.

The fixtures contain no NASA data. They only reproduce the table layout that the
backend importer writes, so the checks run without Docker or backend dependencies.
"""

from __future__ import annotations

import contextlib
import io
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backup_production  # noqa: E402
import restore_snapshot  # noqa: E402
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


def make_snapshot(root: Path, name: str, revision: str = "0" * 40) -> Path:
    directory = root / name
    directory.mkdir(parents=True)
    facts = make_database(directory / tools.DATABASE_NAME)
    (directory / tools.SEED_REFERENCE_NAME).write_text('{"sha256": "' + "a" * 64 + '"}\n', encoding="utf-8")
    manifest = {
        "format": tools.MANIFEST_FORMAT,
        "project": "flareledger",
        "kind": "daily",
        "application": {
            "image_reference": "flareledger-api:abc1234",
            "release_tag": "abc1234",
            "image_id": "sha256:test",
            "revision": revision,
            "revision_source": "image-tag",
        },
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


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), "-c", "user.name=test", "-c", "user.email=test@example.invalid", *arguments],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def make_source(root: Path) -> tuple[Path, list[str]]:
    """A tiny git checkout with a compose.yaml and corpus manifest; returns (path, [sha1, sha2])."""
    source = root / "source"
    (source / "data" / "demo").mkdir(parents=True)
    git(source, "init", "-q")
    (source / "compose.yaml").write_text("name: flareledger\n", encoding="utf-8")
    (source / "data" / "demo" / "seed-reference.json").write_text('{"sha256": "' + "a" * 64 + '"}\n', encoding="utf-8")
    git(source, "add", "-A")
    git(source, "commit", "-q", "-m", "first")
    first = git(source, "rev-parse", "HEAD")
    (source / "later.txt").write_text("later\n", encoding="utf-8")
    git(source, "add", "-A")
    git(source, "commit", "-q", "-m", "second")
    return source, [first, git(source, "rev-parse", "HEAD")]


class RevisionTests(unittest.TestCase):
    def test_release_tag_is_only_the_part_after_the_colon(self):
        self.assertEqual(tools.release_tag("flareledger-api:8be005f"), "8be005f")
        for bad in ("flareledger-api:flareledger-api:8be005f", "other:8be005f", "8be005f", "flareledger-api:"):
            with self.assertRaises(tools.SnapshotError, msg=bad):
                tools.release_tag(bad)

    def test_revision_comes_from_the_image_tag_not_from_the_checked_out_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            source, (first, second) = make_source(Path(folder))
            self.assertEqual(git(source, "rev-parse", "HEAD"), second)
            block = backup_production.application_block(f"flareledger-api:{first[:7]}", "sha256:x", source, None)
            self.assertEqual(block["revision"], first)
            self.assertNotEqual(block["revision"], second)
            self.assertEqual(block["release_tag"], first[:7])
            self.assertEqual(block["revision_source"], "image-tag")

    def test_unresolvable_tags_are_refused_instead_of_guessed(self):
        with tempfile.TemporaryDirectory() as folder:
            source, _ = make_source(Path(folder))
            for tag in ("local", "latest", "deadbeef"):
                with self.assertRaises(tools.SnapshotError, msg=tag):
                    backup_production.application_block(f"flareledger-api:{tag}", "sha256:x", source, None)

    def test_explicit_revision_must_be_a_full_sha(self):
        with tempfile.TemporaryDirectory() as folder:
            source, (first, _) = make_source(Path(folder))
            with self.assertRaises(backup_production.BackupError):
                backup_production.application_block("flareledger-api:local", "sha256:x", source, "abc1234")
            block = backup_production.application_block("flareledger-api:local", "sha256:x", source, first)
            self.assertEqual((block["revision"], block["revision_source"]), (first, "override"))


class FakeDocker:
    """Records commands and answers like a Docker host on which the restore project is absent."""

    def __init__(self, project_exists: bool = False):
        self.calls: list[tuple[list[str], dict | None]] = []
        self.project_exists = project_exists
        self.probe = {
            "ready": "ready", "corpus_version": "synthetic-test", "investigations": 2,
            "records": 3, "trial_rows": 2, "series": 1, "points": 3,
        }

    def __call__(self, command, env=None, cwd=None):
        self.calls.append((list(command), env))
        if command[:3] == ["docker", "volume", "inspect"]:
            if self.project_exists:
                return "[]"
            raise restore_snapshot.RestoreError("no such volume")
        if command[:2] == ["docker", "ps"]:
            return ""
        if command[:3] == ["docker", "image", "inspect"]:
            return "[]"
        if "ps" in command and "--format" in command:
            return "healthy\n"
        if "exec" in command:
            return json.dumps(self.probe) + "\n"
        return ""

    def words(self) -> list[str]:
        return [word for command, _ in self.calls for word in command]


def restore(arguments: list[str], docker: FakeDocker) -> tuple[int, str]:
    errors = io.StringIO()
    with mock.patch.object(restore_snapshot, "run", docker), contextlib.redirect_stdout(io.StringIO()), \
            contextlib.redirect_stderr(errors):
        code = restore_snapshot.main(arguments)
    return code, errors.getvalue()


class RestoreSafetyTests(unittest.TestCase):
    def test_wrong_snapshot_path_with_cleanup_runs_no_docker_command(self):
        with tempfile.TemporaryDirectory() as folder:
            source, _ = make_source(Path(folder))
            docker = FakeDocker(project_exists=True)
            code, errors = restore(
                [str(Path(folder) / "no-such-snapshot"), "--source-dir", str(source), "--cleanup",
                 "--project", "flareledger-restore-existing"],
                docker,
            )
            self.assertEqual(code, 1)
            self.assertEqual(docker.calls, [])
            self.assertIn("RESTORE_FAILED", errors)

    def test_existing_restore_project_is_never_adopted_or_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            source, (_, second) = make_source(Path(folder))
            snapshot = make_snapshot(Path(folder), "flareledger-daily-20261114T031000Z-aaaaaaaa", second)
            docker = FakeDocker(project_exists=True)
            code, errors = restore(
                [str(snapshot), "--source-dir", str(source), "--cleanup",
                 "--project", "flareledger-restore-existing"],
                docker,
            )
            self.assertEqual(code, 1)
            self.assertIn("already exists", errors)
            self.assertIn("NOT_CLEANED", errors)
            for forbidden in ("down", "create", "up", "run"):
                self.assertNotIn(forbidden, docker.words())

    def test_source_revision_mismatch_is_refused_before_docker(self):
        with tempfile.TemporaryDirectory() as folder:
            source, (first, second) = make_source(Path(folder))
            snapshot = make_snapshot(Path(folder), "flareledger-daily-20261114T031000Z-aaaaaaaa", first)
            docker = FakeDocker()
            self.assertEqual(tools.git_head(source), second)
            code, errors = restore([str(snapshot), "--source-dir", str(source), "--cleanup"], docker)
            self.assertEqual(code, 1)
            self.assertIn("--source-dir is at", errors)
            self.assertIn("git worktree add", errors)
            self.assertEqual(docker.calls, [])

    def test_snapshot_without_a_recorded_revision_needs_an_explicit_one(self):
        with tempfile.TemporaryDirectory() as folder:
            source, (first, second) = make_source(Path(folder))
            snapshot = make_snapshot(Path(folder), "flareledger-daily-20261114T031000Z-aaaaaaaa", first)
            manifest = json.loads((snapshot / tools.MANIFEST_NAME).read_text(encoding="utf-8"))
            del manifest["application"]["revision"]
            (snapshot / tools.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
            tools.write_checksums(snapshot)
            docker = FakeDocker()
            code, errors = restore([str(snapshot), "--source-dir", str(source)], docker)
            self.assertEqual(code, 1)
            self.assertIn("--revision", errors)
            self.assertEqual(docker.calls, [])

    def test_matching_revision_restores_with_the_short_image_tag_and_cleans_only_its_own_project(self):
        with tempfile.TemporaryDirectory() as folder:
            source, (first, second) = make_source(Path(folder))
            snapshot = make_snapshot(Path(folder), "flareledger-daily-20261114T031000Z-aaaaaaaa", second)
            docker = FakeDocker()
            code, errors = restore([str(snapshot), "--source-dir", str(source), "--cleanup"], docker)
            self.assertEqual(code, 0, errors)
            compose_calls = [(c, e) for c, e in docker.calls if c[:2] == ["docker", "compose"]]
            self.assertTrue(compose_calls)
            for command, env in compose_calls:
                project = command[command.index("--project-name") + 1]
                self.assertTrue(project.startswith("flareledger-restore-"))
                if env:
                    self.assertEqual(env["IMAGE_TAG"], "abc1234")
            image_checks = [c for c, _ in docker.calls if c[:3] == ["docker", "image", "inspect"]]
            self.assertEqual(image_checks, [["docker", "image", "inspect", "flareledger-api:abc1234"]])
            downs = [c for c, _ in compose_calls if "down" in c]
            self.assertEqual(len(downs), 1)
            self.assertIn("--volumes", downs[0])

    def test_mismatching_restored_data_fails_the_restore(self):
        with tempfile.TemporaryDirectory() as folder:
            source, (first, second) = make_source(Path(folder))
            snapshot = make_snapshot(Path(folder), "flareledger-daily-20261114T031000Z-aaaaaaaa", second)
            docker = FakeDocker()
            docker.probe["points"] = 2
            code, errors = restore([str(snapshot), "--source-dir", str(source)], docker)
            self.assertEqual(code, 1)
            self.assertIn("does not match", errors)


if __name__ == "__main__":
    unittest.main()
