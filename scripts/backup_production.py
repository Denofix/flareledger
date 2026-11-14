"""Create a verified FlareLedger SQLite snapshot on the VPS host.

Runs on the Docker host (Linux). It uses the existing SQLite backup utility inside
the running API container, copies the result out of the volume, verifies it offline,
records a manifest and applies retention. Use --kind pre-update before an update.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import snapshot_tools as tools

ROOT = Path(__file__).resolve().parents[1]
CONTAINER_BACKUPS = "/app/state/backups/"


class BackupError(Exception):
    pass


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, **kwargs)
    except OSError as error:
        raise BackupError(f"Cannot run {command[0]}: {error}") from error
    if result.returncode != 0:
        raise BackupError(f"{' '.join(command[:3])} failed: {result.stderr.strip()[:400]}")
    return result.stdout


def find_container(project: str) -> str:
    output = run(
        [
            "docker", "ps", "--quiet",
            "--filter", f"label=com.docker.compose.project={project}",
            "--filter", "label=com.docker.compose.service=api",
        ]
    ).split()
    if len(output) != 1:
        raise BackupError(f"Expected one running api container for project {project}, found {len(output)}")
    return output[0]


def lock(directory: Path):
    import fcntl  # Linux only; imported here so the helpers stay importable elsewhere.

    handle = (directory / ".lock").open("w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as error:
        raise BackupError("Another backup is already running") from error
    return handle


def create_snapshot(container: str, project_dir: Path, dest: Path, kind: str) -> Path:
    utility = (ROOT / "scripts" / "backup_sqlite.py").read_text(encoding="utf-8")
    stdout = run(["docker", "exec", "-i", container, "python", "-"], input=utility)
    produced = stdout.splitlines()[0].strip() if stdout.strip() else ""
    if not produced.startswith(CONTAINER_BACKUPS) or ".." in produced:
        raise BackupError("The backup utility returned an unexpected path")
    pending = dest / f".pending-{secrets.token_hex(8)}"
    pending.mkdir(mode=0o700)
    try:
        run(["docker", "cp", f"{container}:{produced}", str(pending / tools.DATABASE_NAME)])
        # The copy is now outside the volume; drop the temporary in-volume file.
        run(["docker", "exec", container, "python", "-c", "import os,sys; os.unlink(sys.argv[1])", produced])
        seed = project_dir / "data" / "demo" / "seed-reference.json"
        shutil.copyfile(seed, pending / tools.SEED_REFERENCE_NAME)
        facts = tools.database_facts(pending / tools.DATABASE_NAME)
        source = json.loads(seed.read_text(encoding="utf-8"))
        if source.get("sha256") != facts["seed_sha256"]:
            raise BackupError("data/demo/seed-reference.json does not match the database corpus")
        image_tag = run(["docker", "inspect", container, "--format", "{{.Config.Image}}"]).strip()
        image_id = run(["docker", "inspect", container, "--format", "{{.Image}}"]).strip()
        git_sha = run(["git", "-C", str(project_dir), "rev-parse", "HEAD"]).strip()
        manifest = {
            "format": tools.MANIFEST_FORMAT,
            "project": "flareledger",
            "kind": kind,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "application": {
                "checkout_sha": git_sha,
                "image_tag": image_tag,
                "image_id": image_id,
                "checkout_matches_image_tag": image_tag.rsplit(":", 1)[-1] == git_sha[: len(image_tag.rsplit(":", 1)[-1])],
            },
            "corpus": facts,
            "database_sha256": tools.sha256_file(pending / tools.DATABASE_NAME),
            "database_bytes": (pending / tools.DATABASE_NAME).stat().st_size,
            "note": "Backup of SQLite state only. Keep it with the matching image tag and corpus manifest.",
        }
        (pending / tools.MANIFEST_NAME).write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
        tools.write_checksums(pending)
        for path in pending.iterdir():
            path.chmod(0o600)
        tools.verify_snapshot(pending)
        final = dest / f"flareledger-{kind}-{tools.utc_stamp()}-{secrets.token_hex(4)}"
        pending.rename(final)
        return final
    except BaseException:
        shutil.rmtree(pending, ignore_errors=True)
        raise


def log(dest: Path, entry: dict) -> None:
    entry = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), **entry}
    with (dest / "backup.log").open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, required=True, help="snapshot directory outside the Docker volume")
    parser.add_argument("--kind", choices=tools.KINDS, default="daily")
    parser.add_argument("--keep", type=int, default=7, help="snapshots of this kind to keep")
    parser.add_argument("--project", default="flareledger", help="Compose project name of the running API")
    parser.add_argument("--project-dir", type=Path, default=ROOT, help="checkout holding data/demo/seed-reference.json")
    args = parser.parse_args()
    if args.keep < 1:
        parser.error("--keep must be at least 1")
    args.dest.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.umask(0o077)
    try:
        handle = lock(args.dest)
    except BackupError as error:
        print(f"BACKUP_FAILED | {error}", file=sys.stderr)
        return 1
    with handle:
        try:
            container = find_container(args.project)
            final = create_snapshot(container, args.project_dir.resolve(), args.dest, args.kind)
            removed = tools.prune(args.dest, args.kind, args.keep)
        except (BackupError, tools.SnapshotError, OSError, ValueError) as error:
            log(args.dest, {"event": "backup_failed", "kind": args.kind, "error": str(error)})
            print(f"BACKUP_FAILED | {error}", file=sys.stderr)
            return 1
        manifest = tools.verify_snapshot(final)
        status = {
            "event": "backup_ok",
            "kind": args.kind,
            "snapshot": final.name,
            "corpus_version": manifest["corpus"]["corpus_version"],
            "image_tag": manifest["application"]["image_tag"],
            "pruned": removed,
        }
        log(args.dest, status)
        marker = args.dest / f"last-success-{args.kind}.json"
        temporary = marker.with_suffix(".tmp")
        temporary.write_text(json.dumps({**status, "created_at": manifest["created_at"]}, indent=2) + "\n", encoding="utf-8")
        temporary.replace(marker)
        print(f"BACKUP_OK | kind={args.kind} | snapshot={final.name} | kept<={args.keep} | pruned={len(removed)}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
