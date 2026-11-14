"""Check FlareLedger frontend/API HTTPS, readiness and the age of the last backup.

Modes:
  external  public readiness (HTTP 200 and status ready), catalogue reads and the TLS
            certificate; frontend entry point, TLS and /api readiness with the
            same corpus version. Needs no server access, so it can run from GitHub Actions.
  local     the same plus the age of the newest daily snapshot and free disk space.
            Runs on the VPS, for example from the systemd timer in infra/systemd.

A single failed attempt is not reported: the checks are repeated (--attempts, spaced
by --interval seconds) and the run fails only if every attempt fails. Exit code 0
means healthy, 1 means unhealthy. One JSON line is printed for logs.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import deploy_tools as tools

MIN_FREE_FRACTION = 0.10


def disk_check(path: Path) -> tools.Check:
    usage = shutil.disk_usage(path)
    free = usage.free / usage.total
    return tools.Check("disk space", free >= MIN_FREE_FRACTION, f"{free * 100:.0f}% free of {usage.total / 2**30:.0f} GiB")


def collect(mode: str, public: str, snapshots: Path, web: str = tools.PUBLIC_WEB) -> list[tools.Check]:
    ready, version = tools.public_ready(public)
    checks = [ready, tools.check_tls(public)]
    checks += tools.frontend_checks(web, version)
    if ready.ok:
        checks.append(tools.parallel_reads(public, rounds=1, workers=4))
    if mode == "local":
        checks += [tools.backup_age(snapshots, "daily"), disk_check(snapshots)]
    return checks


def monitor(mode: str, public: str, snapshots: Path, attempts: int, interval: float, sleep=time.sleep, web: str = tools.PUBLIC_WEB) -> tuple[bool, list[tools.Check], int]:
    checks: list[tools.Check] = []
    for number in range(1, attempts + 1):
        checks = collect(mode, public, snapshots, web)
        if all(check.ok for check in checks):
            return True, checks, number
        if number < attempts:
            sleep(interval)
    return False, checks, attempts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=("external", "local"), default="external")
    parser.add_argument("--public-url", default=tools.PUBLIC_API)
    parser.add_argument("--web-url", default=tools.PUBLIC_WEB, help="frontend HTTPS origin; checks its /api rewrite too")
    parser.add_argument("--snapshots", type=Path, default=Path("/var/backups/flareledger/snapshots"))
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--interval", type=float, default=60.0, help="seconds between attempts")
    args = parser.parse_args(argv)
    if args.attempts < 1:
        parser.error("--attempts must be at least 1")
    ok, checks, used = monitor(args.mode, args.public_url, args.snapshots, args.attempts, args.interval, web=args.web_url)
    print(tools.render(checks))
    print(
        json.dumps(
            {
                "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "mode": args.mode,
                "ok": ok,
                "attempts_used": used,
                "checks": [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in checks],
            },
            sort_keys=True,
        )
    )
    if not ok:
        print(f"UNHEALTHY | failed on all {used} attempts", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
