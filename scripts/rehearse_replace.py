"""Rehearse database replacement and rollback on a separate Compose project and volume.

Restores the given snapshot into a new flareledger-restore-rehearsal-<id> project (its
own state volume, no published port, no ingress), then drives scripts/replace_database.py
against that project only and checks every outcome:

  1. a tampered snapshot is refused and the database is unchanged;
  2. a snapshot of another corpus is refused without --allow-corpus-change;
  3. a valid snapshot (the same data plus a harmless marker table) replaces the file;
  4. rollback puts the original file back;
  5. an accepted other-corpus snapshot that the API rejects is rolled back automatically.

The variants are made from the given snapshot in a scratch folder; they are never
written to the real snapshot directory. The live project is never touched. Run it from
the tooling checkout with --project-dir pointing at a checkout of the snapshot's
application revision, as for scripts/restore_snapshot.py.
"""

from __future__ import annotations

import argparse
import json
import secrets
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from pathlib import Path

import snapshot_tools as snap
import restore_snapshot

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "flareledger-restore-rehearsal"

STATE = """
import hashlib, json, sqlite3
path = "/app/state/flareledger.sqlite3"
digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
with sqlite3.connect("file:" + path + "?mode=ro&immutable=1", uri=True) as c:
    marker = c.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='rehearsal_marker'").fetchone()[0] == 1
print(json.dumps({"sha256": digest, "marker": marker}))
"""


def sh(command: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout, result.stderr


def make_variant(source: Path, target: Path, marker: bool = False, seed: str | None = None, tamper: bool = False) -> Path:
    shutil.copytree(source, target)
    database = target / snap.DATABASE_NAME
    manifest = json.loads((target / snap.MANIFEST_NAME).read_text(encoding="utf-8"))
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("PRAGMA journal_mode=DELETE")
        if marker:
            connection.execute("CREATE TABLE rehearsal_marker (note TEXT)")
        if seed:
            metadata = json.loads(connection.execute("SELECT metadata_json FROM fl_corpus").fetchone()[0])
            metadata["seed_sha256"] = seed
            connection.execute("UPDATE fl_corpus SET metadata_json=?", (json.dumps(metadata),))
            manifest["corpus"]["seed_sha256"] = seed
        connection.commit()
    manifest["database_sha256"] = snap.sha256_file(database)
    (target / snap.MANIFEST_NAME).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    snap.write_checksums(target)
    if tamper:
        with database.open("ab") as handle:
            handle.write(b"x")  # now disagrees with SHA256SUMS
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--project-dir", type=Path, required=True, help="checkout of the snapshot's application revision")
    parser.add_argument("--project", help=f"rehearsal project; must start with {PREFIX}")
    parser.add_argument("--keep", action="store_true", help="leave the rehearsal project in place")
    args = parser.parse_args(argv)
    project = args.project or f"{PREFIX}-{secrets.token_hex(3)}"
    if not project.startswith(PREFIX):
        parser.error(f"--project must start with {PREFIX} so the live project is never touched")
    snapshot, app = args.snapshot.resolve(), args.project_dir.resolve()
    snap.verify_snapshot(snapshot)
    scratch = Path(tempfile.mkdtemp(prefix="flareledger-rehearsal-"))
    journal = scratch / "journal"
    journal.mkdir()
    results: list[tuple[str, bool, str]] = []
    owner = secrets.token_hex(16)

    def record(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))
        print(f"  {'PASS' if ok else 'FAIL'} {name}{': ' + detail if detail else ''}")

    def replace(*arguments: str) -> tuple[int, str, str]:
        return sh([sys.executable, str(ROOT / "scripts" / "replace_database.py"), *arguments,
                   "--project", project, "--snapshots", str(journal), "--repo", str(ROOT)])

    def state() -> dict:
        _, ids, _ = sh(["docker", "ps", "--quiet", "--filter", f"label=com.docker.compose.project={project}",
                        "--filter", "label=com.docker.compose.service=api"])
        code, out, err = sh(["docker", "exec", ids.split()[0], "python", "-c", STATE])
        if code != 0:
            raise RuntimeError(err.strip()[-300:])
        return json.loads(out.strip().splitlines()[-1])

    try:
        code, out, err = sh([sys.executable, str(ROOT / "scripts" / "restore_snapshot.py"), str(snapshot),
                             "--project-dir", str(app), "--project", project, "--owner-token", owner])
        print(out.strip().splitlines()[-1] if out.strip() else err.strip())
        if code != 0:
            record("restore the snapshot into the rehearsal project", False, err.strip()[-200:])
            return 1
        original = state()
        record("restore the snapshot into the rehearsal project", not original["marker"], f"database {original['sha256'][:12]}")

        tampered = make_variant(snapshot, scratch / "flareledger-daily-20000101T000000Z-aaaaaaa1", marker=True, tamper=True)
        code, _, err = replace("replace", str(tampered), "--execute")
        record("tampered snapshot refused, database unchanged", code == 1 and "REPLACE_REFUSED" in err and state() == original)

        other = make_variant(snapshot, scratch / "flareledger-daily-20000101T000000Z-aaaaaaa2", seed="c" * 64)
        code, _, err = replace("replace", str(other), "--execute")
        record("other corpus refused without --allow-corpus-change", code == 1 and "different corpus" in err and state() == original)

        marked = make_variant(snapshot, scratch / "flareledger-daily-20000101T000000Z-aaaaaaa3", marker=True)
        marked_sha = snap.sha256_file(marked / snap.DATABASE_NAME)
        code, out, err = replace("replace", str(marked), "--execute")
        now = state()
        record("valid snapshot replaces the database", code == 0 and "REPLACE_OK" in out and now["sha256"] == marked_sha and now["marker"], err.strip()[-200:])

        code, out, err = replace("rollback", "--execute")
        now = state()
        record("rollback restores the original file", code == 0 and "ROLLBACK_OK" in out and now == original, err.strip()[-200:])

        code, _, err = replace("replace", str(other), "--execute", "--allow-corpus-change")
        now = state()
        record("rejected corpus change rolled back automatically", code == 1 and "ROLLED_BACK" in err and now == original, err.strip()[-200:])
    except (RuntimeError, IndexError, OSError, snap.SnapshotError) as error:
        record("rehearsal error", False, str(error))
    finally:
        if not args.keep:
            try:
                removed = restore_snapshot.cleanup_owned(project, owner)
                print(f"  {'CLEANED' if removed else 'NOT_CLEANED: no owned resources'} {project}")
            except (restore_snapshot.RestoreError, OSError) as error:
                record("cleanup owned resources", False, str(error))
        shutil.rmtree(scratch, ignore_errors=True)
    failed = [name for name, ok, _ in results if not ok]
    print("REHEARSAL_OK" if not failed and len(results) == 6 else f"REHEARSAL_FAILED | {', '.join(failed) or 'incomplete'}")
    return 0 if not failed and len(results) == 6 else 1


if __name__ == "__main__":
    raise SystemExit(main())
