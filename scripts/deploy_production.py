"""Deploy or roll back the FlareLedger API on the VPS to an explicit commit.

Subcommands: status, plan, deploy, rollback. deploy and rollback only describe what
they would do unless --execute is given. The target is always an explicit commit
that is part of origin/main; the script names the image it will run before it acts.

deploy: pre-checks, pre-update backup, build, restart, post-checks, and an automatic
return to the previous image if a post-check fails. rollback: the same without a
build (the image must already exist). Neither changes the corpus or the database
file; if a release changes the database schema, restore the pre-update snapshot
(docs/BACKUP_RECOVERY.md) before returning to an older revision.

Run it from the tooling checkout, not from the application checkout it manages.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import deploy_tools as tools
import snapshot_tools as snap
import operation_lock
from restore_snapshot import PROBE

ROOT = Path(__file__).resolve().parents[1]
BACKUP_SCRIPT = ROOT / "scripts" / "backup_production.py"
COUNT_KEYS = ("corpus_version", "investigations", "records", "trial_rows", "series", "points")


class DeployError(Exception):
    pass


@dataclass
class Context:
    app_dir: Path
    project: str
    snapshots: Path
    repo: Path
    public: str
    sites: tuple[str, ...]
    recovery: bool = False
    expected_corpus: str | None = None


def run(command: list[str], env: dict | None = None, cwd: Path | None = None, pass_fds: tuple[int, ...] = ()) -> str:
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=False, env={**os.environ, **(env or {})}, cwd=cwd,
            **({"pass_fds": pass_fds} if pass_fds else {}),
        )
    except OSError as error:
        raise DeployError(f"Cannot run {command[0]}: {error}") from error
    if result.returncode != 0:
        raise DeployError(f"{' '.join(command[:4])} failed: {(result.stderr or result.stdout).strip()[-400:]}")
    return result.stdout


@contextmanager
def lock(directory: Path, project: str = "flareledger"):
    with operation_lock.acquire(directory, project) as handle:
        yield handle


def compose(ctx: Context, *arguments: str) -> list[str]:
    return [
        "docker", "compose", "--project-name", ctx.project,
        "--file", str(ctx.app_dir / "compose.yaml"), "--file", str(ctx.app_dir / "compose.prod.yaml"),
        *arguments,
    ]


def compose_env(tag: str) -> dict:
    return {"IMAGE_TAG": tag, "APP_ENV": "production", "LLM_ENABLED": "false"}


def container(ctx: Context) -> str:
    ids = run(
        [
            "docker", "ps", *(["--all"] if ctx.recovery else []), "--quiet",
            "--filter", f"label=com.docker.compose.project={ctx.project}",
            "--filter", "label=com.docker.compose.service=api",
        ]
    ).split()
    if len(ids) != 1:
        raise DeployError(f"Expected one running api container in project {ctx.project}, found {len(ids)}")
    return ids[0]


def running(ctx: Context) -> tuple[str, str, str]:
    """(container id, image reference, full revision resolved from the image tag)."""
    cid = container(ctx)
    reference = run(["docker", "inspect", cid, "--format", "{{.Config.Image}}"]).strip()
    revision = snap.resolve_revision(ctx.app_dir, snap.release_tag(reference))
    return cid, reference, revision


def probe(cid: str) -> dict:
    output = run(["docker", "exec", cid, "python", "-c", PROBE])
    return json.loads(output.strip().splitlines()[-1])


def wait_healthy(ctx: Context, attempts: int = 45) -> str:
    for _ in range(attempts):
        try:
            cid = container(ctx)
            if run(["docker", "inspect", cid, "--format", "{{.State.Health.Status}}"]).strip() == "healthy":
                return cid
        except DeployError:
            pass
        time.sleep(2)
    raise DeployError("The API did not become healthy within 90 seconds")


def resolve_target(ctx: Context, revision: str) -> str:
    try:
        run(["git", "-C", str(ctx.app_dir), "fetch", "--quiet", "origin"])
    except DeployError as error:
        print(f"NOTE: git fetch failed, using local objects only ({error})", file=sys.stderr)
    try:
        full = snap.resolve_revision(ctx.app_dir, revision)
    except snap.SnapshotError as error:
        raise DeployError(
            f"{revision!r} is not a known commit in {ctx.app_dir} (use a commit SHA that is on origin/main): {error}"
        ) from error
    try:
        run(["git", "-C", str(ctx.app_dir), "merge-base", "--is-ancestor", full, "origin/main"])
    except DeployError as error:
        raise DeployError(f"{full[:12]} is not part of origin/main; only reviewed commits can be deployed") from error
    return full


def require_clean_checkout(ctx: Context) -> None:
    if run(["git", "-C", str(ctx.app_dir), "status", "--porcelain"]).strip():
        raise DeployError(f"{ctx.app_dir} has uncommitted changes; refusing to move it")


def image_exists(reference: str) -> bool:
    try:
        run(["docker", "image", "inspect", reference])
    except DeployError:
        return False
    return True


def switch(ctx: Context, revision: str, build: bool) -> str:
    tag, reference = revision[:7], f"flareledger-api:{revision[:7]}"
    run(["git", "-C", str(ctx.app_dir), "checkout", "--quiet", "--detach", revision])
    if not image_exists(reference):
        if not build:
            raise DeployError(f"Image {reference} is missing and rollback never builds")
        run(compose(ctx, "build", "api"), env=compose_env(tag), cwd=ctx.app_dir)
    run(compose(ctx, "up", "-d", "--no-deps", "api"), env=compose_env(tag), cwd=ctx.app_dir)
    return wait_healthy(ctx)


def pre_checks(ctx: Context) -> tuple[list[tools.Check], dict]:
    cid = container(ctx)
    if ctx.recovery:
        # Recovery is explicit: current HTTP/SQLite health is not a precondition.
        # Read-only probes may still supply useful data-preservation checks.
        try:
            baseline = probe(cid)
        except (DeployError, ValueError, IndexError):
            baseline = {}
        if baseline.get("ready") != "ready" or baseline.get("corpus_version") != ctx.expected_corpus:
            baseline = {"corpus_version": ctx.expected_corpus}
        return [tools.check_tls(ctx.public), tools.sites_up(ctx.sites)], baseline
    baseline = probe(cid)
    checks = [tools.Check("local ready", baseline.get("ready") == "ready", f"corpus {str(baseline.get('corpus_version'))[:24]}")]
    public, version = tools.public_ready(ctx.public)
    checks += [public, tools.check_tls(ctx.public), tools.sites_up(ctx.sites)]
    if public.ok and version != baseline.get("corpus_version"):
        checks.append(tools.Check("public matches local", False, "corpus versions differ"))
    return checks, baseline


def post_checks(ctx: Context, baseline: dict, allow_corpus_change: bool) -> list[tools.Check]:
    cid = container(ctx)
    now = probe(cid)
    if allow_corpus_change:
        same = tools.Check("data unchanged", now.get("ready") == "ready", "corpus change allowed; ready only")
    else:
        diff = [key for key in COUNT_KEYS if key in baseline and now.get(key) != baseline.get(key)]
        same = tools.Check("data unchanged", now.get("ready") == "ready" and not diff, "all counts and corpus version match" if not diff else f"differs: {', '.join(diff)}")
    public, version = tools.public_ready(ctx.public)
    agrees = tools.Check("public matches local", public.ok and version == now.get("corpus_version"), "corpus versions must match")
    return [same, public, agrees, tools.parallel_reads(ctx.public), tools.sites_up(ctx.sites), tools.check_tls(ctx.public)]


def backup_before(ctx: Context, handle=None) -> str:
    fd = handle.fileno() if handle is not None else None
    output = run(
        [
            sys.executable, str(BACKUP_SCRIPT), "--dest", str(ctx.snapshots), "--kind", "pre-update",
            "--repo", str(ctx.repo), "--project", ctx.project,
            *(["--lock-fd", str(fd)] if fd is not None else []),
        ], pass_fds=(fd,) if fd is not None else (),
    )
    for part in output.split("|"):
        if part.strip().startswith("snapshot="):
            return part.strip().split("=", 1)[1]
    raise DeployError("The pre-update backup did not report a snapshot")


def record(ctx: Context, entry: dict) -> None:
    entry = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), **entry}
    with (ctx.snapshots / "deploy.log").open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def describe(ctx: Context, action: str, revision: str, planning: bool) -> tuple[str, str, str, bool]:
    cid, current_ref, current_revision = running(ctx)
    target = resolve_target(ctx, revision)
    reference = f"flareledger-api:{target[:7]}"
    present = image_exists(reference)
    head = run(["git", "-C", str(ctx.app_dir), "rev-parse", "HEAD"]).strip()
    print(f"action:  {'plan (deploy builds a missing image; rollback needs it present)' if planning else action}")
    print(f"current: {current_ref}  revision {current_revision}")
    print(f"target:  {reference}  revision {target}  (image {'present' if present else 'missing, deploy would build it'})")
    if head != current_revision:
        print(f"WARNING: checkout HEAD {head[:12]} differs from the running revision {current_revision[:12]}")
    return current_revision, target, reference, present


def perform(
    ctx: Context, action: str, revision: str, execute: bool, allow_corpus_change: bool, planning: bool = False
) -> int:
    current, target, reference, present = describe(ctx, action, revision, planning)
    if action == "rollback" and not present:
        print(f"REFUSED | {reference} is not present and rollback never builds", file=sys.stderr)
        return 1
    if current == target and not ctx.recovery:
        print("NOTHING_TO_DO | the target revision is already running")
        return 0
    if not execute:
        print("PLAN_ONLY | add --execute to run the steps: pre-checks, pre-update backup, "
              + ("build, " if action == "deploy" and not present else "")
              + "restart, post-checks, automatic return to the previous image on failure")
        return 0
    with lock(ctx.snapshots, ctx.project) as handle:
        # Another operation may have completed between the plan and lock acquisition.
        _, _, current = running(ctx)
        require_clean_checkout(ctx)
        checks, baseline = pre_checks(ctx)
        print("pre-checks:\n" + tools.render(checks))
        if not all(check.ok for check in checks):
            record(ctx, {"event": "refused", "action": action, "target": target})
            print("REFUSED | pre-checks failed; nothing was changed", file=sys.stderr)
            return 1
        try:
            snapshot = backup_before(ctx, handle)
        except DeployError as error:
            if not ctx.recovery:
                raise
            snapshot = "unavailable-current-state-left-in-volume"
            print(f"WARNING: recovery backup unavailable; no database replacement is performed: {error}", file=sys.stderr)
        print(f"pre-update backup: {snapshot}")
        record(ctx, {"event": "started", "action": action, "from": current, "to": target, "backup": snapshot})
        failure = None
        try:
            switch(ctx, target, build=action == "deploy")
            results = post_checks(ctx, baseline, allow_corpus_change)
            print("post-checks:\n" + tools.render(results))
            if not all(check.ok for check in results):
                failure = "post-checks failed"
        except (DeployError, snap.SnapshotError, ValueError, KeyError) as error:
            failure = str(error)
        if failure is None:
            record(ctx, {"event": "ok", "action": action, "from": current, "to": target, "backup": snapshot})
            print(f"{action.upper()}_OK | now running {reference} | backup {snapshot}")
            return 0
        print(f"FAILED | {failure}; returning to {current[:12]}", file=sys.stderr)
        try:
            switch(ctx, current, build=False)
            results = post_checks(ctx, baseline, allow_corpus_change=False)
            print("post-checks after return:\n" + tools.render(results))
            if all(check.ok for check in results):
                record(ctx, {"event": "rolled_back", "action": action, "to": target, "failure": failure})
                print(f"ROLLED_BACK | running {current[:12]} again; the release failed: {failure}", file=sys.stderr)
                return 1
        except (DeployError, snap.SnapshotError, ValueError, KeyError) as error:
            failure += f"; return failed: {error}"
        record(ctx, {"event": "rollback_failed", "action": action, "failure": failure, "backup": snapshot})
        print(f"ROLLBACK_FAILED | manual recovery needed; pre-update backup {snapshot}. {failure}", file=sys.stderr)
        return 2


def status(ctx: Context) -> int:
    cid, reference, revision = running(ctx)
    head = run(["git", "-C", str(ctx.app_dir), "rev-parse", "HEAD"]).strip()
    dirty = bool(run(["git", "-C", str(ctx.app_dir), "status", "--porcelain"]).strip())
    print(f"running: {reference}  revision {revision}")
    print(f"checkout {ctx.app_dir}: HEAD {head[:12]}{' (differs from running)' if head != revision else ''}{', UNCOMMITTED CHANGES' if dirty else ''}")
    local = probe(cid)
    public, _ = tools.public_ready(ctx.public)
    checks = [
        tools.Check("local ready", local.get("ready") == "ready", f"{local.get('investigations')} investigations, {local.get('records')} records, {local.get('points')} points"),
        public, tools.check_tls(ctx.public), tools.sites_up(ctx.sites),
        tools.backup_age(ctx.snapshots, "daily"),
    ]
    print(tools.render(checks))
    return 0 if all(check.ok for check in checks) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("status", "plan", "deploy", "rollback"))
    parser.add_argument("--revision", help="commit (full or abbreviated SHA) that is part of origin/main")
    parser.add_argument("--execute", action="store_true", help="actually run deploy or rollback")
    parser.add_argument("--allow-corpus-change", action="store_true", help="release intentionally changes the corpus")
    parser.add_argument("--recover", action="store_true", help="rollback only: recover an unavailable or stopped API")
    parser.add_argument("--expected-corpus-version", help="required with --recover: corpus version the restored API must serve")
    parser.add_argument("--app-dir", type=Path, default=Path.home() / "flareledger")
    parser.add_argument("--project", default="flareledger")
    parser.add_argument("--snapshots", type=Path, default=Path("/var/backups/flareledger/snapshots"))
    parser.add_argument("--repo", type=Path, default=ROOT, help="tooling checkout used for the backup script")
    parser.add_argument("--public-url", default=tools.PUBLIC_API)
    parser.add_argument("--site", action="append", dest="sites", help="neighbouring site that must stay up (repeatable)")
    args = parser.parse_args(argv)
    if args.command != "status" and not args.revision:
        parser.error(f"{args.command} needs --revision")
    if args.recover and (args.command != "rollback" or not args.expected_corpus_version or args.allow_corpus_change):
        parser.error("--recover requires rollback and --expected-corpus-version; corpus changes are not allowed")
    if args.app_dir.resolve() == ROOT:
        parser.error("--app-dir must not be the tooling checkout")
    ctx = Context(
        args.app_dir.resolve(), args.project, args.snapshots, args.repo.resolve(),
        args.public_url, tuple(args.sites) if args.sites else tools.SITES,
        args.recover, args.expected_corpus_version,
    )
    try:
        if args.command == "status":
            return status(ctx)
        action = "deploy" if args.command == "plan" else args.command
        return perform(
            ctx, action, args.revision, args.execute and args.command != "plan", args.allow_corpus_change,
            planning=args.command == "plan",
        )
    except (DeployError, snap.SnapshotError, OSError) as error:
        print(f"DEPLOY_REFUSED | {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
