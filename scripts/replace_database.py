"""Replace the SQLite database of a running FlareLedger API with a verified snapshot.

Subcommands: replace and rollback. Both only describe what they would do unless
--execute is given. Use --project to point them at a rehearsal project instead of
the live one; rehearse there first (scripts/rehearse_replace.py).

replace: verifies the snapshot offline, refuses a snapshot of a different corpus,
takes a pre-update snapshot of the current database, stops only the API container,
swaps the file inside its state volume (the old file is kept next to it as
flareledger.sqlite3.replaced-<stamp>), starts the container and checks that it is
ready and serves exactly what the snapshot contains. If any check fails, or the swap
fails, the previous file is put back and checked again. Nothing is deleted.

rollback: puts the newest (or --stamp) kept previous file back.

The API is stopped for the swap, so the live service is unavailable for about half
a minute. A snapshot must come from a compatible schema; the checks refuse one whose
schema version the tooling does not know.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import snapshot_tools as snap
from restore_snapshot import PROBE

ROOT = Path(__file__).resolve().parents[1]
BACKUP_SCRIPT = ROOT / "scripts" / "backup_production.py"
LIVE_PROJECT = "flareledger"
PUBLIC_API = "https://api.flareledger.fun"
COUNT_KEYS = ("corpus_version", "investigations", "records", "trial_rows", "series", "points")

# Runs inside the API image as root with only the state volume and the snapshot mounted.
SWAP = """
import hashlib, json, os, shutil, sys
state = os.environ.get("STATE_DIR", "/app/state")
source = os.environ.get("SNAPSHOT_DIR", "/snapshot") + "/flareledger.sqlite3"
stamp, expected = sys.argv[1], sys.argv[2]
live = state + "/flareledger.sqlite3"
incoming = live + ".incoming"

def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def own(path):
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        os.chown(path, 10001, 10001)
    os.chmod(path, 0o600)

try:
    shutil.copyfile(source, incoming)
    own(incoming)
    if digest(incoming) != expected:
        raise SystemExit("checksum mismatch after copying the snapshot; the live file was not touched")
    with open(incoming, "r+b") as handle:
        os.fsync(handle.fileno())
except BaseException:
    if os.path.exists(incoming):
        os.unlink(incoming)
    raise
saved = live + ".replaced-" + stamp
if os.path.exists(live):
    os.rename(live, saved)
    for suffix in ("-wal", "-shm"):
        if os.path.exists(live + suffix):
            os.rename(live + suffix, saved + suffix)
os.rename(incoming, live)
try:  # durability of the rename; best effort where directories cannot be opened
    fd = os.open(state, os.O_RDONLY)
    os.fsync(fd)
    os.close(fd)
except OSError:
    pass
print(json.dumps({"saved": os.path.basename(saved), "live_sha256": digest(live)}))
"""

UNDO = """
import hashlib, json, os, sys
state = os.environ.get("STATE_DIR", "/app/state")
stamp = sys.argv[1]
live = state + "/flareledger.sqlite3"
saved = live + ".replaced-" + stamp
if not os.path.exists(saved):
    raise SystemExit("no kept previous file for stamp " + stamp)
if os.path.exists(live):
    os.rename(live, live + ".replaced-away-" + stamp)
    for suffix in ("-wal", "-shm"):
        if os.path.exists(live + suffix):
            os.rename(live + suffix, live + ".replaced-away-" + stamp + suffix)
os.rename(saved, live)
for suffix in ("-wal", "-shm"):
    if os.path.exists(saved + suffix):
        os.rename(saved + suffix, live + suffix)
try:  # durability of the rename; best effort where directories cannot be opened
    fd = os.open(state, os.O_RDONLY)
    os.fsync(fd)
    os.close(fd)
except OSError:
    pass
h = hashlib.sha256()
with open(live, "rb") as handle:
    for block in iter(lambda: handle.read(1 << 20), b""):
        h.update(block)
print(json.dumps({"restored": stamp, "live_sha256": h.hexdigest()}))
"""

LIST = """
import os
state = os.environ.get("STATE_DIR", "/app/state")
for name in sorted(os.listdir(state)):
    if name.startswith("flareledger.sqlite3.replaced-") and not name.endswith(("-wal", "-shm")) and "-away-" not in name:
        print(name.rsplit(".replaced-", 1)[1])
"""


class ReplaceError(Exception):
    pass


def run(command: list[str], env: dict | None = None, cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=False, env={**os.environ, **(env or {})}, cwd=cwd
        )
    except OSError as error:
        raise ReplaceError(f"Cannot run {command[0]}: {error}") from error
    if result.returncode != 0:
        raise ReplaceError(f"{' '.join(command[:4])} failed: {(result.stderr or result.stdout).strip()[-400:]}")
    return result.stdout


@contextmanager
def lock(directory: Path):
    import fcntl  # Linux only

    with (directory / ".replace.lock").open("w") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ReplaceError("Another replacement, deploy or backup is running") from error
        yield


def target(project: str) -> tuple[str, str, str]:
    """(container id, image reference, state volume name) of the project's API."""
    ids = run(
        [
            "docker", "ps", "--quiet",
            "--filter", f"label=com.docker.compose.project={project}",
            "--filter", "label=com.docker.compose.service=api",
        ]
    ).split()
    if len(ids) != 1:
        raise ReplaceError(f"Expected one running api container in project {project}, found {len(ids)}")
    cid = ids[0]
    image = run(["docker", "inspect", cid, "--format", "{{.Config.Image}}"]).strip()
    volume = run(
        ["docker", "inspect", cid, "--format", '{{range .Mounts}}{{if eq .Destination "/app/state"}}{{.Name}}{{end}}{{end}}']
    ).strip()
    if not volume:
        raise ReplaceError("The API container has no named volume at /app/state")
    return cid, image, volume


def probe(cid: str) -> dict:
    """What the API serves now. An API that answers 503 or cannot be reached is "unavailable"."""
    try:
        return json.loads(run(["docker", "exec", cid, "python", "-c", PROBE]).strip().splitlines()[-1])
    except (ReplaceError, ValueError, IndexError):
        return {"ready": "unavailable"}


def running_seed(cid: str) -> str:
    code = "import json; print(json.load(open('/app/data/demo/seed-reference.json'))['sha256'])"
    return run(["docker", "exec", cid, "python", "-c", code]).strip()


def helper(image: str, volume: str, script: str, *arguments: str, snapshot: Path | None = None) -> str:
    command = ["docker", "run", "--rm", "--read-only", "--network", "none", "--user", "0", "--entrypoint", "python",
               "-v", f"{volume}:/app/state"]
    if snapshot is not None:
        command += ["-v", f"{snapshot}:/snapshot:ro"]
    return run(command + [image, "-c", script, *arguments])


def wait_healthy(cid: str, attempts: int = 45) -> None:
    for _ in range(attempts):
        try:
            if run(["docker", "inspect", cid, "--format", "{{.State.Health.Status}}"]).strip() == "healthy":
                return
        except ReplaceError:
            pass
        time.sleep(2)
    raise ReplaceError("The API did not become healthy within 90 seconds")


def restart(cid: str) -> None:
    run(["docker", "start", cid])
    wait_healthy(cid)


def expected_facts(manifest: dict) -> dict:
    return {"ready": "ready", **{key: manifest["corpus"][key] for key in COUNT_KEYS}}


def matches(observed: dict, expected: dict, strict: bool) -> bool:
    if not strict:
        return observed.get("ready") == "ready"
    return all(observed.get(key) == value for key, value in expected.items())


def public_ok(public: str | None, version: str) -> bool:
    if not public:
        return True
    import deploy_tools

    check, found = deploy_tools.public_ready(public)
    return check.ok and found == version


def log(directory: Path, entry: dict) -> None:
    entry = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), **entry}
    with (directory / "replace.log").open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def safety_backup(project: str, snapshots: Path, repo: Path) -> str:
    output = run(
        [sys.executable, str(BACKUP_SCRIPT), "--dest", str(snapshots), "--kind", "pre-update",
         "--repo", str(repo), "--project", project]
    )
    for part in output.split("|"):
        if part.strip().startswith("snapshot="):
            return part.strip().split("=", 1)[1]
    raise ReplaceError("The safety backup did not report a snapshot")


def put_back(cid: str, image: str, volume: str, stamp: str) -> dict:
    run(["docker", "stop", cid])
    result = json.loads(helper(image, volume, UNDO, stamp).strip().splitlines()[-1])
    restart(cid)
    return result


def do_replace(args: argparse.Namespace) -> int:
    snapshot = args.snapshot.resolve()
    manifest = snap.verify_snapshot(snapshot)
    cid, image, volume = target(args.project)
    seed = running_seed(cid)
    if manifest["corpus"]["seed_sha256"] != seed and not args.allow_corpus_change:
        raise ReplaceError(
            "The snapshot is from a different corpus than the one the running API serves; "
            "pass --allow-corpus-change only for a deliberate corpus change"
        )
    baseline = probe(cid)
    if baseline.get("ready") != "ready":
        raise ReplaceError("The API is not ready now; refusing to replace its database")
    print(f"snapshot: {snapshot.name}  corpus {manifest['corpus']['corpus_version'][:30]}")
    print(f"target:   project {args.project}, container {cid[:12]}, volume {volume}, image {image}")
    print(f"current:  {baseline['investigations']} investigations, {baseline['records']} records, {baseline['points']} points")
    if not args.execute:
        print("PLAN_ONLY | add --execute: safety backup, stop the API, swap the file, start, verify, "
              "and put the previous file back if anything fails")
        return 0
    stamp = snap.utc_stamp()
    strict = not args.allow_corpus_change
    expected = expected_facts(manifest)
    with lock(args.snapshots):
        backup = safety_backup(args.project, args.snapshots, args.repo)
        print(f"safety backup of the current database: {backup}")
        log(args.snapshots, {"event": "started", "project": args.project, "snapshot": snapshot.name, "stamp": stamp, "backup": backup})
        failure = None
        try:
            run(["docker", "stop", cid])
            output = helper(image, volume, SWAP, stamp, manifest["database_sha256"], snapshot=snapshot)
            print("swapped: " + output.strip().splitlines()[-1])
            restart(cid)
            observed = probe(cid)
            version = manifest["corpus"]["corpus_version"]
            good = matches(observed, expected, strict) and public_ok(args.public_url, version if strict else observed.get("corpus_version", ""))
            print(f"after replacement: ready={observed.get('ready')}, {observed.get('investigations')} investigations, "
                  f"{observed.get('records')} records, {observed.get('trial_rows')} trial_row, {observed.get('series')} series, {observed.get('points')} points")
            if not good:
                failure = "the replaced database does not serve what the snapshot contains"
        except (ReplaceError, snap.SnapshotError, ValueError, KeyError) as error:
            failure = str(error)
        if failure is None:
            log(args.snapshots, {"event": "ok", "project": args.project, "stamp": stamp, "backup": backup})
            print(f"REPLACE_OK | stamp {stamp} | previous file kept as flareledger.sqlite3.replaced-{stamp} | backup {backup}")
            return 0
        print(f"FAILED | {failure}", file=sys.stderr)
        try:
            # Put the kept file back if the swap got as far as moving it; otherwise the
            # live file was never touched and the API only needs to be running again.
            if stamp in [line for line in helper(image, volume, LIST).splitlines() if line.strip()]:
                put_back(cid, image, volume, stamp)
            else:
                restart(cid)
            back = probe(cid)
            if matches(back, baseline, strict=True) and public_ok(args.public_url, baseline["corpus_version"]):
                log(args.snapshots, {"event": "rolled_back", "project": args.project, "stamp": stamp, "failure": failure})
                print(f"ROLLED_BACK | the previous database is serving again and matches the state before; failure: {failure}", file=sys.stderr)
                return 1
            failure += "; the restored state does not match the state before"
        except (ReplaceError, ValueError, KeyError) as error:
            failure += f"; putting the previous file back failed: {error}"
        log(args.snapshots, {"event": "rollback_failed", "project": args.project, "stamp": stamp, "failure": failure})
        print(f"ROLLBACK_FAILED | manual recovery needed; safety backup {backup}; kept file flareledger.sqlite3.replaced-{stamp}. {failure}", file=sys.stderr)
        return 2


def do_rollback(args: argparse.Namespace) -> int:
    cid, image, volume = target(args.project)
    stamps = [line for line in helper(image, volume, LIST).splitlines() if line.strip()]
    if not stamps:
        raise ReplaceError("No kept previous database file was found in the state volume")
    stamp = args.stamp or stamps[-1]
    if stamp not in stamps:
        raise ReplaceError(f"Unknown stamp {stamp}; available: {', '.join(stamps)}")
    print(f"target: project {args.project}, volume {volume}; kept previous files: {', '.join(stamps)}")
    print(f"would restore stamp {stamp}")
    if not args.execute:
        print("PLAN_ONLY | add --execute: stop the API, put the kept file back, start and check readiness")
        return 0
    with lock(args.snapshots):
        before = probe(cid)
        result = put_back(cid, image, volume, stamp)
        after = probe(cid)
        ok = after.get("ready") == "ready" and public_ok(args.public_url, after.get("corpus_version", ""))
        log(args.snapshots, {"event": "manual_rollback_ok" if ok else "manual_rollback_failed", "project": args.project, "stamp": stamp})
        print(f"restored {result['restored']} (sha256 {result['live_sha256'][:16]}); ready={after.get('ready')}; before had {before.get('records')} records")
        if not ok:
            print("ROLLBACK_FAILED | the API is not ready after restoring the kept file", file=sys.stderr)
            return 2
        print("ROLLBACK_OK")
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("replace", "rollback"))
    parser.add_argument("snapshot", nargs="?", type=Path, help="snapshot directory (replace only)")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--project", default=LIVE_PROJECT, help="Compose project of the API (rehearsals use their own)")
    parser.add_argument("--snapshots", type=Path, default=Path("/var/backups/flareledger/snapshots"))
    parser.add_argument("--repo", type=Path, default=ROOT, help="tooling checkout used by the backup script")
    parser.add_argument("--public-url", help=f"also require this public URL to serve the data (live: {PUBLIC_API})")
    parser.add_argument("--allow-corpus-change", action="store_true", help="snapshot may come from a different corpus")
    parser.add_argument("--stamp", help="rollback: which kept file to restore (default newest)")
    args = parser.parse_args(argv)
    if args.command == "replace" and args.snapshot is None:
        parser.error("replace needs a snapshot directory")
    if args.project == LIVE_PROJECT and args.execute and not args.public_url:
        parser.error(f"the live project needs --public-url {PUBLIC_API} so the public service is checked too")
    try:
        return do_replace(args) if args.command == "replace" else do_rollback(args)
    except (ReplaceError, snap.SnapshotError, OSError) as error:
        print(f"REPLACE_REFUSED | {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
