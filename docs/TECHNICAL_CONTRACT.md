# Technical contract

## Implemented in this bootstrap

The repository layout, contribution process, MIT code license, data license boundary,
setup documentation and infrastructure scaffold exist. The first backend and importer
are implemented with pinned dependencies, lint, type checks and native tests.
See [backend setup](../backend/README.md) and the [API handoff](BACKEND_API.md).
The backend is deployed on the VPS. Frontend and enabled LLM generation remain
implementation work.

## Backend target

| Item | Agreed target |
| --- | --- |
| Directory and Python | backend/, Python 3.12 |
| Entry point | backend/app/main.py exporting app |
| Runtime command, from backend/ | python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 |
| Dependencies | requirements.txt; requirements-dev.txt includes runtime dependencies and checks |
| API prefix | /api |
| Liveness | GET /api/health/live checks the process |
| Readiness | GET /api/health/ready checks SQLite and the required corpus; 503 until ready |
| State and corpus | DATABASE_PATH and DATA_DIR; writable SQLite state and read-only source corpus |
| Initial checks | python -m ruff check .; python -m pytest -q once configured and meaningful tests exist |

From backend/, python -m app.ingest imports the checksum-verified English v2 seed
using DATA_DIR and DATABASE_PATH. Repeating the identical import is a no-op.
Readiness checks the installed corpus without LLM calls or re-importing data.
Implemented checks are python -m ruff check ., python -m ruff format --check .,
python -m mypy app and python -m pytest -q.

LLM failure must not disable catalog, source access or measured data. Ask currently
returns a structured unavailable response and source retrieval, without generation.
Before generation is enabled, implement its complete timeout, rate limits,
concurrency guard and insufficient-evidence behavior. Reserved LLM environment names
are not functioning safeguards for an enabled adapter in this release.

## Frontend target

| Item | Agreed target |
| --- | --- |
| Directory | frontend/ |
| Framework | Vue 3, TypeScript, Vite |
| Node target | Node 24, subject to verification against the first real dependencies |
| Package manager | npm, with a committed package-lock.json |
| Install and build, from frontend/ | npm ci; npm run build |
| Build output | frontend/dist/ |
| API base | /api through VITE_API_BASE_URL |
| Checks | npm run typecheck; npm run lint; npm run build when the scripts exist |

The first frontend PR must include package.json, its lock file, real scripts, local /api proxy behavior, and SPA routing. Add unit-test commands only when the corresponding tests are present. Runtime API keys never belong in VITE_* values.

## Data target

Keep source records, original file versions, units, qualifiers, trial identity, and evidence locators. Import the reviewed JSON as a versioned corpus. A matrix row, operating condition, measurement series, source note, and historical incident must remain distinct record types.

The demo JSON includes actual source inconsistencies and measurements with camera limitations. Resolve or display those limitations instead of silently fixing the numbers. See [data/demo/README.md](../data/demo/README.md).

## Infrastructure target

Timofey has prepared Dockerfiles and a local Compose scaffold against this target
contract, plus infrastructure-only CI. Image builds and runtime compatibility remain
unverified until the application handoff. Application CI follows the real dependency
commands. See [infrastructure status](INFRA_STATUS.md).

The team selected a Vercel frontend and VPS API/SQLite. The local Compose web is a
development/fallback server. For the VPS, inspect existing ingress before selecting
production isolation and routing. The proposed production override attaches API to
the dedicated external flareledger_ingress network with alias flareledger-api;
existing Nginx owns HTTPS. See [the runbook](../infra/proxy/PRODUCTION.md). No remote
deployment change is included in this phase.

If the current host proxy forwards to a loopback port, 127.0.0.1:18080 is only a candidate until confirmed free. A containerized ingress needs a reachable container upstream or an approved host gateway; its localhost is not the application container. Public 80/443 remain owned by the existing ingress.

Manual deployment of a verified commit is sufficient for the first demo. The API
is deployed this way at https://api.flareledger.fun; see [DEPLOYMENT.md](DEPLOYMENT.md),
[INFRA_STATUS.md](INFRA_STATUS.md) and [BACKUP_RECOVERY.md](BACKUP_RECOVERY.md).
