"""Read-only request connections to an explicitly initialized, versioned corpus."""

import json
import re
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from typing import Any

from app.config import Settings
from app.corpus import SCHEMA_VERSION, SEED_FORMAT


class CorpusUnavailable(RuntimeError):
    """A verified database is not ready to serve."""


class Repository:
    def __init__(self, settings: Settings):
        self.settings = settings

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        try:
            uri = self.settings.database_path.as_uri() + "?mode=ro"
            # FastAPI can move a request between workers, including dependency cleanup.
            # Each request owns one connection; its operations remain sequential.
            with closing(sqlite3.connect(uri, uri=True, timeout=2, check_same_thread=False)) as connection:
                connection.row_factory = sqlite3.Row
                connection.execute("PRAGMA query_only=ON")
                self.metadata(connection)
                yield connection
        except (OSError, ValueError, sqlite3.Error) as exc:
            raise CorpusUnavailable("Verified corpus is unavailable; run the documented importer.") from exc

    def metadata(self, connection: sqlite3.Connection) -> dict:
        if connection.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
            raise CorpusUnavailable("The corpus database schema is unavailable or unsupported.")
        row = connection.execute("SELECT metadata_json FROM fl_corpus WHERE id=1").fetchone()
        if row is None:
            raise CorpusUnavailable("The required corpus has not been initialized.")
        metadata = json.loads(row[0])
        manifest = json.loads(self.settings.manifest_path.read_text(encoding="utf-8"))
        if metadata["seed_sha256"] != manifest["sha256"] or metadata["seed_format"] != SEED_FORMAT:
            raise CorpusUnavailable("The database does not match the required source manifest.")
        return metadata

    def readiness(self) -> dict:
        with self.connection() as connection:
            metadata = self.metadata(connection)
            actual = dict(connection.execute("SELECT kind, COUNT(*) FROM fl_entities GROUP BY kind"))
            if actual != metadata["entity_counts"]:
                raise CorpusUnavailable("The corpus database is incomplete.")
            points = sum(
                len(json.loads(row[0])["points"])
                for row in connection.execute("SELECT payload_json FROM fl_entities WHERE kind='series'")
            )
            if points != metadata["statistics"]["time_series_points"]:
                raise CorpusUnavailable("The numerical series are incomplete.")
            return metadata

    @staticmethod
    def item(connection: sqlite3.Connection, kind: str, identifier: str) -> dict | None:
        row = connection.execute(
            "SELECT payload_json FROM fl_entities WHERE kind=? AND identifier=?", (kind, identifier)
        ).fetchone()
        return json.loads(row[0]) if row else None

    @staticmethod
    def page(
        connection: sqlite3.Connection,
        kind: str,
        limit: int,
        offset: int,
        investigation_id: str | None = None,
        record_type: str | None = None,
    ) -> dict:
        conditions = ["kind=?"]
        parameters: list[Any] = [kind]
        for column, value in (("investigation_id", investigation_id), ("record_type", record_type)):
            if value is not None:
                conditions.append(f"{column}=?")
                parameters.append(value)
        where = " AND ".join(conditions)
        total = connection.execute(f"SELECT COUNT(*) FROM fl_entities WHERE {where}", parameters).fetchone()[
            0
        ]
        rows = connection.execute(
            f"SELECT payload_json FROM fl_entities WHERE {where} ORDER BY ordinal LIMIT ? OFFSET ?",
            [*parameters, limit, offset],
        )
        items = [json.loads(row[0]) for row in rows]
        if kind == "series":
            items = [{k: v for k, v in item.items() if k not in {"points", "source_rows"}} for item in items]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    def detail(self, connection: sqlite3.Connection, kind: str, item: dict) -> dict:
        source_ids = list(item.get("source_ids", []))
        if item.get("source_id"):
            source_ids.append(item["source_id"])
        if kind == "source":
            source_ids.append(item["id"])
        evidence_ids = item.get("evidence_ids", [])
        sources = [self.item(connection, "source", i) for i in dict.fromkeys(source_ids)]
        evidence = [self.item(connection, "evidence", i) for i in evidence_ids]
        issues = [
            json.loads(row[0])
            for row in connection.execute(
                "SELECT payload_json FROM fl_entities WHERE kind='quality_issue' ORDER BY ordinal"
            )
        ]
        investigation_id = item.get("investigation_id") or (item["id"] if kind == "investigation" else None)
        issues = [
            q
            for q in issues
            if q["id"] in item.get("quality_issue_ids", [])
            or (investigation_id is not None and investigation_id in q.get("investigation_ids", []))
        ]
        return {"item": item, "sources": sources, "evidence": evidence, "quality_issues": issues}

    def search(self, connection: sqlite3.Connection, query: str, limit: int) -> list[dict]:
        stop = {"a", "an", "and", "are", "do", "does", "how", "in", "is", "of", "the", "to", "what", "why"}
        tokens = list(dict.fromkeys(t for t in re.findall(r"[\w-]+", query.casefold()) if t not in stop))[:8]
        if not tokens:
            return []
        conditions = ["kind IN ('investigation','record','knowledge_card','source')"]
        parameters: list[Any] = []
        for token in tokens:
            conditions.append("search_text LIKE ? ESCAPE '\\'")
            parameters.append("%" + token.replace("\\", "\\\\").replace("_", "\\_") + "%")
        rows = connection.execute(
            "SELECT kind, identifier, investigation_id, payload_json FROM fl_entities WHERE "
            + " AND ".join(conditions)
            + " ORDER BY CASE kind WHEN 'investigation' THEN 0 WHEN 'knowledge_card' THEN 1 "
            + "WHEN 'record' THEN 2 ELSE 3 END, ordinal LIMIT ?",
            [*parameters, limit],
        )
        results = []
        for row in rows:
            item = json.loads(row["payload_json"])
            source_ids = item.get("source_ids", []) or ([item["id"]] if row["kind"] == "source" else [])
            results.append(
                {
                    "kind": row["kind"],
                    "id": row["identifier"],
                    "investigation_id": row["investigation_id"],
                    "title": item.get("title_en") or item.get("title") or item.get("material") or item["id"],
                    "excerpt": (item.get("text_en") or item.get("summary_en") or item.get("material") or "")[
                        :500
                    ],
                    "source_ids": source_ids,
                    "evidence_ids": item.get("evidence_ids", []),
                    "sources": [self.item(connection, "source", i) for i in source_ids],
                }
            )
        return results
