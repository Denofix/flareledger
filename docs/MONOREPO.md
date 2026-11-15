# Monorepo structure

One repository holds the API, web client, reviewed data, infrastructure, and team documentation. Keep the directory contract stable so each team member can work independently.

| Path | Contents and boundary |
| --- | --- |
| backend/app/ | FastAPI routes, retrieval, data access and the optional Gemini adapter |
| backend/tests/ | Corpus, API, quota, citation and recovery tests |
| frontend/src/ | Vue application, measured charts and API client |
| frontend/public/ | Small reviewed public assets; all files here may be served to browsers |
| data/demo/ | Reviewed demo seed and its provenance |
| data/ask-context/ | Hash-pinned original ReadMe companion required for document-text retrieval |
| data/raw/ | Local original research downloads, ignored except documentation |
| data/processed/ | Local generated import products, ignored except documentation |
| infra/docker/ | Container documentation; application Dockerfiles live in backend/ and frontend/ |
| infra/proxy/ | Reviewed ingress configuration and production runbook |
| scripts/ | Reproducible repository and operations commands |
| docs/adr/ | Agreed architecture decisions |
| design/ | Original design exports and asset credits |
| presentation/ | Pitch content, demo script, and source credits |
| .github/ | Collaboration templates, owners, dependency maintenance, and CI |

Git tracks files rather than empty directories. README files preserve the initial directory layout and describe what belongs there.

Python dependencies are pinned in backend/requirements.txt and backend/requirements-dev.txt. Frontend dependencies are recorded in frontend/package.json and frontend/package-lock.json. These files reflect the implemented and tested applications.

Do not put SQLite state, environment secrets, backup archives, generated frontend bundles, virtual environments, node_modules, or bulk NASA downloads in Git. Small reviewed demo files may be tracked under data/demo/ with their provenance and license information.
