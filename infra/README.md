# Infrastructure

Timofey coordinates infrastructure. This branch provides a local container scaffold,
Compose configuration and SQLite backup checks. Application source, dependency
files and the data importer are not implemented in this checkout yet. Images have
not been built or run. See [progress](../docs/INFRA_STATUS.md).

## Layout and boundaries

- API: Python 3.12, app.main:app, one Uvicorn worker, internal port 8000.
- Web: Node 24/npm build stage and Caddy serving dist with an /api proxy and SPA fallback.
- Local URL: http://127.0.0.1:8080 using compose.dev.yaml. API has no published port.
- State: app_state volume at /app/state, database /app/state/flareledger.sqlite3.
- Corpus: ./data mounted read-only at /app/data, including the team's demo seed.
- API runs as UID/GID 10001 with a read-only root filesystem and writable state/tmp.
- Logs rotate at 10 MB with three files per service. Resource limits are initial
  budgets for validation, not measured application requirements.

The team selected Vercel for the public frontend and the VPS for API/SQLite. The
local web container is for development and fallback demos; it does not replace
Vercel. API-only production configuration and the Nginx/Certbot candidates are
documented in [the production runbook](proxy/PRODUCTION.md); no DNS, certificate
or server change has been applied.
Follow [the contract](../docs/TECHNICAL_CONTRACT.md) and
[deployment decision](../docs/DEPLOYMENT.md).

## Checks available now

From the repository root, with Python installed and Docker Compose CLI available:

```sh
docker compose -f compose.yaml -f compose.dev.yaml config --quiet
python scripts/test_backup.py
python scripts/check_repository.py
```

Compose configuration validation does not build or start containers and does not
need a running Docker Engine. The backup tests use disposable synthetic databases,
not scientific data. They verify an active WAL backup and a missing source database.
The separate infrastructure workflow runs these real checks without provider keys.
Application CI will be added after real dependencies and commands are available.

With Docker Engine running, also run `python scripts/test_caddy.py`. It validates
the actual Caddyfile and tests static files, SPA routes, API prefix/query retention,
POST forwarding, JSON 404, and static availability during an upstream outage.
It uses a Python HTTP stub and clearly marked temporary HTML, not the application
or NASA data. Official Caddy/Python images may be pulled on the first run. A unique
Compose project binds a random localhost port and removes its own containers,
network and volumes in a finally block. No existing application stack is stopped.

## Startup after the application handoff

The commands in this section are pending application implementation. First obtain:

1. backend/app/main.py, requirements.txt and requirements-dev.txt with checked commands.
2. frontend/package.json, package-lock.json and source with build/typecheck/lint scripts.
3. Backend confirmation of env names, health routes, write permissions, and a tested
   explicit import command for data/demo/FlareLedger_NASA_Demo_Data.json.

Start Docker Engine and copy .env.example to .env (`Copy-Item .env.example .env`
in PowerShell or `cp .env.example .env` in a POSIX shell). Leave LLM_ENABLED=false
and both request limits at zero. Compose passes the settings; the backend must
implement their meaning. FreeLLMAPI is not included in this scaffold. Its reserved
example key is not passed to any container. VITE_* settings are public, never secrets.

```sh
docker compose -f compose.yaml -f compose.dev.yaml build
docker compose -f compose.yaml -f compose.dev.yaml up -d api
```

Run the backend owner's tested import command with container paths, DATA_DIR=/app/data
and DATABASE_PATH=/app/state/flareledger.sqlite3. Do not guess a CLI or re-import at
every startup. Ready returns 503 until the required corpus is initialized; live
checks only the process. LLM outages must not change catalog readiness. Then:

```sh
docker compose -f compose.yaml -f compose.dev.yaml up -d web
docker compose -f compose.yaml -f compose.dev.yaml ps
python scripts/smoke.py
```

The smoke script checks live/ready, catalog, JSON 404, and direct /compare SPA
navigation. It never calls an LLM and does not verify scientific conclusions,
database persistence or Ask failure states. Those require manual acceptance.
Docker unhealthy status does not automatically restart a running process.
Confirm versions/digests after the first successful build; current image tags are
provisional and are not a verified release.

## Operation and acceptance

```sh
docker compose -f compose.yaml -f compose.dev.yaml logs --tail 100 api web
docker compose -f compose.yaml -f compose.dev.yaml stop
docker compose -f compose.yaml -f compose.dev.yaml start
```

Do not log provider credentials or post resolved Compose configuration containing
keys. Use config --quiet. Never run down -v or system-wide cleanup to repair this
project. A newly created app_state volume inherits image ownership; an existing
volume with different permissions requires an explicit migration, not deletion.

After the handoff, verify real search, graph, source links and disabled-LLM behavior.
Record the catalog and /api/meta values, recreate only api, and compare actual records
and corpus version afterward; HTTP 200 alone does not prove persistence:

```sh
docker compose -f compose.yaml -f compose.dev.yaml up -d --force-recreate api
python scripts/smoke.py
```

## Backup and restoration

With the real API running, execute the backup utility inside its container.
PowerShell:

```powershell
Get-Content -Raw scripts/backup_sqlite.py | docker compose -f compose.yaml -f compose.dev.yaml exec -T api python -
```

POSIX shell:

```sh
docker compose -f compose.yaml -f compose.dev.yaml exec -T api python - < scripts/backup_sqlite.py
```

The utility uses SQLite backup(), including committed WAL content, checks integrity,
and prints a filename under /app/state/backups. Copy that exact file to private
storage outside the volume with docker compose cp. Keep its matching corpus,
manifest/source hashes, application SHA and image IDs. A backup on the same volume
alone is not disaster recovery. Never commit runtime backups.

Rehearse restore in a separate Compose project with a separate state volume and
different localhost port. Supply the matching backup, corpus and application image,
preserve UID permissions, then verify ready, records, sources and corpus_version.
Do not overwrite the active database. A whole-application restore is still pending
the real importer/schema; reading the test backup is not proof of that recovery.

Before an update record the SHA, image IDs, corpus version and backup. Keep the
previous images and corpus. Roll back by selecting the prior IMAGE_TAG without
rebuilding. Schema changes may require the matching database backup as well.
The current phase performs no VPS deployment or remote rollback.
