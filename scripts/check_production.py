"""Validate API-only Compose boundaries without starting containers or printing keys."""

import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def main():
    result = subprocess.run(
        ["docker", "compose", "-f", "compose.yaml", "-f", "compose.prod.yaml",
         "--profile", "*", "config", "--format", "json"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    config = json.loads(result.stdout)
    api = config["services"]["api"]
    web = config["services"]["web"]
    checks = {
        "API has no public ports": not api.get("ports"),
        "API uses production environment": api["environment"]["APP_ENV"] == "production",
        "Unique upstream alias": "flareledger-api" in api["networks"]["ingress"]["aliases"],
        "Ingress is external": config["networks"]["ingress"].get("external") is True,
        "Ingress has a dedicated name": config["networks"]["ingress"]["name"] == "flareledger_ingress",
        "Local web is opt-in": web.get("profiles") == ["local-web"],
        "Local web has no host ports": not web.get("ports"),
        "Web is not on ingress": "ingress" not in web["networks"],
        "SQLite has its own volume": any(v["type"] == "volume" and v["target"] == "/app/state" for v in api["volumes"]),
        "Corpus is read-only": any(v["target"] == "/app/data" and v.get("read_only") for v in api["volumes"]),
    }
    for label, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'} {label}")
    if not all(checks.values()):
        raise SystemExit(1)
    subprocess.run(["docker", "compose", "-f", "compose.certbot.yaml", "config", "--quiet"], cwd=ROOT, check=True)
    print("PASS Certbot maintenance configuration parses; no volumes or services started")


if __name__ == "__main__":
    main()
