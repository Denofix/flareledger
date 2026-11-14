# Monorepo structure

One repository holds the API, web client, reviewed data, infrastructure, and team documentation. Keep the directory contract stable so each team member can work independently.

| Path | Contents and boundary |
| --- | --- |
| backend/app/ | Planned FastAPI package, routes, retrieval, data access, and LLM adapter |
| backend/tests/ | Future meaningful backend tests, added with the implementation |
| frontend/src/ | Planned Vue application and API client |
| frontend/public/ | Small reviewed public assets; all files here may be served to browsers |
| data/demo/ | Reviewed demo seed and its provenance |
| data/raw/ | Local original research downloads, ignored except documentation |
| data/processed/ | Local generated import products, ignored except documentation |
| infra/docker/ | Future Dockerfiles and container documentation |
| infra/proxy/ | Future ingress configuration selected after server inspection |
| scripts/ | Reproducible repository and operations commands |
| docs/adr/ | Agreed architecture decisions |
| design/ | Original design exports and asset credits |
| presentation/ | Pitch content, demo script, and source credits |
| .github/ | Collaboration templates, owners, dependency maintenance, and CI |

Git tracks files rather than empty directories. README files preserve the initial directory layout and describe what belongs there.

Python dependencies belong in backend/requirements.txt and backend/requirements-dev.txt when the backend is introduced. Frontend dependencies belong in frontend/package.json and frontend/package-lock.json when the web client is introduced. Those files must reflect real, tested dependencies.

Do not put SQLite state, environment secrets, backup archives, generated frontend bundles, virtual environments, node_modules, or bulk NASA downloads in Git. Small reviewed demo files may be tracked under data/demo/ with their provenance and license information.
