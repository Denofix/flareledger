import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from app.storage import Repository


def test_request_connection_survives_worker_handoffs_and_stays_read_only(settings):
    repository = Repository(settings)
    manager = repository.connection()
    # A synchronous FastAPI dependency can open, use and close on different workers.
    with (
        ThreadPoolExecutor(max_workers=1) as opening_worker,
        ThreadPoolExecutor(max_workers=1) as endpoint_worker,
        ThreadPoolExecutor(max_workers=1) as closing_worker,
    ):
        connection = opening_worker.submit(manager.__enter__).result(timeout=10)

        def read_and_reject_write():
            result = repository.page(connection, "record", 1, 0)
            assert connection.execute("PRAGMA query_only").fetchone()[0] == 1
            with pytest.raises(sqlite3.OperationalError, match="readonly"):
                connection.execute("DELETE FROM fl_entities")
            return result

        try:
            page = endpoint_worker.submit(read_and_reject_write).result(timeout=10)
            assert page["total"] == 1132
            assert len(page["items"]) == 1
        finally:
            closing_worker.submit(manager.__exit__, None, None, None).result(timeout=10)

    assert repository.readiness()["entity_counts"]["record"] == 1132


def test_overlapping_api_reads_keep_catalog_counts_and_json_404(client):
    cases = (
        ("/api/meta", 200, None),
        ("/api/investigations?limit=1", 200, 10),
        ("/api/records?limit=1", 200, 1132),
        ("/api/trials?limit=1", 200, 647),
        ("/api/series?limit=1", 200, 6),
        ("/api/investigations/__concurrency_unknown_id__", 404, None),
    )
    barrier = Barrier(4)

    def read_catalog():
        barrier.wait(timeout=10)
        for path, status, total in cases:
            response = client.get(path)
            assert response.status_code == status, (path, response.text)
            assert response.headers["cache-control"] == "no-store"
            body = response.json()
            if total is not None:
                assert body["total"] == total
                assert len(body["items"]) == 1
            elif status == 404:
                assert body["detail"]["code"] == "not_found"
            else:
                assert body["live_generation_available"] is False

    with ThreadPoolExecutor(max_workers=4) as workers:
        pending = [workers.submit(read_catalog) for _ in range(4)]
        for future in pending:
            future.result(timeout=30)

    assert client.get("/api/health/ready").status_code == 200
