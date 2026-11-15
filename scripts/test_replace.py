"""Test database replacement and rollback with real file swaps and a fake Docker host.

The swap and undo scripts that run inside the helper container are executed here for
real against temporary directories, so file moves, checksums and kept copies are
tested for real. Docker itself is replaced by an in-memory fake. Databases are
synthetic and contain no NASA data.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rehearse_replace  # noqa: E402
import replace_database as replace  # noqa: E402
import snapshot_tools as snap  # noqa: E402
import test_snapshots as fixtures  # noqa: E402
import deploy_tools  # noqa: E402


def run_script(script: str, state: Path, snapshot: Path | None, *arguments: str) -> subprocess.CompletedProcess:
    environment = {**os.environ, "STATE_DIR": str(state)}
    if snapshot is not None:
        environment["SNAPSHOT_DIR"] = str(snapshot)
    return subprocess.run([sys.executable, "-c", script, *arguments], env=environment, capture_output=True, text=True)


def make_variant(root: Path, name: str, marker: bool = False, seed: str | None = None) -> Path:
    """A synthetic snapshot; marker adds a table, seed changes the corpus identity."""
    directory = fixtures.make_snapshot(root, name)
    database = directory / snap.DATABASE_NAME
    manifest = json.loads((directory / snap.MANIFEST_NAME).read_text(encoding="utf-8"))
    with closing(sqlite3.connect(database)) as connection:
        if marker:
            connection.execute("CREATE TABLE rehearsal_marker (note TEXT)")
        if seed:
            metadata = json.loads(connection.execute("SELECT metadata_json FROM fl_corpus").fetchone()[0])
            metadata["seed_sha256"] = seed
            connection.execute("UPDATE fl_corpus SET metadata_json=?", (json.dumps(metadata),))
            manifest["corpus"]["seed_sha256"] = seed
        connection.commit()
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    for leftover in (database.with_name(database.name + "-wal"), database.with_name(database.name + "-shm")):
        leftover.unlink(missing_ok=True)
    manifest["database_sha256"] = snap.sha256_file(database)
    (directory / snap.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    snap.write_checksums(directory)
    return directory


class FakeHost:
    """Docker stand-in. The state volume is a real directory."""

    def __init__(self, state: Path, seed: str = "a" * 64):
        self.state, self.seed, self.running = state, seed, True
        self.log: list[list[str]] = []
        self.unready: set[str] = set()
        self.fail_swap = False
        self.fail_undo = False
        self.fail_start = False

    def words(self) -> list[str]:
        return [word for command in self.log for word in command]

    def live_sha(self) -> str:
        return snap.sha256_file(self.state / snap.DATABASE_NAME)

    def facts(self) -> dict:
        database = self.state / snap.DATABASE_NAME
        if not database.exists() or self.live_sha() in self.unready:
            return {"ready": "unavailable"}
        try:
            return {"ready": "ready", **snap.database_facts(database)}
        except snap.SnapshotError:
            return {"ready": "unavailable"}

    def __call__(self, command, env=None, cwd=None, pass_fds=()):
        self.log.append(list(command))
        if command[:2] == ["docker", "ps"]:
            return "cid1\n" if self.running or "--all" in command else ""
        if command[:3] == ["docker", "image", "inspect"]:
            return "sha256:test-image\n"
        if command[:3] == ["docker", "volume", "inspect"]:
            return "vol1\n"
        if command[:2] == ["docker", "inspect"]:
            fmt = command[-1]
            if "Config.Image" in fmt:
                return "flareledger-api:abc1234\n"
            if "Mounts" in fmt:
                return "vol1\n"
            if fmt == "{{.Image}}":
                return "sha256:test-image\n"
            return "healthy\n" if self.running else "exited\n"
        if command[:2] == ["docker", "exec"]:
            if not self.running:
                raise replace.ReplaceError("container is not running")
            return (self.seed if "seed-reference" in command[-1] else json.dumps(self.facts())) + "\n"
        if command[:2] == ["docker", "stop"]:
            self.running = False
            return ""
        if command[:2] == ["docker", "start"]:
            if self.fail_start:
                raise replace.ReplaceError("container start failed")
            self.running = True
            return ""
        if command[:3] == ["docker", "run", "--rm"]:
            index = command.index("-c")
            script, arguments = command[index + 1], command[index + 2:]
            if "seed-reference" in script:
                return self.seed + "\n"
            if (self.fail_swap and ".incoming" in script) or (self.fail_undo and "no kept previous file" in script):
                raise replace.ReplaceError("helper failed")
            mounts = [word for word in command if word.endswith(":/snapshot:ro")]
            snapshot = Path(mounts[0][: -len(":/snapshot:ro")]) if mounts else None
            result = run_script(script, self.state, snapshot, *arguments)
            if result.returncode != 0:
                raise replace.ReplaceError(result.stderr.strip())
            return result.stdout
        if command[0] == sys.executable:
            return "BACKUP_OK | kind=pre-update | snapshot=flareledger-pre-update-20261114T000000Z-aaaaaaaa | kept<=7\n"
        raise AssertionError(f"unexpected command {command}")


class SwapScriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state = self.root / "state"
        self.state.mkdir()
        fixtures.make_database(self.state / snap.DATABASE_NAME)
        self.original = snap.sha256_file(self.state / snap.DATABASE_NAME)

    def test_swap_installs_the_snapshot_and_keeps_the_previous_file(self):
        snapshot = make_variant(self.root, "flareledger-daily-20261114T031000Z-bbbbbbbb", marker=True)
        (self.state / "flareledger.sqlite3-wal").write_bytes(b"stale")
        expected = snap.sha256_file(snapshot / snap.DATABASE_NAME)
        result = run_script(replace.SWAP, self.state, snapshot, "S1", expected)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(snap.sha256_file(self.state / snap.DATABASE_NAME), expected)
        self.assertEqual(snap.sha256_file(self.state / "flareledger.sqlite3.replaced-S1"), self.original)
        self.assertTrue((self.state / "flareledger.sqlite3.replaced-S1-wal").exists())
        self.assertFalse((self.state / "flareledger.sqlite3-wal").exists())
        self.assertFalse((self.state / "flareledger.sqlite3.incoming").exists())

    def test_checksum_mismatch_leaves_the_live_file_untouched(self):
        snapshot = make_variant(self.root, "flareledger-daily-20261114T031000Z-bbbbbbbb", marker=True)
        result = run_script(replace.SWAP, self.state, snapshot, "S1", "0" * 64)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(snap.sha256_file(self.state / snap.DATABASE_NAME), self.original)
        self.assertEqual(sorted(path.name for path in self.state.iterdir()), [snap.DATABASE_NAME])

    def test_undo_restores_the_kept_file_and_keeps_what_it_replaced(self):
        snapshot = make_variant(self.root, "flareledger-daily-20261114T031000Z-bbbbbbbb", marker=True)
        swapped = snap.sha256_file(snapshot / snap.DATABASE_NAME)
        run_script(replace.SWAP, self.state, snapshot, "S1", swapped)
        result = run_script(replace.UNDO, self.state, None, "S1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(snap.sha256_file(self.state / snap.DATABASE_NAME), self.original)
        self.assertEqual(snap.sha256_file(self.state / "flareledger.sqlite3.replaced-away-S1"), swapped)

    def test_undo_without_a_kept_file_changes_nothing(self):
        result = run_script(replace.UNDO, self.state, None, "NOPE")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(snap.sha256_file(self.state / snap.DATABASE_NAME), self.original)

    def test_list_names_kept_files_only(self):
        (self.state / "flareledger.sqlite3.replaced-20261114T010000Z").write_bytes(b"x")
        (self.state / "flareledger.sqlite3.replaced-20261114T020000Z").write_bytes(b"x")
        (self.state / "flareledger.sqlite3.replaced-20261114T020000Z-wal").write_bytes(b"x")
        (self.state / "flareledger.sqlite3.replaced-away-20261114T020000Z").write_bytes(b"x")
        out = run_script(replace.LIST, self.state, None).stdout.split()
        self.assertEqual(out, ["20261114T010000Z", "20261114T020000Z"])


class ReplaceFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state = self.root / "state"
        self.state.mkdir()
        self.snapshots = self.root / "snapshots"
        self.snapshots.mkdir()
        fixtures.make_database(self.state / snap.DATABASE_NAME)
        self.original = snap.sha256_file(self.state / snap.DATABASE_NAME)
        self.host = FakeHost(self.state)
        for patch in (
            mock.patch.object(replace, "run", self.host),
            mock.patch.object(replace, "lock", lambda directory, project="flareledger": contextlib.nullcontext()),
            mock.patch.object(replace.time, "sleep", lambda seconds: None),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def invoke(self, *arguments: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = replace.main([*arguments, "--project", "flareledger-rehearsal-x", "--snapshots", str(self.snapshots)])
        return code, out.getvalue(), err.getvalue()

    def events(self) -> list[str]:
        return [json.loads(line)["event"] for line in (self.snapshots / "replace.log").read_text(encoding="utf-8").splitlines()]

    def variant(self, **options) -> Path:
        return make_variant(self.root, "flareledger-daily-20261114T031000Z-bbbbbbbb", **options)

    def test_without_execute_only_a_plan_is_printed(self):
        code, out, _ = self.invoke("replace", str(self.variant(marker=True)))
        self.assertEqual(code, 0)
        self.assertIn("PLAN_ONLY", out)
        self.assertNotIn("stop", self.host.words())
        self.assertEqual(self.host.live_sha(), self.original)

    def test_tampered_snapshot_is_refused_before_any_docker_command(self):
        snapshot = self.variant(marker=True)
        with (snapshot / snap.DATABASE_NAME).open("ab") as handle:
            handle.write(b"x")
        code, _, err = self.invoke("replace", str(snapshot), "--execute")
        self.assertEqual(code, 1)
        self.assertIn("REPLACE_REFUSED", err)
        self.assertEqual(self.host.log, [])

    def test_a_snapshot_of_another_corpus_is_refused_without_the_explicit_flag(self):
        code, _, err = self.invoke("replace", str(self.variant(seed="c" * 64)), "--execute")
        self.assertEqual(code, 1)
        self.assertIn("different corpus", err)
        self.assertNotIn("stop", self.host.words())
        self.assertEqual(self.host.live_sha(), self.original)

    def test_successful_replacement_orders_backup_stop_swap_start_and_keeps_the_old_file(self):
        snapshot = self.variant(marker=True)
        code, out, err = self.invoke("replace", str(snapshot), "--execute")
        self.assertEqual(code, 0, err)
        self.assertIn("REPLACE_OK", out)
        steps = []
        for command in self.host.log:
            if command[0] == sys.executable:
                steps.append("backup")
            elif command[:2] == ["docker", "stop"]:
                steps.append("stop")
            elif command[:3] == ["docker", "run", "--rm"]:
                steps.append("swap")
            elif command[:2] == ["docker", "start"]:
                steps.append("start")
        self.assertEqual(steps, ["backup", "stop", "swap", "start"])
        self.assertEqual(self.host.live_sha(), snap.sha256_file(snapshot / snap.DATABASE_NAME))
        kept = [p for p in self.state.iterdir() if ".replaced-" in p.name]
        self.assertEqual(len(kept), 1)
        self.assertEqual(snap.sha256_file(kept[0]), self.original)
        self.assertTrue(self.host.running)
        self.assertEqual(self.events(), ["started", "ok"])

    def test_failed_post_check_puts_the_previous_database_back(self):
        snapshot = self.variant(marker=True)
        self.host.unready.add(snap.sha256_file(snapshot / snap.DATABASE_NAME))
        code, _, err = self.invoke("replace", str(snapshot), "--execute")
        self.assertEqual(code, 1)
        self.assertIn("ROLLED_BACK", err)
        self.assertEqual(self.host.live_sha(), self.original)
        self.assertTrue(self.host.running)
        self.assertEqual(self.events(), ["started", "rolled_back"])
        self.assertEqual(len([p for p in self.state.iterdir() if "replaced-away" in p.name]), 1)

    def test_corpus_change_that_the_api_rejects_is_rolled_back(self):
        snapshot = self.variant(seed="c" * 64)
        self.host.unready.add(snap.sha256_file(snapshot / snap.DATABASE_NAME))
        code, _, err = self.invoke("replace", str(snapshot), "--execute", "--allow-corpus-change")
        self.assertEqual(code, 1)
        self.assertIn("ROLLED_BACK", err)
        self.assertEqual(self.host.live_sha(), self.original)

    def test_an_api_that_answers_503_is_reported_in_plain_words_not_as_a_traceback(self):
        snapshot = self.variant(marker=True)
        self.host.unready.add(snap.sha256_file(snapshot / snap.DATABASE_NAME))
        _, _, err = self.invoke("replace", str(snapshot), "--execute")
        self.assertIn("does not serve what the snapshot contains", err)
        self.assertNotIn("Traceback", err)

    def test_a_failed_swap_leaves_the_live_file_and_restarts_the_api(self):
        self.host.fail_swap = True
        code, _, err = self.invoke("replace", str(self.variant(marker=True)), "--execute")
        self.assertEqual(code, 1)
        self.assertIn("ROLLED_BACK", err)
        self.assertEqual(self.host.live_sha(), self.original)
        self.assertTrue(self.host.running)
        self.assertEqual([p.name for p in self.state.iterdir()], [snap.DATABASE_NAME])

    def test_failure_to_put_the_file_back_is_reported_as_needing_manual_recovery(self):
        snapshot = self.variant(marker=True)
        self.host.unready.add(snap.sha256_file(snapshot / snap.DATABASE_NAME))
        self.host.fail_undo = True
        code, _, err = self.invoke("replace", str(snapshot), "--execute")
        self.assertEqual(code, 2)
        self.assertIn("ROLLBACK_FAILED", err)
        self.assertIn("flareledger-pre-update-", err)
        self.assertIn("flareledger.sqlite3.replaced-", err)

    def test_manual_rollback_restores_the_newest_kept_file(self):
        snapshot = self.variant(marker=True)
        self.assertEqual(self.invoke("replace", str(snapshot), "--execute")[0], 0)
        code, out, err = self.invoke("rollback", "--execute")
        self.assertEqual(code, 0, err)
        self.assertIn("ROLLBACK_OK", out)
        self.assertEqual(self.host.live_sha(), self.original)
        self.assertTrue(self.host.running)

    def test_rollback_without_a_kept_file_is_refused(self):
        code, _, err = self.invoke("rollback", "--execute")
        self.assertEqual(code, 1)
        self.assertIn("No kept previous database file", err)
        self.assertNotIn("stop", self.host.words())

    def test_the_live_project_needs_a_public_url_to_execute(self):
        with self.assertRaises(SystemExit) as stop, contextlib.redirect_stderr(io.StringIO()):
            replace.main(["replace", str(self.variant(marker=True)), "--execute"])
        self.assertEqual(stop.exception.code, 2)

    def test_disaster_recovery_handles_missing_corrupt_and_stopped_api(self):
        snapshot = self.variant(marker=True)
        for mode in ("missing", "corrupt", "stopped"):
            with self.subTest(mode=mode):
                database = self.state / snap.DATABASE_NAME
                fixtures.make_database(database) if not database.exists() else None
                old = database.read_bytes()
                if mode == "missing":
                    database.unlink()
                    (self.state / (snap.DATABASE_NAME + "-wal")).write_bytes(b"orphaned-wal")
                elif mode == "corrupt":
                    database.write_bytes(b"damaged database")
                else:
                    self.host.running = False
                with mock.patch.object(deploy_tools, "public_ready", lambda base: (
                    deploy_tools.Check("public ready", self.host.running and self.host.facts().get("ready") == "ready"),
                    self.host.facts().get("corpus_version") if self.host.running else None,
                )):
                    code, out, err = self.invoke("recover", str(snapshot), "--execute", "--public-url", "https://test.invalid")
                self.assertEqual(code, 0, err)
                self.assertIn("RECOVER_OK", out)
                self.assertTrue(self.host.running)
                self.assertEqual(self.host.live_sha(), snap.sha256_file(snapshot / snap.DATABASE_NAME))
                self.assertFalse(any(c[0] == sys.executable for c in self.host.log[-8:]))
                if mode == "corrupt":
                    self.assertTrue(any(p.read_bytes() == b"damaged database" for p in self.state.glob("*.replaced-*")))
                if mode == "missing":
                    self.assertFalse((self.state / (snap.DATABASE_NAME + "-wal")).exists())
                    self.assertTrue(any(p.read_bytes() == b"orphaned-wal" for p in self.state.glob("*.replaced-*-wal")))
                database.write_bytes(old)

    def test_normal_replace_still_refuses_unavailable_database(self):
        (self.state / snap.DATABASE_NAME).unlink()
        code, _, err = self.invoke("replace", str(self.variant(marker=True)), "--execute")
        self.assertEqual(code, 1)
        self.assertIn("explicit recover", err)
        self.assertNotIn("stop", self.host.words())

    def test_public_url_success_and_failure_use_the_actual_helper(self):
        snapshot = self.variant(marker=True)
        version = snap.verify_snapshot(snapshot)["corpus"]["corpus_version"]
        with mock.patch.object(deploy_tools, "public_ready", return_value=(deploy_tools.Check("ready", True), version)) as public:
            code, _, err = self.invoke("replace", str(snapshot), "--execute", "--public-url", "https://test.invalid")
        self.assertEqual(code, 0, err)
        public.assert_called_with("https://test.invalid")
        with mock.patch.object(deploy_tools, "public_ready", return_value=(deploy_tools.Check("ready", True), version)):
            self.assertEqual(self.invoke("rollback", "--execute", "--public-url", "https://test.invalid")[0], 0)
        with mock.patch.object(deploy_tools, "public_ready", return_value=(deploy_tools.Check("ready", False), None)):
            code, _, err = self.invoke("replace", str(snapshot), "--execute", "--public-url", "https://test.invalid")
        self.assertEqual(code, 2)
        self.assertIn("ROLLBACK_FAILED", err)

    def test_manual_rollback_helper_failure_restarts_last_working_api(self):
        snapshot = self.variant(marker=True)
        self.assertEqual(self.invoke("replace", str(snapshot), "--execute")[0], 0)
        current = self.host.live_sha()
        self.host.fail_undo = True
        code, _, err = self.invoke("rollback", "--execute")
        self.assertEqual(code, 1, err)
        self.assertIn("ROLLED_BACK", err)
        self.assertTrue(self.host.running)
        self.assertEqual(self.host.live_sha(), current)

    def test_manual_rollback_bad_database_returns_to_current_working_file(self):
        snapshot = self.variant(marker=True)
        self.assertEqual(self.invoke("replace", str(snapshot), "--execute")[0], 0)
        current = self.host.live_sha()
        self.host.unready.add(self.original)
        code, _, err = self.invoke("rollback", "--execute")
        self.assertEqual(code, 1, err)
        self.assertIn("ROLLED_BACK", err)
        self.assertTrue(self.host.running)
        self.assertEqual(self.host.live_sha(), current)

    def test_retagged_image_and_missing_volume_are_refused_before_stop(self):
        snapshot = self.variant(marker=True)
        for kind in ("image", "volume"):
            def changed(command, env=None, cwd=None, pass_fds=()):
                if command[:3] == ["docker", kind, "inspect"]:
                    return "different-object\n"
                return self.host(command, env, cwd, pass_fds)
            with mock.patch.object(replace, "run", changed):
                code, _, _ = self.invoke("recover", str(snapshot), "--execute")
            self.assertEqual(code, 1)
            self.assertNotIn("stop", self.host.words())

    def test_partial_undo_failure_returns_the_displaced_working_file(self):
        snapshot = self.variant(marker=True)
        self.assertEqual(self.invoke("replace", str(snapshot), "--execute")[0], 0)
        current = self.host.live_sha()
        failed = [False]
        def partial(command, env=None, cwd=None, pass_fds=()):
            if command[:3] == ["docker", "run", "--rm"] and replace.UNDO in command and not failed[0]:
                failed[0] = True
                command = list(command)
                index = command.index(replace.UNDO)
                command[index] = replace.UNDO.replace("os.rename(saved, live)", "raise RuntimeError('failed after moving current file')")
            return self.host(command, env, cwd, pass_fds)
        with mock.patch.object(replace, "run", partial):
            code, _, err = self.invoke("rollback", "--execute")
        self.assertEqual(code, 1, err)
        self.assertTrue(self.host.running)
        self.assertEqual(self.host.live_sha(), current)

    def test_failed_restart_during_manual_rollback_reports_recovery_details(self):
        self.assertEqual(self.invoke("replace", str(self.variant(marker=True)), "--execute")[0], 0)
        self.host.fail_start = True
        code, _, err = self.invoke("rollback", "--execute")
        self.assertEqual(code, 2)
        self.assertIn("ROLLBACK_FAILED", err)
        self.assertIn("volume vol1", err)
        self.assertNotIn("REPLACE_REFUSED", err)


class RehearsalGuardTests(unittest.TestCase):
    def test_the_rehearsal_refuses_project_names_that_could_hit_the_live_stack(self):
        for name in ("flareledger", "flareledger-restore", "other"):
            with self.assertRaises(SystemExit) as stop, contextlib.redirect_stderr(io.StringIO()):
                rehearse_replace.main(["missing", "--project-dir", ".", "--project", name])
            self.assertEqual(stop.exception.code, 2, name)

    def test_variants_pass_or_fail_verification_as_intended(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = fixtures.make_snapshot(root, "flareledger-daily-20261114T031000Z-aaaaaaaa")
            good = rehearse_replace.make_variant(source, root / "good", marker=True)
            self.assertEqual(snap.verify_snapshot(good)["corpus"]["records"], 3)
            other = rehearse_replace.make_variant(source, root / "other", seed="c" * 64)
            self.assertEqual(snap.verify_snapshot(other)["corpus"]["seed_sha256"], "c" * 64)
            bad = rehearse_replace.make_variant(source, root / "bad", marker=True, tamper=True)
            with self.assertRaises(snap.SnapshotError):
                snap.verify_snapshot(bad)


@unittest.skipUnless(sys.platform == "linux", "Linux host flock")
class ReplacementLockTests(unittest.TestCase):
    def test_replacement_blocks_a_real_scheduled_backup_process(self):
        with tempfile.TemporaryDirectory() as folder:
            with replace.lock(Path(folder)):
                code = "import backup_production as b,sys; sys.exit(b.main(['--dest',sys.argv[1]]))"
                child = subprocess.run([sys.executable, "-c", code, folder],
                                       cwd=Path(__file__).resolve().parent, capture_output=True, text=True, timeout=10)
            self.assertEqual(child.returncode, 1)
            self.assertIn("Another backup, deploy or database operation", child.stderr)

    def test_nested_backup_inherits_replacement_lock_without_unlocking_it(self):
        import operation_lock
        with tempfile.TemporaryDirectory() as folder:
            with replace.lock(Path(folder)) as handle:
                code = "import backup_production as b,sys; from pathlib import Path; b.lock(Path(sys.argv[1]),'flareledger',int(sys.argv[2])).close()"
                child = subprocess.run([sys.executable, "-c", code, folder, str(handle.fileno())],
                                       cwd=Path(__file__).resolve().parent, capture_output=True, text=True,
                                       pass_fds=(handle.fileno(),), timeout=10)
                self.assertEqual(child.returncode, 0, child.stderr)
                with self.assertRaises(OSError):
                    operation_lock.acquire(Path(folder), "flareledger")


if __name__ == "__main__":
    unittest.main()
