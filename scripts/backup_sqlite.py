"""Run inside api with stdin redirected from this file; see infra/README.md."""

import os
from contextlib import closing
from pathlib import Path
import sqlite3
from datetime import datetime, timezone


def main():
    source = Path(os.environ["DATABASE_PATH"]).resolve()
    if not source.is_file():
        raise SystemExit("Database does not exist; initialize the verified corpus first.")
    directory = source.parent / "backups"
    directory.mkdir(mode=0o700, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    destination = directory / f"flareledger-{stamp}.sqlite3"
    # mode=ro prevents silently creating an empty source DB. backup() handles WAL.
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=30)) as reader:
            with closing(sqlite3.connect(destination, timeout=30)) as writer:
                reader.backup(writer)
                result = writer.execute("PRAGMA integrity_check").fetchall()
                if result != [("ok",)]:
                    raise RuntimeError(f"Backup integrity check failed: {result}")
        destination.chmod(0o600)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    print(destination)
    print("Copy this backup off the volume, with manifest, corpus and application SHA.")


if __name__ == "__main__":
    main()
