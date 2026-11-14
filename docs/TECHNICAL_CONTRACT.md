# Technical contract

## Implemented in this bootstrap

The repository layout, contribution process, MIT code license, data license boundary, setup documentation, and repository-check command exist. The application and deployment interfaces below are the implementation target. Their commands must not be advertised as runnable until the corresponding files and code are merged.

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

Readiness must not make an LLM call or re-import the corpus. Ingestion requires an explicit, documented, idempotent command, to be implemented by backend/data development. No importer command exists yet.

LLM failure must not disable catalog, source access, or valid charts. Before generation is enabled, implement its complete timeout, rate limits, concurrency guard, and unavailable/insufficient-evidence responses. The environment example documents the proposed names and disabled defaults, not functioning safeguards.

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

Timofey adds actual Dockerfiles, Compose, and application CI after obtaining the implementation and its verified commands. For an existing QResto host, inspect the current ingress first. Proposed isolation is a separate FlareLedger directory, Compose project or Kubernetes namespace, persistent application state, and read-only corpus.

If the current host proxy forwards to a loopback port, 127.0.0.1:18080 is only a candidate until confirmed free. A containerized ingress needs a reachable container upstream or an approved host gateway; its localhost is not the application container. Public 80/443 remain owned by the existing ingress.

Manual deployment of a verified commit is sufficient for the first demo. Hosting, server IP, ingress implementation, DNS, and HTTPS remain open until checked. See [DEPLOYMENT.md](DEPLOYMENT.md).
