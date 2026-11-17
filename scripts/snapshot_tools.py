"""Shared helpers to write, verify and prune FlareLedger SQLite snapshots.

A snapshot is a directory holding the database, a manifest, the source manifest
and SHA256SUMS. Verification reads the database offline and does not need the API.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_FORMAT = "flareledger.backup.v1"
DATABASE_NAME = "flareledger.sqlite3"
MANIFEST_NAME = "manifest.json"
SEED_REFERENCE_NAME = "seed-reference.json"
CHECKSUMS_NAME = "SHA256SUMS"
KINDS = ("daily", "pre-update")
SNAPSHOT_NAME = re.compile(r"^flareledger-(daily|pre-update)-\d{8}T\d{6}Z-[a-f0-9]{8}$")
CHECKSUM_LINE = re.compile(r"^([a-f0-9]{64}) [ *]([^/\\]+)$")
SCHEMA_VERSION = 1


class SnapshotError(Exception):
    """Raised when a snapshot is incomplete, altered or not restorable."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def database_facts(database: Path) -> dict:
    """Read integrity and corpus facts from a snapshot copy without modifying it."""
    uri = database.resolve().as_uri() + "?mode=ro&immutable=1"
    try:
        with closing(sqlite3.connect(uri, uri=True, timeout=10)) as connection:
            if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise SnapshotError("SQLite integrity_check failed")
            if connection.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
                raise SnapshotError("Unsupported database schema version")
            row = connection.execute("SELECT metadata_json FROM fl_corpus WHERE id=1").fetchone()
            if row is None:
                raise SnapshotError("The database contains no imported corpus")
            metadata = json.loads(row[0])
            entities = dict(connection.execute("SELECT kind, COUNT(*) FROM fl_entities GROUP BY kind"))
            record_types = dict(
                connection.execute(
                    "SELECT json_extract(payload_json, '$.record_type'), COUNT(*) "
                    "FROM fl_entities WHERE kind='record' GROUP BY 1"
                )
            )
            points = sum(
                len(json.loads(item[0])["points"])
                for item in connection.execute("SELECT payload_json FROM fl_entities WHERE kind='series'")
            )
    except (sqlite3.Error, KeyError, ValueError) as error:
        raise SnapshotError(f"Cannot read the snapshot database: {error}") from error
    if entities != metadata["entity_counts"]:
        raise SnapshotError("Entity counts do not match the stored corpus metadata")
    if points != metadata["statistics"]["time_series_points"]:
        raise SnapshotError("Measured points do not match the stored corpus metadata")
    return {
        "corpus_version": metadata["corpus_version"],
        "seed_sha256": metadata["seed_sha256"],
        "investigations": entities.get("investigation", 0),
        "records": entities.get("record", 0),
        "trial_rows": record_types.get("trial_row", 0),
        "series": entities.get("series", 0),
        "points": points,
    }


def write_checksums(directory: Path) -> None:
    names = sorted(path.name for path in directory.iterdir() if path.is_file() and path.name != CHECKSUMS_NAME)
    lines = [f"{sha256_file(directory / name)}  {name}\n" for name in names]
    (directory / CHECKSUMS_NAME).write_text("".join(lines), encoding="utf-8", newline="\n")


def verify_snapshot(directory: Path) -> dict:
    """Return the manifest of a complete, unmodified and readable snapshot."""
    required = (DATABASE_NAME, MANIFEST_NAME, SEED_REFERENCE_NAME, CHECKSUMS_NAME)
    for name in required:
        if not (directory / name).is_file():
            raise SnapshotError(f"Snapshot is incomplete: {name} is missing")
    listed: dict[str, str] = {}
    for line in (directory / CHECKSUMS_NAME).read_text(encoding="utf-8").splitlines():
        match = CHECKSUM_LINE.match(line)
        if match is None:
            raise SnapshotError("Invalid SHA256SUMS entry")
        listed[match[2]] = match[1]
    for name in (DATABASE_NAME, MANIFEST_NAME, SEED_REFERENCE_NAME):
        if name not in listed:
            raise SnapshotError(f"SHA256SUMS does not cover {name}")
    for name, expected in listed.items():
        path = directory / name
        if not path.is_file() or sha256_file(path) != expected:
            raise SnapshotError(f"Checksum mismatch: {name}")
    try:
        manifest = json.loads((directory / MANIFEST_NAME).read_text(encoding="utf-8"))
    except ValueError as error:
        raise SnapshotError("manifest.json is not valid JSON") from error
    if manifest.get("format") != MANIFEST_FORMAT or manifest.get("project") != "flareledger":
        raise SnapshotError("Unsupported snapshot manifest")
    facts = database_facts(directory / DATABASE_NAME)
    if manifest.get("corpus") != facts:
        raise SnapshotError("The manifest does not describe the database in this snapshot")
    return manifest


def application_image(manifest: dict) -> str:
    application = manifest.get("application", {})
    return application.get("image_reference") or application.get("image_tag") or "unknown"


def snapshots(root: Path, kind: str) -> list[Path]:
    """Return snapshot directories of one kind, newest first."""
    if not root.is_dir():
        return []
    found = [
        path
        for path in root.iterdir()
        if path.is_dir() and SNAPSHOT_NAME.match(path.name) and path.name.startswith(f"flareledger-{kind}-")
    ]
    return sorted(found, key=lambda path: path.name, reverse=True)


def prune(root: Path, kind: str, keep: int) -> list[str]:
    """Delete older snapshots of one kind. Only names matching the snapshot pattern qualify."""
    if keep < 1:
        raise ValueError("keep must be at least 1")
    removed = []
    for path in snapshots(root, kind)[keep:]:
        if path.is_symlink() or path.parent.resolve() != root.resolve():
            raise SnapshotError(f"Unsafe retention target: {path}")
        shutil.rmtree(path)
        removed.append(path.name)
    return removed


IMAGE_REFERENCE = re.compile(r"^flareledger-api:([A-Za-z0-9_][A-Za-z0-9_.-]{0,127})$")
FULL_SHA = re.compile(r"^[a-f0-9]{40}$")


def release_tag(image_reference: str) -> str:
    """Return the part Compose expects in IMAGE_TAG from a full image reference.

    Compose builds the image name as flareledger-api:${IMAGE_TAG}, so passing the
    whole reference would produce flareledger-api:flareledger-api:<tag>.
    """
    match = IMAGE_REFERENCE.match(image_reference)
    if match is None:
        raise SnapshotError(f"Not a flareledger-api image reference: {image_reference!r}")
    return match[1]


def git_head(repository: Path) -> str:
    return _git(repository, "rev-parse", "--verify", "HEAD")


def resolve_revision(repository: Path, tag: str) -> str:
    """Resolve a commit-style image tag to a full commit SHA in the given repository.

    The running image, not the current folder, defines the application revision. Tags
    that are not commit abbreviations, or that are unknown or ambiguous here, are
    refused so the manifest never records a guessed revision.
    """
    if not re.fullmatch(r"[0-9a-f]{7,40}", tag):
        raise SnapshotError(f"Image tag {tag!r} is not a commit SHA; pass the revision explicitly")
    return _git(repository, "rev-parse", "--verify", "--quiet", f"{tag}^{{commit}}")


def _git(repository: Path, *arguments: str) -> str:
    import subprocess

    try:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments], capture_output=True, text=True, check=False
        )
    except OSError as error:
        raise SnapshotError(f"Cannot run git: {error}") from error
    value = result.stdout.strip()
    if result.returncode != 0 or not FULL_SHA.match(value):
        raise SnapshotError(f"Cannot resolve a commit with git {' '.join(arguments[:3])}")
    return value


def utc_stamp(moment: datetime | None = None) -> str:
    return (moment or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")


def main(argv: list[str] | None = None) -> int:
    import sys

    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 2 or arguments[0] != "verify":
        print("Usage: python scripts/snapshot_tools.py verify SNAPSHOT_DIRECTORY", file=sys.stderr)
        return 2
    try:
        manifest = verify_snapshot(Path(arguments[1]))
    except (SnapshotError, OSError) as error:
        print(f"SNAPSHOT_INVALID | {error}", file=sys.stderr)
        return 1
    corpus = manifest["corpus"]
    print(
        "SNAPSHOT_OK | "
        f"corpus={corpus['corpus_version']} | investigations={corpus['investigations']} | "
        f"records={corpus['records']} | trial_rows={corpus['trial_rows']} | "
        f"series={corpus['series']} | points={corpus['points']} | "
        f"image={application_image(manifest)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
