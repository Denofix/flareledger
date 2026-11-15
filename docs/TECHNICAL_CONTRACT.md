# Technical contract

## Implemented application

The repository layout, contribution process, MIT code license, data license boundary,
setup documentation and infrastructure scaffold exist. The first backend and importer
are implemented with pinned dependencies, lint, type checks and native tests.
See [backend setup](../backend/README.md) and the [API handoff](BACKEND_API.md).
The Vue frontend is implemented with npm dependencies, type checks, lint, tests,
a production build, a local API proxy and Vercel routing configuration. See
[frontend setup](../frontend/README.md) and [deployment handoff](FRONTEND_HANDOFF.md).
The backend is deployed on the VPS and the frontend is published on Vercel.
An optional Gemini adapter is implemented; enabled production generation and
independent scientific evaluation remain separate work.

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

LLM failure must not disable catalog, source access or measured data. Ask defaults
to a structured unavailable response and source retrieval. The opt-in Gemini
adapter requires an explicitly allowed Gemini model, key, positive rolling quotas and
explicit `python -m app.migrate_ask` after a backup. Reservations persist in the
same SQLite snapshot; quota writes never change source entities. A transactional
lease, network timeout, byte limits, no retries and explicit insufficient-evidence
behavior bound enabled operation. See [AI setup](AI_SETUP.md) for precise limits,
mechanical validation gaps and recovery precautions. Budget: USD 0, no paid fallback.

## Frontend contract

| Item | Agreed target |
| --- | --- |
| Directory | frontend/ |
| Framework | Vue 3, TypeScript, Vite |
| Node target | Node 24; pinned dependencies and package-lock.json |
| Package manager | npm, with a committed package-lock.json |
| Install and build, from frontend/ | npm ci; npm run build |
| Build output | frontend/dist/ |
| API base | /api through VITE_API_BASE_URL |
| Checks | npm run typecheck; npm run lint; npm run test; npm run build |

The Vite development proxy forwards /api to API_PROXY_TARGET (default
http://127.0.0.1:8000). Vercel forwards /api to https://api.flareledger.fun and
uses a separate non-API SPA fallback. Keep VITE_API_BASE_URL=/api for the agreed
deployment; direct cross-origin API access needs a separately agreed CORS policy.
Runtime API keys never belong in VITE_* values.

Charts preserve source point order, missing values and original time coordinates.
Comparison requires matching axis quantity names and units; matching axes do not
establish matched experimental conditions. Unknown values render as Not reported.
Ask handles structured unavailable, rate-limited and insufficient-evidence results
without claiming generation. Generated text is escaped and labeled FlareLedger,
with model/corpus, exact context excerpts, verified source links and limitations.
Mechanical citation checks do not constitute independent scientific review.

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
