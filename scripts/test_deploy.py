"""Test deploy, rollback and monitoring logic without Docker or network access.

Docker and HTTP are replaced by in-memory fakes. Git runs for real against a tiny
temporary repository, so revision resolution, the origin/main rule and checkout
movement are exercised for real. No NASA data is involved.
"""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy_production as deploy  # noqa: E402
import deploy_tools as tools  # noqa: E402
import monitor_production as monitor  # noqa: E402

REAL_RUN = deploy.run
PROBE_DATA = {
    "ready": "ready", "corpus_version": "synthetic", "investigations": 10, "records": 1132,
    "trial_rows": 647, "series": 6, "points": 1844,
}


def git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *arguments],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def make_repo(root: Path) -> tuple[Path, list[str]]:
    """Commits A and B are on origin/main; C is not."""
    app = root / "app"
    app.mkdir()
    git(app, "init", "-q")
    shas = []
    for name in ("a", "b", "c"):
        (app / f"{name}.txt").write_text(name, encoding="utf-8")
        git(app, "add", "-A")
        git(app, "commit", "-q", "-m", name)
        shas.append(git(app, "rev-parse", "HEAD"))
    git(app, "update-ref", "refs/remotes/origin/main", shas[1])
    git(app, "checkout", "-q", "--detach", shas[0])
    return app, shas


class FakeHost:
    """Answers Docker commands; git commands run for real."""

    def __init__(self, shas: list[str]):
        self.shas = shas
        self.running = shas[0]
        self.images = {f"flareledger-api:{shas[0][:7]}"}
        self.log: list[list[str]] = []
        self.up_fails_for: str | None = None
        self.build_tags: list[str] = []
        self.stopped = False
        self.probe_fails_for: str | None = None
        self.backup_fails = False

    def words(self) -> list[str]:
        return [word for command in self.log for word in command]

    def __call__(self, command, env=None, cwd=None, pass_fds=()):
        if command[0] == "git":
            return REAL_RUN(command, env, cwd)
        self.log.append(list(command))
        if command[:2] == ["docker", "ps"]:
            return "" if self.stopped and "--all" not in command else "cid1\n"
        if command[:2] == ["docker", "inspect"]:
            return f"flareledger-api:{self.running[:7]}\n" if "Config.Image" in command[-1] else "healthy\n"
        if command[:2] == ["docker", "exec"]:
            if self.stopped or self.running == self.probe_fails_for:
                raise deploy.DeployError("current API unavailable")
            return json.dumps(PROBE_DATA) + "\n"
        if command[:3] == ["docker", "image", "inspect"]:
            if command[3] not in self.images:
                raise deploy.DeployError("no such image")
            return "[]"
        if command[:2] == ["docker", "compose"]:
            if "build" in command:
                self.build_tags.append(env["IMAGE_TAG"])
                self.images.add(f"flareledger-api:{env['IMAGE_TAG']}")
            if "up" in command:
                target = next(sha for sha in self.shas if sha.startswith(env["IMAGE_TAG"]))
                if self.up_fails_for and target == self.up_fails_for:
                    raise deploy.DeployError("compose up failed")
                self.running = target
                self.stopped = False
            return ""
        if command[0] == sys.executable:  # the backup script
            if self.backup_fails:
                raise deploy.DeployError("SQLite backup unavailable")
            return "BACKUP_OK | kind=pre-update | snapshot=flareledger-pre-update-20261114T000000Z-aaaaaaaa | kept<=7\n"
        raise AssertionError(f"unexpected command {command}")


class DeployTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.app, self.shas = make_repo(root)
        self.snapshots = root / "snapshots"
        self.snapshots.mkdir()
        self.host = FakeHost(self.shas)
        self.bad_when_running: str | None = None
        self.public_ok = True
        patches = [
            mock.patch.object(deploy, "run", self.host),
            mock.patch.object(deploy, "lock", lambda directory, project="flareledger": contextlib.nullcontext()),
            mock.patch.object(deploy.time, "sleep", lambda seconds: None),
            mock.patch.object(tools, "public_ready", self.public_ready),
            mock.patch.object(tools, "parallel_reads", self.parallel_reads),
            mock.patch.object(tools, "sites_up", lambda sites=tools.SITES: tools.Check("neighbouring sites", True, "all 200")),
            mock.patch.object(tools, "check_tls", lambda base=tools.PUBLIC_API: tools.Check("tls certificate", True, "60 days")),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def public_ready(self, base=tools.PUBLIC_API):
        if not self.public_ok:
            return tools.Check("public ready", False, "HTTP 502"), None
        return tools.Check("public ready", True, "ok"), "synthetic"

    def parallel_reads(self, base=tools.PUBLIC_API, rounds=6, workers=8):
        if self.bad_when_running and self.host.running == self.bad_when_running:
            return tools.Check("parallel catalog reads", False, "3 unexpected: /api/meta=503")
        return tools.Check("parallel catalog reads", True, "all as expected")

    def invoke(self, *arguments: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = deploy.main([*arguments, "--app-dir", str(self.app), "--snapshots", str(self.snapshots)])
        return code, out.getvalue(), err.getvalue()

    def head(self) -> str:
        return git(self.app, "rev-parse", "HEAD")

    def events(self) -> list[str]:
        lines = (self.snapshots / "deploy.log").read_text(encoding="utf-8").splitlines()
        return [json.loads(line)["event"] for line in lines]

    def test_plan_names_the_target_image_and_changes_nothing(self):
        code, out, _ = self.invoke("plan", "--revision", self.shas[1][:7])
        self.assertEqual(code, 0)
        self.assertIn(f"target:  flareledger-api:{self.shas[1][:7]}", out)
        self.assertIn(f"current: flareledger-api:{self.shas[0][:7]}", out)
        self.assertIn("PLAN_ONLY", out)
        self.assertNotIn("up", self.host.words())
        self.assertNotIn("build", self.host.words())
        self.assertEqual(self.head(), self.shas[0])

    def test_deploy_without_execute_is_only_a_plan(self):
        code, out, _ = self.invoke("deploy", "--revision", self.shas[1])
        self.assertEqual(code, 0)
        self.assertIn("PLAN_ONLY", out)
        self.assertNotIn("up", self.host.words())

    def test_revision_outside_origin_main_is_refused(self):
        code, _, err = self.invoke("deploy", "--revision", self.shas[2], "--execute")
        self.assertEqual(code, 1)
        self.assertIn("not part of origin/main", err)
        self.assertNotIn("up", self.host.words())
        self.assertEqual(self.head(), self.shas[0])

    def test_unknown_or_non_commit_revision_is_refused(self):
        for revision in ("deadbeef", "latest", "main"):
            code, _, err = self.invoke("deploy", "--revision", revision, "--execute")
            self.assertEqual(code, 1, revision)
            self.assertIn("DEPLOY_REFUSED", err)

    def test_successful_deploy_backs_up_first_then_builds_then_restarts(self):
        code, out, err = self.invoke("deploy", "--revision", self.shas[1], "--execute")
        self.assertEqual(code, 0, err)
        self.assertIn("DEPLOY_OK", out)
        kinds = [("backup" if c[0] == sys.executable else "build" if "build" in c else "up" if "up" in c else "")
                 for c in self.host.log]
        kinds = [k for k in kinds if k]
        self.assertEqual(kinds, ["backup", "build", "up"])
        self.assertEqual(self.host.running, self.shas[1])
        self.assertEqual(self.head(), self.shas[1])
        self.assertEqual(self.events(), ["started", "ok"])
        self.assertEqual(self.host.build_tags, [self.shas[1][:7]])

    def test_failed_post_check_returns_to_the_previous_image_without_rebuilding(self):
        self.bad_when_running = self.shas[1]
        code, out, err = self.invoke("deploy", "--revision", self.shas[1], "--execute")
        self.assertEqual(code, 1)
        self.assertIn("ROLLED_BACK", err)
        self.assertEqual(self.host.running, self.shas[0])
        self.assertEqual(self.head(), self.shas[0])
        self.assertEqual(sum(1 for c in self.host.log if "build" in c), 1)
        self.assertEqual(self.events(), ["started", "rolled_back"])

    def test_failed_restart_returns_to_the_previous_image(self):
        self.host.up_fails_for = self.shas[1]
        code, _, err = self.invoke("deploy", "--revision", self.shas[1], "--execute")
        self.assertEqual(code, 1)
        self.assertIn("ROLLED_BACK", err)
        self.assertEqual(self.host.running, self.shas[0])
        self.assertEqual(self.head(), self.shas[0])

    def test_failure_of_the_return_is_reported_as_needing_manual_recovery(self):
        self.bad_when_running = self.shas[1]
        original_switch = deploy.switch
        calls = []

        def switch(ctx, revision, build):
            calls.append(revision)
            if len(calls) == 2:
                raise deploy.DeployError("cannot restart")
            return original_switch(ctx, revision, build)

        with mock.patch.object(deploy, "switch", switch):
            code, _, err = self.invoke("deploy", "--revision", self.shas[1], "--execute")
        self.assertEqual(code, 2)
        self.assertIn("ROLLBACK_FAILED", err)
        self.assertIn("flareledger-pre-update-", err)
        self.assertEqual(self.events(), ["started", "rollback_failed"])

    def test_pre_check_failure_changes_nothing_and_takes_no_backup(self):
        self.public_ok = False
        code, _, err = self.invoke("deploy", "--revision", self.shas[1], "--execute")
        self.assertEqual(code, 1)
        self.assertIn("pre-checks failed", err)
        self.assertNotIn("up", self.host.words())
        self.assertFalse(any(c[0] == sys.executable for c in self.host.log))
        self.assertEqual(self.events(), ["refused"])

    def test_uncommitted_changes_in_the_checkout_are_refused(self):
        (self.app / "a.txt").write_text("edited", encoding="utf-8")
        code, _, err = self.invoke("deploy", "--revision", self.shas[1], "--execute")
        self.assertEqual(code, 1)
        self.assertIn("uncommitted changes", err)
        self.assertNotIn("up", self.host.words())

    def test_rollback_never_builds_and_needs_the_image(self):
        code, _, err = self.invoke("rollback", "--revision", self.shas[1], "--execute")
        self.assertEqual(code, 1)
        self.assertIn("never builds", err)
        self.assertNotIn("build", self.host.words())

    def test_rollback_to_an_existing_image_succeeds(self):
        self.host.running = self.shas[1]
        self.host.images.add(f"flareledger-api:{self.shas[1][:7]}")
        git(self.app, "checkout", "-q", "--detach", self.shas[1])
        code, out, err = self.invoke("rollback", "--revision", self.shas[0], "--execute")
        self.assertEqual(code, 0, err)
        self.assertIn("ROLLBACK_OK", out)
        self.assertEqual(self.host.running, self.shas[0])
        self.assertNotIn("build", self.host.words())

    def test_deploying_the_running_revision_does_nothing(self):
        code, out, _ = self.invoke("deploy", "--revision", self.shas[0], "--execute")
        self.assertEqual(code, 0)
        self.assertIn("NOTHING_TO_DO", out)
        self.assertNotIn("up", self.host.words())

    def test_recovery_rollback_handles_unavailable_or_stopped_api_and_failed_backup(self):
        for stopped in (False, True):
            self.host.running = self.shas[0]
            self.host.stopped = stopped
            self.host.probe_fails_for = self.shas[0]
            self.host.backup_fails = True
            self.host.images.add(f"flareledger-api:{self.shas[1][:7]}")
            with mock.patch.object(tools, "public_ready", lambda base: (
                tools.Check("public ready", self.host.running == self.shas[1], ""),
                "synthetic" if self.host.running == self.shas[1] else None,
            )):
                code, out, err = self.invoke("rollback", "--revision", self.shas[1], "--execute",
                                             "--recover", "--expected-corpus-version", "synthetic")
            self.assertEqual(code, 0, err)
            self.assertIn("ROLLBACK_OK", out)
            self.assertEqual(self.host.running, self.shas[1])
            self.assertNotIn("build", self.host.words())

    def test_recovery_refuses_wrong_expected_corpus_after_restart(self):
        self.host.images.add(f"flareledger-api:{self.shas[1][:7]}")
        self.host.probe_fails_for = self.shas[0]
        code, _, err = self.invoke("rollback", "--revision", self.shas[1], "--execute",
                                    "--recover", "--expected-corpus-version", "wrong")
        self.assertEqual(code, 2)
        self.assertIn("ROLLBACK_FAILED", err)

    def test_recovery_can_restart_the_same_stopped_revision(self):
        self.host.stopped = True
        code, out, err = self.invoke("rollback", "--revision", self.shas[0], "--execute",
                                    "--recover", "--expected-corpus-version", "synthetic")
        self.assertEqual(code, 0, err)
        self.assertIn("ROLLBACK_OK", out)
        self.assertFalse(self.host.stopped)

    def test_recovery_requires_explicit_expected_corpus_and_rollback(self):
        for command in ("deploy", "rollback"):
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                self.invoke(command, "--revision", self.shas[1], "--recover")

    def test_the_tooling_checkout_cannot_be_the_managed_checkout(self):
        with self.assertRaises(SystemExit) as stop, contextlib.redirect_stderr(io.StringIO()):
            deploy.main(["status", "--app-dir", str(deploy.ROOT)])
        self.assertEqual(stop.exception.code, 2)

    def test_status_reports_a_checkout_that_differs_from_the_running_revision(self):
        git(self.app, "checkout", "-q", "--detach", self.shas[1])
        with mock.patch.object(tools, "backup_age", lambda *a, **k: tools.Check("daily backup age", True, "1 h")):
            code, out, _ = self.invoke("status")
        self.assertEqual(code, 0)
        self.assertIn("differs from running", out)


class MonitorTests(unittest.TestCase):
    def test_tls_thresholds(self):
        for days, ok, note in ((60.0, True, ""), (15.0, True, "warning"), (5.0, False, "")):
            with mock.patch.object(tools, "tls_days_left", lambda host, days=days: days):
                check = tools.check_tls("https://example.invalid")
            self.assertEqual(check.ok, ok, days)
            self.assertIn(note, check.detail)

    def test_tls_failure_to_connect_is_a_failed_check(self):
        def broken(host):
            raise OSError("handshake failed")

        with mock.patch.object(tools, "tls_days_left", broken):
            check = tools.check_tls("https://example.invalid")
        self.assertFalse(check.ok)

    def test_backup_age(self):
        with tempfile.TemporaryDirectory() as folder:
            snapshots = Path(folder)
            now = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)
            self.assertFalse(tools.backup_age(snapshots, "daily", now).ok)  # no marker at all
            for age, ok in ((3, True), (25, True), (27, False)):
                created = (now - timedelta(hours=age)).isoformat()
                (snapshots / "last-success-daily.json").write_text(json.dumps({"created_at": created}), encoding="utf-8")
                self.assertEqual(tools.backup_age(snapshots, "daily", now).ok, ok, age)

    def test_unexpected_status_in_parallel_reads_fails(self):
        def fake(url, timeout=15.0):
            return (503, b"{}") if url.endswith("/api/meta") else (404 if "__deploy_check" in url else 200, b"{}")

        with mock.patch.object(tools, "http_get", fake):
            check = tools.parallel_reads("https://x.invalid", rounds=2, workers=2)
        self.assertFalse(check.ok)
        self.assertIn("/api/meta=503", check.detail)

    def test_expected_statuses_pass_parallel_reads(self):
        def fake(url, timeout=15.0):
            return (404 if "__deploy_check" in url else 200, b"{}")

        with mock.patch.object(tools, "http_get", fake):
            self.assertTrue(tools.parallel_reads("https://x.invalid", rounds=2, workers=2).ok)

    def test_public_ready_rejects_non_json_and_not_ready(self):
        for status, body in ((200, b"null"), (200, b"[]"), (502, b"<html>bad gateway</html>"), (503, b'{"error": {"code": "corpus_unavailable"}}'),
                             (200, b'{"status": "starting"}')):
            with mock.patch.object(tools, "http_get", lambda url, timeout=15.0, s=status, b=body: (s, b)):
                check, version = tools.public_ready("https://x.invalid")
            self.assertFalse(check.ok, status)
            self.assertIsNone(version)
        body = b'{"status": "ready", "corpus_version": "v1"}'
        with mock.patch.object(tools, "http_get", lambda url, timeout=15.0: (200, body)):
            check, version = tools.public_ready("https://x.invalid")
        self.assertTrue(check.ok)
        self.assertEqual(version, "v1")

    def test_one_failed_attempt_is_not_reported_but_repeated_failures_are(self):
        good = [tools.Check("public ready", True, "")]
        bad = [tools.Check("public ready", False, "HTTP 502")]
        sleeps = []
        with mock.patch.object(monitor, "collect", side_effect=[bad, good]):
            ok, _, used = monitor.monitor("external", "u", Path("."), 3, 60, sleep=sleeps.append)
        self.assertTrue(ok)
        self.assertEqual((used, sleeps), (2, [60]))
        with mock.patch.object(monitor, "collect", return_value=bad):
            ok, _, used = monitor.monitor("external", "u", Path("."), 3, 60, sleep=sleeps.append)
        self.assertFalse(ok)
        self.assertEqual(used, 3)

    def test_local_mode_adds_backup_and_disk_checks_external_does_not(self):
        with mock.patch.object(tools, "public_ready", lambda base: (tools.Check("public ready", True, ""), "v")), \
                mock.patch.object(tools, "check_tls", lambda base: tools.Check("tls certificate", True, "")), \
                mock.patch.object(tools, "parallel_reads", lambda *a, **k: tools.Check("parallel catalog reads", True, "")), \
                mock.patch.object(tools, "backup_age", lambda *a, **k: tools.Check("daily backup age", True, "")), \
                mock.patch.object(tools, "frontend_checks", lambda *a: [tools.Check("frontend ready", True, "")]):
            external = [c.name for c in monitor.collect("external", "u", Path("."))]
            local = [c.name for c in monitor.collect("local", "u", Path("."))]
        self.assertIn("frontend ready", external)
        self.assertIn("frontend ready", local)
        self.assertNotIn("daily backup age", external)
        self.assertIn("daily backup age", local)
        self.assertIn("disk space", local)

    def test_unhealthy_run_exits_with_one(self):
        out = io.StringIO()
        with mock.patch.object(monitor, "collect", return_value=[tools.Check("public ready", False, "HTTP 502")]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = monitor.main(["--attempts", "2", "--interval", "0"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out.getvalue().strip().splitlines()[-1])["ok"], False)


class FrontendMonitorTests(unittest.TestCase):
    def checks(self, *, shell=True, page_status=200, ready_status=200,
               ready_body=b'{"status":"ready","corpus_version":"v1"}', tls=True):
        calls = []
        def get(url, timeout=15.0):
            calls.append(url)
            if url == "https://web.invalid/":
                return page_status, b'<div id="app"></div><script src="/assets/app.js"></script>' if shell else b'<html>Error page</html>'
            if url == "https://web.invalid/api/health/ready":
                return ready_status, ready_body
            raise AssertionError(url)
        with mock.patch.object(tools, "http_get", get), \
                mock.patch.object(tools, "check_tls", return_value=tools.Check("TLS", tls, "certificate")):
            checks = tools.frontend_checks("https://web.invalid/", "v1")
        self.assertFalse(any("/ask" in url for url in calls))
        return {c.name: c for c in checks}

    def test_static_page_and_real_rewrite_are_both_required(self):
        self.assertTrue(all(c.ok for c in self.checks().values()))
        self.assertFalse(self.checks(shell=False)["frontend page"].ok)
        self.assertFalse(self.checks(page_status=503)["frontend page"].ok)
        self.assertFalse(self.checks(ready_status=502)["frontend ready"].ok)

    def test_spa_fallback_on_api_and_wrong_corpus_fail(self):
        self.assertFalse(self.checks(ready_body=b'<div id="app"></div>')["frontend ready"].ok)
        wrong = b'{"status":"ready","corpus_version":"old"}'
        self.assertFalse(self.checks(ready_body=wrong)["frontend corpus version"].ok)

    def test_frontend_certificate_failure_fails_the_run(self):
        self.assertFalse(self.checks(tls=False)["frontend TLS"].ok)

    def test_web_url_option_reaches_the_retried_check(self):
        good = [tools.Check("frontend ready", True)]
        with mock.patch.object(monitor, "collect", return_value=good) as collect, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(monitor.main(["--web-url", "https://preview.invalid", "--attempts", "1"]), 0)
        self.assertEqual(collect.call_args.args[3], "https://preview.invalid")


if __name__ == "__main__":
    unittest.main()
