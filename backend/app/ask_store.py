"""Explicit, additive Ask state in the corpus database; no import or HTTP-time DDL."""

import sqlite3
import uuid
from contextlib import closing
from pathlib import Path


class AskStateUnavailable(RuntimeError):
    pass


class Limited(RuntimeError):
    def __init__(self, retry_after: int):
        self.retry_after = max(1, retry_after)


def connect(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=rw", uri=True, timeout=2)


def migrate(path: Path) -> None:
    """Keep corpus schema v1 backward compatible; own the additive Ask schema separately."""
    with closing(connect(path)) as db, db:
        if db.execute("PRAGMA user_version").fetchone()[0] != 1:
            raise AskStateUnavailable("Import the supported corpus before migrating Ask state.")
        if db.execute("SELECT COUNT(*) FROM fl_corpus").fetchone()[0] != 1:
            raise AskStateUnavailable("The corpus is not initialized.")
        db.execute("BEGIN IMMEDIATE")
        existing = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('fl_ask_schema','fl_ask_calls')"
            )
        }
        if existing and existing != {"fl_ask_schema", "fl_ask_calls"}:
            raise AskStateUnavailable(
                "Incomplete Ask state; restore a verified snapshot instead of resetting usage."
            )
        if existing and db.execute("SELECT version FROM fl_ask_schema WHERE id=1").fetchone() != (1,):
            raise AskStateUnavailable("Unsupported Ask state version; nothing was reset.")
        db.execute(
            "CREATE TABLE IF NOT EXISTS fl_ask_schema (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL, last_seen REAL NOT NULL)"
        )
        db.execute("INSERT OR IGNORE INTO fl_ask_schema VALUES (1, 1, 0)")
        if db.execute("SELECT version FROM fl_ask_schema WHERE id=1").fetchone()[0] != 1:
            raise AskStateUnavailable("Unsupported Ask state version; nothing was reset.")
        db.execute(
            "CREATE TABLE IF NOT EXISTS fl_ask_calls (id TEXT PRIMARY KEY, created_at REAL NOT NULL, lease_until REAL NOT NULL, finished INTEGER NOT NULL DEFAULT 0)"
        )
        db.execute("CREATE INDEX IF NOT EXISTS fl_ask_calls_time ON fl_ask_calls(created_at)")
        db.execute("SELECT id, created_at, lease_until, finished FROM fl_ask_calls LIMIT 0")


class AskStore:
    def __init__(self, path: Path):
        self.path = path

    def ready(self) -> bool:
        try:
            with closing(sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
                db.execute("SELECT id, created_at, lease_until, finished FROM fl_ask_calls LIMIT 0")
                return db.execute("SELECT version FROM fl_ask_schema WHERE id=1").fetchone() == (1,)
        except (sqlite3.Error, ValueError, OSError):
            return False

    def reserve(self, now: float, daily: int, minute: int, timeout: int) -> str:
        try:
            with closing(connect(self.path)) as db, db:
                db.execute("BEGIN IMMEDIATE")
                version, last_seen = db.execute(
                    "SELECT version, last_seen FROM fl_ask_schema WHERE id=1"
                ).fetchone()
                if version != 1 or now < last_seen:
                    raise AskStateUnavailable("Ask state or server clock is unavailable.")
                db.execute("UPDATE fl_ask_schema SET last_seen=? WHERE id=1", (now,))
                active = db.execute(
                    "SELECT MAX(lease_until) FROM fl_ask_calls WHERE finished=0 AND lease_until>?", (now,)
                ).fetchone()[0]
                if active is not None:
                    raise Limited(int(active - now) + 1)
                for window, maximum in ((60, minute), (86400, daily)):
                    count, earliest = db.execute(
                        "SELECT COUNT(*), MIN(created_at) FROM fl_ask_calls WHERE created_at>?",
                        (now - window,),
                    ).fetchone()
                    if count >= maximum:
                        raise Limited(int(earliest + window - now) + 1)
                db.execute("DELETE FROM fl_ask_calls WHERE created_at<?", (now - 172800,))
                identifier = uuid.uuid4().hex
                db.execute(
                    "INSERT INTO fl_ask_calls VALUES (?, ?, ?, 0)", (identifier, now, now + timeout + 60)
                )
                return identifier
        except (sqlite3.Error, TypeError, ValueError, OSError) as error:
            raise AskStateUnavailable("Ask quota state is unavailable.") from error

    def finish(self, identifier: str) -> None:
        # A provider error still consumes the reservation. A crash leaves a bounded lease.
        try:
            with closing(connect(self.path)) as db, db:
                db.execute("UPDATE fl_ask_calls SET finished=1 WHERE id=?", (identifier,))
        except sqlite3.Error:
            pass
