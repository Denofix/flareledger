"""Restore a FlareLedger snapshot into a separate Compose project and verify it.

Run this script from any current checkout (it carries the tooling). Give it the
application source of the snapshot's revision with --project-dir, for example a
separate git worktree; that source supplies compose.yaml, the corpus under data/ and,
with --build, the image. The restore project has its own state volume and no
published port or ingress network, so the live API is never touched.

Everything that can be refused is checked before any Docker command runs, and
--cleanup only ever removes resources this run created.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import time
import tempfile
from pathlib import Path

import snapshot_tools as tools

ROOT = Path(__file__).resolve().parents[1]
PROJECT_PREFIX = "flareledger-restore"
OWNER_LABEL = "org.flareledger.restore-owner"

PROBE = """
import json, sys, urllib.request
def get(path):
    with urllib.request.urlopen("http://127.0.0.1:8000" + path, timeout=15) as response:
        return json.load(response)
ready = get("/api/health/ready")
series = get("/api/series?limit=100")
points = sum(len(get("/api/series/" + item["id"])["item"]["points"]) for item in series["items"])
print(json.dumps({
    "ready": ready.get("status"),
    "corpus_version": ready.get("corpus_version"),
    "investigations": get("/api/investigations?limit=1")["total"],
    "records": get("/api/records?limit=1")["total"],
    "trial_rows": get("/api/trials?limit=1")["total"],
    "series": series["total"],
    "points": points,
}))
"""

COPY = (
    "import os, shutil; "
    "shutil.copyfile('/snapshot/flareledger.sqlite3', '/app/state/flareledger.sqlite3'); "
    "os.chown('/app/state/flareledger.sqlite3', 10001, 10001); "
    "os.chmod('/app/state/flareledger.sqlite3', 0o600)"
)


class RestoreError(Exception):
    pass


def run(command: list[str], env: dict | None = None, cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=False, env={**os.environ, **(env or {})}, cwd=cwd
        )
    except OSError as error:
        raise RestoreError(f"Cannot run {command[0]}: {error}") from error
    if result.returncode != 0:
        raise RestoreError(f"{' '.join(command[:4])} failed: {(result.stderr or result.stdout).strip()[-500:]}")
    return result.stdout


def exists(command: list[str]) -> bool:
    """True when the command succeeds. A failing inspect means the resource is absent."""
    try:
        run(command)
    except RestoreError:
        return False
    return True


def cleanup_owned(project: str, owner: str) -> int:
    """Remove only resources labelled with this exact project AND invocation token.

    Do not use compose down: its orphans/volumes may predate this invocation.
    Labels are checked again before each removal; lookup failure preserves resources.
    """
    if not project.startswith(PROJECT_PREFIX) or not re.fullmatch(r"[a-f0-9]{32}", owner):
        raise RestoreError("Invalid rehearsal cleanup ownership")
    filters = ["--filter", f"label=com.docker.compose.project={project}",
               "--filter", f"label={OWNER_LABEL}={owner}"]
    removed = 0
    for kind, listing, labels in (
        ("container", ["docker", "ps", "--all", "--quiet"], ".Config.Labels"),
        ("volume", ["docker", "volume", "ls", "--quiet"], ".Labels"),
        ("network", ["docker", "network", "ls", "--quiet"], ".Labels"),
    ):
        for identifier in run(listing + filters).split():
            found = run(["docker", kind, "inspect", identifier, "--format",
                         '{{index ' + labels + ' "' + OWNER_LABEL + '"}}']).strip()
            if found != owner:
                continue
            run(["docker", kind, "rm", *(["--force"] if kind == "container" else []), identifier])
            removed += 1
    return removed


def check_source(source: Path, manifest: dict, revision: str | None) -> tuple[str, str]:
    """Validate the application source before any Docker command. Returns (revision, release tag)."""
    application = manifest["application"]
    reference = application.get("image_reference") or application.get("image_tag") or ""
    tag = tools.release_tag(reference)
    expected = revision or application.get("revision")
    if not expected:
        raise RestoreError(
            "This snapshot does not record the application revision; pass --revision <full SHA> "
            "after confirming which release was running"
        )
    if not tools.FULL_SHA.match(expected):
        raise RestoreError("The revision must be a full 40-character commit SHA")
    if not (source / "compose.yaml").is_file():
        raise RestoreError(f"{source} has no compose.yaml; pass the application checkout with --project-dir")
    actual = tools.git_head(source)
    if actual != expected:
        raise RestoreError(
            f"--project-dir is at {actual[:12]} but the snapshot was taken from {expected[:12]}. "
            f"Create a matching checkout first: git worktree add <path> {expected}"
        )
    seed = json.loads((source / "data" / "demo" / "seed-reference.json").read_text(encoding="utf-8"))
    if seed.get("sha256") != manifest["corpus"]["seed_sha256"]:
        raise RestoreError("The source corpus does not match the snapshot corpus")
    return expected, tag


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="snapshot directory (for example one pulled from off the VPS)")
    parser.add_argument("--project-dir", type=Path, default=ROOT, help="checkout of the snapshot's application revision")
    parser.add_argument("--revision", help="full commit SHA; only for snapshots that predate the revision field")
    parser.add_argument("--project", help=f"Compose project; must start with {PROJECT_PREFIX} (default: unique name)")
    parser.add_argument("--build", action="store_true", help="build the image from --project-dir when it is missing")
    parser.add_argument("--cleanup", action="store_true", help="remove what this run created afterwards")
    parser.add_argument("--owner-token", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    project = args.project or f"{PROJECT_PREFIX}-{secrets.token_hex(3)}"
    if not project.startswith(PROJECT_PREFIX):
        parser.error(f"--project must start with {PROJECT_PREFIX} so the live project is never touched")
    if args.owner_token and not re.fullmatch(r"[a-f0-9]{32}", args.owner_token):
        parser.error("invalid --owner-token")
    snapshot = args.snapshot.resolve()
    source = args.project_dir.resolve()
    compose = ["docker", "compose", "--project-name", project, "--file", str(source / "compose.yaml")]
    volume = f"{project}_app_state"
    created = False  # cleanup is allowed only after this run created the project
    status = 1
    owner_file: Path | None = None
    try:
        manifest = tools.verify_snapshot(snapshot)
        facts = manifest["corpus"]
        revision, tag = check_source(source, manifest, args.revision)
        reference = f"flareledger-api:{tag}"
        print(f"SNAPSHOT_OK | {snapshot.name} | corpus={facts['corpus_version']} | revision={revision[:12]} | image={reference}")
        # Never adopt, reuse or later delete a project that already exists.
        if exists(["docker", "volume", "inspect", volume]) or run(
            ["docker", "ps", "--all", "--quiet", "--filter", f"label=com.docker.compose.project={project}"]
        ).strip():
            raise RestoreError(f"Compose project {project} already exists; choose another --project or remove it yourself")
        if args.owner_token:
            labels = {OWNER_LABEL: args.owner_token}
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", encoding="utf-8", delete=False) as handle:
                owner_file = Path(handle.name)
                json.dump({"services": {"api": {"labels": labels}},
                           "volumes": {"app_state": {"labels": labels}},
                           "networks": {"app": {"labels": labels}}}, handle)
            compose += ["--file", str(owner_file)]
        env = {"IMAGE_TAG": tag, "APP_ENV": "production", "LLM_ENABLED": "false"}
        if not exists(["docker", "image", "inspect", reference]):
            if not args.build:
                raise RestoreError(f"Image {reference} is missing; build it from the source or pass --build")
            run(compose + ["build", "api"], env=env, cwd=source)
        created = True
        run(compose + ["create", "api"], env=env, cwd=source)
        if args.owner_token:
            found = run(["docker", "volume", "inspect", volume, "--format",
                         '{{index .Labels "' + OWNER_LABEL + '"}}']).strip()
            if found != args.owner_token:
                raise RestoreError("State volume is not owned by this restore; refusing to copy the database")
        run(
            [
                "docker", "run", "--rm", "--read-only", "--network", "none", "--user", "0",
                "--entrypoint", "python",
                "-v", f"{volume}:/app/state", "-v", f"{snapshot}:/snapshot:ro",
                reference, "-c", COPY,
            ]
        )
        run(compose + ["up", "-d", "api"], env=env, cwd=source)
        for _ in range(45):
            health = run(compose + ["ps", "--format", "{{.Health}}", "api"], env=env, cwd=source).strip()
            if health == "healthy":
                break
            time.sleep(2)
        else:
            raise RestoreError("The restored API did not become healthy within 90 seconds")
        output = run(compose + ["exec", "-T", "api", "python", "-c", PROBE], env=env, cwd=source)
        observed = json.loads(output.strip().splitlines()[-1])
        expected = {"ready": "ready", "corpus_version": facts["corpus_version"]} | {
            key: facts[key] for key in ("investigations", "records", "trial_rows", "series", "points")
        }
        for key, value in expected.items():
            marker = "OK " if observed.get(key) == value else "BAD"
            print(f"  {marker} {key}: restored={observed.get(key)} snapshot={value}")
        if observed != expected:
            raise RestoreError("Restored API does not match the verified snapshot")
        print(f"RESTORE_OK | project={project} | volume={volume}")
        status = 0
    except (RestoreError, tools.SnapshotError, OSError, ValueError, KeyError) as error:
        print(f"RESTORE_FAILED | {error}", file=sys.stderr)
    finally:
        if args.cleanup and created:
            try:
                if args.owner_token:
                    cleanup_owned(project, args.owner_token)
                else:
                    run(compose + ["down", "--volumes", "--remove-orphans"], cwd=source)
                print(f"CLEANED | project={project}")
            except RestoreError as error:
                print(f"CLEANUP_FAILED | {error}", file=sys.stderr)
                status = 1
        elif args.cleanup:
            print(f"NOT_CLEANED | nothing was created by this run for project {project}", file=sys.stderr)
        if owner_file is not None:
            owner_file.unlink(missing_ok=True)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
