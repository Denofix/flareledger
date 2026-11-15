"""Checks shared by the FlareLedger deploy, rollback and monitoring scripts.

Only the Python standard library is used. Network helpers go through http_get so
tests can replace them. None of these helpers changes any state.
"""

from __future__ import annotations

import json
import socket
import ssl
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

PUBLIC_API = "https://api.flareledger.fun"
PUBLIC_WEB = "https://flareledger.fun"
SITES = ("https://qresto.cfd", "https://feloza.pl")
# (path, expected status). The unknown ID must stay a JSON 404, never a 5xx.
CATALOG_PATHS = (
    ("/api/health/ready", 200),
    ("/api/meta", 200),
    ("/api/investigations?limit=1", 200),
    ("/api/records?limit=1", 200),
    ("/api/trials?limit=1", 200),
    ("/api/series?limit=1", 200),
    ("/api/investigations/__deploy_check_unknown__", 404),
)
TLS_FAIL_DAYS = 10.0
TLS_WARN_DAYS = 21.0
BACKUP_MAX_AGE_HOURS = 26.0


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


def http_get(url: str, timeout: float = 15.0) -> tuple[int, bytes]:
    request = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": "flareledger-ops/1"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
    except (urllib.error.URLError, OSError, TimeoutError) as error:
        return 0, str(error).encode("utf-8", "replace")


def public_ready(base: str = PUBLIC_API) -> tuple[Check, str | None]:
    status, body = http_get(base + "/api/health/ready")
    try:
        payload = json.loads(body)
    except ValueError:
        return Check("public ready", False, f"HTTP {status}, not JSON"), None
    if not isinstance(payload, dict):
        return Check("public ready", False, f"HTTP {status}, JSON object required"), None
    version = payload.get("corpus_version")
    if status == 200 and payload.get("status") == "ready" and version:
        return Check("public ready", True, f"corpus {str(version)[:24]}"), version
    return Check("public ready", False, f"HTTP {status}: {str(payload)[:120]}"), None


def frontend_checks(base: str, api_version: str | None) -> list[Check]:
    """Check the static entry point, TLS and the real same-origin API rewrite.

    Ask is deliberately not probed: its current 503 llm_unavailable is expected,
    and monitoring must not consume model quota after generation is enabled.
    """
    base = base.rstrip("/")
    status, body = http_get(base + "/")
    html = body.decode("utf-8", "replace").lower()
    shell = 'id="app"' in html and '<script' in html and 'src=' in html
    page = Check("frontend page", status == 200 and shell,
                 f"HTTP {status}, application shell {'present' if shell else 'missing'}")
    tls = check_tls(base)
    ready, version = public_ready(base)
    checks = [page, Check("frontend TLS", tls.ok, tls.detail),
              Check("frontend ready", ready.ok, ready.detail)]
    if ready.ok and api_version is not None:
        checks.append(Check("frontend corpus version", version == api_version,
                            "matches direct API" if version == api_version else "differs from direct API"))
    return checks


def parallel_reads(base: str = PUBLIC_API, rounds: int = 6, workers: int = 8) -> Check:
    """Overlapping catalog reads; any unexpected status (a 503, for example) fails."""
    jobs = [item for _ in range(rounds) for item in CATALOG_PATHS]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda job: (job, http_get(base + job[0])[0]), jobs))
    bad = [f"{path}={status}" for (path, expected), status in results if status != expected]
    if bad:
        return Check("parallel catalog reads", False, f"{len(bad)}/{len(jobs)} unexpected: {bad[0]}")
    return Check("parallel catalog reads", True, f"{len(jobs)} requests, all as expected")


def sites_up(sites: tuple[str, ...] = SITES) -> Check:
    down = [f"{site}={http_get(site)[0]}" for site in sites]
    down = [item for item in down if not item.endswith("=200")]
    return Check("neighbouring sites", not down, ", ".join(down) if down else "all 200")


def tls_days_left(host: str, port: int = 443, timeout: float = 10.0) -> float:
    """Days until the served certificate expires; the chain is verified normally."""
    context = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=timeout) as raw:
        with context.wrap_socket(raw, server_hostname=host) as tls:
            expires = ssl.cert_time_to_seconds(tls.getpeercert()["notAfter"])
    return (expires - datetime.now(timezone.utc).timestamp()) / 86400.0


def check_tls(base: str = PUBLIC_API) -> Check:
    host = urlsplit(base).hostname or ""
    try:
        days = tls_days_left(host)
    except (OSError, ssl.SSLError, KeyError, ValueError) as error:
        return Check("tls certificate", False, f"{host}: {error}")
    detail = f"{days:.1f} days left"
    if days < TLS_FAIL_DAYS:
        return Check("tls certificate", False, detail + f" (renewal should have happened; limit {TLS_FAIL_DAYS:.0f})")
    if days < TLS_WARN_DAYS:
        detail += " (warning: below 21 days)"
    return Check("tls certificate", True, detail)


def backup_age(snapshots: Path, kind: str = "daily", now: datetime | None = None) -> Check:
    marker = snapshots / f"last-success-{kind}.json"
    try:
        created = datetime.fromisoformat(json.loads(marker.read_text(encoding="utf-8"))["created_at"])
    except (OSError, ValueError, KeyError) as error:
        return Check(f"{kind} backup age", False, f"no readable {marker.name}: {error}")
    hours = ((now or datetime.now(timezone.utc)) - created).total_seconds() / 3600.0
    ok = hours <= BACKUP_MAX_AGE_HOURS
    return Check(f"{kind} backup age", ok, f"{hours:.1f} h old (limit {BACKUP_MAX_AGE_HOURS:.0f} h)")


def render(checks: list[Check]) -> str:
    return "\n".join(f"  {'OK ' if check.ok else 'BAD'} {check.name}: {check.detail}" for check in checks)
