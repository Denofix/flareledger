# Infrastructure

Timofey coordinates infrastructure. Backend, frontend, pinned dependencies, the
explicit corpus importer and container builds are implemented. The frontend is
published on Vercel and the API runs on the VPS. See the dated
[release audit](../docs/RELEASE_AUDIT.md) and [status](../docs/INFRA_STATUS.md).

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
Vercel. API-only production configuration and the applied Nginx/Certbot setup are
documented in [the production runbook](proxy/PRODUCTION.md). DNS, public HTTPS and
the dedicated ingress are configured; a routine update must not repeat bootstrap.
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
Backend and frontend workflows also run their actual checks and image builds.

With Docker Engine running, also run `python scripts/test_caddy.py`. It validates
the actual Caddyfile and tests static files, SPA routes, API prefix/query retention,
POST forwarding, JSON 404, and static availability during an upstream outage.
It uses a Python HTTP stub and clearly marked temporary HTML, not the application
or NASA data. Official Caddy/Python images may be pulled on the first run. A unique
Compose project binds a random localhost port and removes its own containers,
network and volumes in a finally block. No existing application stack is stopped.

## Local startup with a fresh database

These commands are for a separate local project, not the managed VPS checkout.
The source, dependency files and importer are already included in this repository.

Start Docker Engine and copy .env.example to .env (`Copy-Item .env.example .env`
in PowerShell or `cp .env.example .env` in a POSIX shell). Leave LLM_ENABLED=false
and both request limits at zero. No provider key is needed for the catalog, sources
or charts. VITE_* settings are public, never secrets. Ask migration and activation
are separate steps in [AI setup](../docs/AI_SETUP.md).

```sh
docker compose -f compose.yaml -f compose.dev.yaml build
docker compose -f compose.yaml -f compose.dev.yaml up -d api
```

Initialize this fresh local database explicitly; Compose supplies the container
DATA_DIR and DATABASE_PATH. Do not re-import at every startup or use initialization
as production recovery. Ready returns 503 until the required corpus exists; live
checks only the process. LLM outages do not change catalog readiness. Then:

```sh
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps api python -m app.ingest
docker compose -f compose.yaml -f compose.dev.yaml up -d web
docker compose -f compose.yaml -f compose.dev.yaml ps
python scripts/smoke.py
```

The smoke script checks live/ready, catalog, JSON 404, and direct /compare SPA
navigation. It never calls an LLM and does not verify scientific conclusions,
database persistence or Ask failure states. Those require manual acceptance.
Docker unhealthy status does not automatically restart a running process.
These commands use the local image tag. Production names an explicit reviewed
release; the current technical baseline and image are recorded in the release audit.

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

For a local persistence check, verify search, graphs, source links and disabled-LLM behavior.
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

Production snapshots, retention, the off-VPS copy and the separate-project restore
are scripted: see [backup and recovery](../docs/BACKUP_RECOVERY.md). The manual
utility above remains the building block they use. Do not overwrite the active
database.

Before an update record the SHA, image IDs, corpus version and backup. Keep the
previous images and corpus. Roll back by selecting the prior IMAGE_TAG without
rebuilding. Schema changes may require the matching database backup as well.
These local instructions do not authorize a VPS deployment or remote rollback.
