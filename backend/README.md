# Backend

Python 3.12, FastAPI and SQLite. This implementation imports the committed English
NASA demo v2 after checking its manifest. Native tests cover the real source data,
idempotent ingestion and backend backup restoration. The frontend and production
deployment are separate work. See the [API handoff](../docs/BACKEND_API.md).

## Native Ubuntu development

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m app.ingest
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000/api/docs> in the VM's browser. These are interactive
API docs, not the product frontend. Defaults use data/ and ignored state/ in the
repository root. The root .env.example contains container paths and is not loaded
automatically. DATA_DIR and DATABASE_PATH environment variables override defaults.

In another terminal, from backend/ with its virtual environment active:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy app
python -m pytest -q
```

Runtime and development dependencies are separately pinned, including transitive
dependencies. The backend workflow also requests a real Docker image build;
native test results do not prove that a container or VPS deployment was tested.

## Import and readiness

python -m app.ingest is the only initialization command. It makes no network
requests. It verifies seed bytes against data/demo/seed-reference.json, validates
counts and references, and writes a transaction to a dedicated SQLite file.
Identical input is a no-op. A different corpus requires --replace after a backup.
An unrelated or unsupported database is rejected.

The complete original seed bytes are retained as a compressed SQLite snapshot.
Indexed records keep their original JSON payloads. Numerical points, units, nulls,
evidence locators, raw material and source limitations remain unchanged.

The HTTP API opens SQLite read-only and does not import or create state at startup.
Liveness checks the process; readiness returns 503 until a complete matching corpus
exists. Readiness checks the required manifest version and entity/point counts;
it does not call an LLM or replace independent scientific or backup review.

## Container handoff for Timofey

The following commands use the existing Dockerfile and agreed container paths.
Image construction and startup still require verification on a Docker host:

```bash
docker compose -f compose.yaml build api
docker compose -f compose.yaml run --rm --no-deps api python -m app.ingest
docker compose -f compose.yaml up -d api
docker compose -f compose.yaml exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health/ready').read().decode())"
```

Importer and runtime both use the existing UID 10001, state at
/app/state/flareledger.sqlite3 and a read-only corpus at /app/data. Run the explicit
import once, not on every restart. API port 8000 remains internal. The Vercel
frontend will use /api rewrites to the confirmed HTTPS API hostname. No frontend
build or ingress change is included here.

Follow the backup and off-volume copy procedure in [infra/README.md](../infra/README.md).
Backend tests rehearse backup/restore with the real corpus and a new app instance.
Full VPS recovery, external HTTPS and off-host retention remain infrastructure work.

## Live AI

This release provides lexical discovery and source retrieval. POST /api/ask always
returns HTTP 503, answer=null, llm_unavailable and available lexical evidence.
No provider is called, including when LLM_ENABLED=true is accidentally supplied.
The API budget remains USD 0.

Provider selection, enabled-mode timeouts, quotas and concurrency enforcement are
not implemented. Existing LLM environment names are reserved settings, not active
guards for an enabled adapter. Enable generation only in a separate reviewed
implementation after verifying an official free API and its limits.
