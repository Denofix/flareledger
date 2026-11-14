"""Restore a FlareLedger snapshot into a separate Compose project and verify it.

The restore project has its own state volume and no published port or ingress network,
so it cannot touch the running API. It is meant to be run from a checkout whose
data/demo corpus matches the snapshot and from which the snapshot's image tag exists.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import snapshot_tools as tools

ROOT = Path(__file__).resolve().parents[1]
PROJECT_PREFIX = "flareledger-restore"

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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="snapshot directory (for example one pulled from off the VPS)")
    parser.add_argument("--project", default=PROJECT_PREFIX, help=f"Compose project; must start with {PROJECT_PREFIX}")
    parser.add_argument("--project-dir", type=Path, default=ROOT, help="checkout with compose.yaml and data/")
    parser.add_argument("--cleanup", action="store_true", help="remove the restore containers, network and volume afterwards")
    args = parser.parse_args()
    if not args.project.startswith(PROJECT_PREFIX):
        parser.error(f"--project must start with {PROJECT_PREFIX} so the live project is never touched")
    snapshot = args.snapshot.resolve()
    project_dir = args.project_dir.resolve()
    compose = ["docker", "compose", "--project-name", args.project, "--file", str(project_dir / "compose.yaml")]
    status = 1
    try:
        manifest = tools.verify_snapshot(snapshot)
        facts = manifest["corpus"]
        print(f"SNAPSHOT_OK | {snapshot.name} | corpus={facts['corpus_version']} | app={manifest['application']['image_tag']}")
        seed = json.loads((project_dir / "data" / "demo" / "seed-reference.json").read_text(encoding="utf-8"))
        if seed.get("sha256") != facts["seed_sha256"]:
            raise RestoreError("The checkout corpus does not match the snapshot; check out the snapshot's application SHA")
        image_tag = manifest["application"]["image_tag"]
        run(["docker", "image", "inspect", image_tag])  # fails clearly if the image is missing
        env = {"IMAGE_TAG": image_tag.rsplit(":", 1)[-1], "APP_ENV": "production", "LLM_ENABLED": "false"}
        run(compose + ["create", "api"], env=env, cwd=project_dir)
        volume = f"{args.project}_app_state"
        run(
            [
                "docker", "run", "--rm", "--read-only", "--network", "none", "--user", "0",
                "--entrypoint", "python",
                "-v", f"{volume}:/app/state", "-v", f"{snapshot}:/snapshot:ro",
                image_tag, "-c", COPY,
            ]
        )
        run(compose + ["up", "-d", "api"], env=env, cwd=project_dir)
        for _ in range(45):
            health = run(
                compose + ["ps", "--format", "{{.Health}}", "api"], env=env, cwd=project_dir
            ).strip()
            if health == "healthy":
                break
            time.sleep(2)
        else:
            raise RestoreError("The restored API did not become healthy within 90 seconds")
        output = run(compose + ["exec", "-T", "api", "python", "-c", PROBE], env=env, cwd=project_dir)
        observed = json.loads(output.strip().splitlines()[-1])
        expected = {"ready": "ready", "corpus_version": facts["corpus_version"]} | {
            key: facts[key] for key in ("investigations", "records", "trial_rows", "series", "points")
        }
        for key, value in expected.items():
            marker = "OK " if observed.get(key) == value else "BAD"
            print(f"  {marker} {key}: restored={observed.get(key)} snapshot={value}")
        if observed != expected:
            raise RestoreError("Restored API does not match the verified snapshot")
        print(f"RESTORE_OK | project={args.project} | volume={volume}")
        status = 0
    except (RestoreError, tools.SnapshotError, OSError, ValueError, KeyError) as error:
        print(f"RESTORE_FAILED | {error}", file=sys.stderr)
    finally:
        if args.cleanup:
            try:
                run(compose + ["down", "--volumes", "--remove-orphans"], cwd=project_dir)
                print(f"CLEANED | project={args.project}")
            except RestoreError as error:
                print(f"CLEANUP_FAILED | {error}", file=sys.stderr)
                status = 1
    return status


if __name__ == "__main__":
    raise SystemExit(main())
