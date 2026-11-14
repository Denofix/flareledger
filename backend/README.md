# Backend

Implementation target: Python 3.12, FastAPI, SQLite, and a source-linked corpus. Read [the technical contract](../docs/TECHNICAL_CONTRACT.md).

The first backend PR must add app/main.py, requirements.txt, requirements-dev.txt, actual checks, and /api/health/live plus /api/health/ready. It must document how to initialize state and import the corpus. The application and these commands are not implemented in this bootstrap.

The future production entry point is app.main:app on port 8000, with /api preserved by the proxy. Live LLM access remains disabled until its implementation and free API access are verified.
