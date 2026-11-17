"""Exercise the rehearsal wrapper and real restore CLI with a labelled fake Docker.

Snapshot verification runs for real; only Docker/process execution is substituted.
Resource maps expose accidental deletion/adoption after refusal and partial failure.
"""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rehearse_replace as rehearsal
import restore_snapshot as restore
from test_snapshots import make_snapshot

PROJECT = "flareledger-restore-rehearsal-ownership"


class Docker:
    def __init__(self, stage, existing=None):
        self.stage = stage
        self.resources = {kind: {} for kind in ("container", "volume", "network")}
        if existing:
            self.resources[existing]["saved-resource"] = "another-run"
            if existing == "volume":
                self.resources[existing][PROJECT + "_app_state"] = "another-run"
        self.calls = []
        self.removed = []
        self.owner = None

    def __call__(self, command, env=None, cwd=None):
        self.calls.append(list(command))
        if "down" in command or "stop" in command:
            raise AssertionError("broad cleanup must never run")
        if command[:3] == ["docker", "image", "inspect"]:
            return "[]"
        if command[:2] == ["docker", "compose"]:
            if "create" in command:
                files = [command[index + 1] for index, word in enumerate(command) if word == "--file"]
                file = files[-1]
                self.owner = json.loads(Path(file).read_text())["volumes"]["app_state"]["labels"][restore.OWNER_LABEL]
                self.resources["volume"][PROJECT + "_app_state"] = self.owner
                self.resources["network"]["new-network"] = self.owner
                if self.stage == "partial":
                    # Unowned orphans appearing after preflight must survive too.
                    self.resources["volume"]["foreign-orphan"] = "another-run"
                    raise restore.RestoreError("compose create partially failed")
                self.resources["container"]["new-container"] = self.owner
                if self.stage == "wrong-owner":
                    self.resources["volume"][PROJECT + "_app_state"] = "another-run"
                return ""
            if "ps" in command:
                return "healthy"
            if "exec" in command:
                return json.dumps({"ready": "ready", "corpus_version": "synthetic-test",
                                   "investigations": 2, "records": 3, "trial_rows": 2, "series": 1, "points": 3})
            return ""
        if command[:3] == ["docker", "run", "--rm"]:
            return ""
        if command[:2] == ["docker", "exec"]:
            raise restore.RestoreError("injected later rehearsal failure")
        if command[:2] == ["docker", "ps"] or (len(command) > 2 and command[2] == "ls"):
            kind = "container" if command[1] == "ps" else command[1]
            ownership = next((word.split("=", 2)[2] for word in command
                              if word.startswith("label=" + restore.OWNER_LABEL + "=")), None)
            return "\n".join(name for name, owner in self.resources[kind].items()
                             if ownership is None or owner == ownership)
        if len(command) > 2 and command[2] == "inspect":
            kind, name = command[1], command[3]
            if name not in self.resources[kind]:
                raise restore.RestoreError("not found")
            return self.resources[kind][name] if "--format" in command else "[]"
        if len(command) > 2 and command[2] == "rm":
            kind, name = command[1], command[-1]
            if self.resources[kind].pop(name) != self.owner:
                raise AssertionError("attempt to delete an unowned resource")
            self.removed.append((kind, name))
            return ""
        raise AssertionError(command)


class RehearsalCleanupTests(unittest.TestCase):
    def invoke(self, docker, keep=False):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            snapshot = make_snapshot(root, "flareledger-daily-20261114T031000Z-aaaaaaaa")
            source = root / "app"
            source.mkdir()
            (source / "compose.yaml").write_text("services: {}\n")
            def shell(command):
                out, err = io.StringIO(), io.StringIO()
                if command[0] == sys.executable:
                    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                        code = restore.main(command[2:])
                    return code, out.getvalue(), err.getvalue()
                try:
                    return 0, docker(command), ""
                except restore.RestoreError as error:
                    return 1, "", str(error)
            with mock.patch.object(rehearsal, "sh", shell), \
                    mock.patch.object(restore, "run", docker), \
                    mock.patch.object(restore, "check_source", return_value=("b" * 40, "abc1234")), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return rehearsal.main([str(snapshot), "--project-dir", str(source), "--project", PROJECT,
                                       *(["--keep"] if keep else [])])

    def test_existing_project_and_container_are_not_stopped_or_removed(self):
        docker = Docker("refused", existing="container")
        before = {kind: dict(items) for kind, items in docker.resources.items()}
        self.assertEqual(self.invoke(docker), 1)
        self.assertEqual(docker.resources, before)
        self.assertEqual(docker.removed, [])
        self.assertFalse(any("create" in command for command in docker.calls))

    def test_existing_volume_is_not_adopted_written_or_removed(self):
        docker = Docker("refused", existing="volume")
        before = {kind: dict(items) for kind, items in docker.resources.items()}
        self.assertEqual(self.invoke(docker), 1)
        self.assertEqual(docker.resources, before)
        self.assertEqual(docker.removed, [])
        self.assertFalse(any(command[:2] == ["docker", "run"] for command in docker.calls))

    def test_partial_restore_cleans_owned_resources_and_preserves_unowned_orphan(self):
        docker = Docker("partial")
        self.assertEqual(self.invoke(docker), 1)
        self.assertEqual(len(docker.removed), 2)
        self.assertEqual(docker.resources["volume"], {"foreign-orphan": "another-run"})
        self.assertEqual(docker.resources["network"], {})

    def test_successful_restore_then_failed_rehearsal_cleans_its_own_resources(self):
        docker = Docker("later-failure")
        self.assertEqual(self.invoke(docker), 1)
        self.assertEqual(len(docker.removed), 3)
        self.assertFalse(any(docker.resources.values()))

    def test_keep_preserves_even_partially_created_resources(self):
        docker = Docker("partial")
        self.assertEqual(self.invoke(docker, keep=True), 1)
        self.assertEqual(docker.removed, [])
        self.assertTrue(any(docker.resources.values()))

    def test_changed_volume_owner_prevents_database_copy(self):
        docker = Docker("wrong-owner")
        self.assertEqual(self.invoke(docker), 1)
        self.assertFalse(any(command[:2] == ["docker", "run"] for command in docker.calls))
        self.assertEqual(docker.resources["volume"][PROJECT + "_app_state"], "another-run")


if __name__ == "__main__":
    unittest.main()
