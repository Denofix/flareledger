# FlareLedger

Explore NASA microgravity combustion research and trace fire safety explanations to their evidence.

FlareLedger is a team project for the **2026 NASA Space Apps Challenge**, addressing [Flame in Freefall](https://www.spaceappschallenge.org/2026/challenges/flame-in-freefall/?tab=resources). The planned workflow is to find an investigation, inspect its test conditions, compare suitable measurements, and read an explanation linked to the original sources.

## Current status

The first backend provides explicit checksum-verified SQLite ingestion, investigation
browsing, typed source records, measured series, lexical search and source-linked
comparison. Native tests exercise the real corpus and backend backup restoration.
See [backend setup](backend/README.md) and the [API handoff](docs/BACKEND_API.md).

The backend API runs on the VPS at https://api.flareledger.fun (readiness:
`/api/health/ready`) with the verified corpus, verified SQLite snapshots (an off-VPS copy is pulled
by the team laptop) and a tested restore procedure. The Vue frontend now provides
investigation browsing, original measured charts, compatible-series comparison,
source records and evidence search. Ask supports optional source-linked Gemini
explanations with persistent quotas and remains disabled by default. Production
activation and independent scientific evaluation are still pending. See [AI setup](docs/AI_SETUP.md),
[frontend setup](frontend/README.md), [Vercel handoff](docs/FRONTEND_HANDOFF.md),
[infrastructure status](docs/INFRA_STATUS.md)
and [backup and recovery](docs/BACKUP_RECOVERY.md).

The registered project domain is **flareledger.fun**. The frontend is published at https://flareledger.fun/ and https://flareledger.vercel.app/
from main commit 1d258c9, with same-origin /api forwarding to the VPS. The VPS lease ends on 1 December 2026. [Deployment decisions](docs/DEPLOYMENT.md) describe the layout.

## Start here

```bash
gh repo clone Denofix/flareledger
cd flareledger
python3 scripts/check_repository.py
```

For a new Ubuntu VM, follow the [Ubuntu and GitHub setup guide](docs/SETUP_UBUNTU.md). It covers installation, GitHub device-code login, Git identity, invitations, branch rules, and your next tasks.

- [Team rules](TEAM_RULES.md)
- [Contribution workflow](CONTRIBUTING.md)
- [Monorepo layout](docs/MONOREPO.md)
- [Backend and frontend contract](docs/TECHNICAL_CONTRACT.md)
- [Implementation roadmap](docs/ROADMAP.md)
- [Domain setup](docs/DOMAIN_SETUP.md)
- [Data and licensing](DATA_LICENSES.md)

## Repository layout

| Path | Responsibility |
| --- | --- |
| `backend/` | Python 3.12, FastAPI, SQLite ingestion, source retrieval and opt-in Gemini Ask |
| `frontend/` | Vue 3, TypeScript, Vite, measured charts and source-linked evidence browsing |
| `data/` | Dataset documentation, reviewed demo data, and local raw/processed files |
| `infra/` | Docker, Compose, ingress, and deployment implementation |
| `scripts/` | Repository checks and future reproducible maintenance commands |
| `docs/` | Setup, contracts, architecture decisions, and delivery plan |
| `design/` | Original UI assets, design exports, and their credits |
| `presentation/` | Pitch material, screenshots, demo script, and source credits |
| `.github/` | Repository checks, issue templates, PR template, and code owners |

Python and frontend dependencies will be owned by their respective directories. A root JavaScript workspace or additional monorepo framework is not required for the current scope.

## Target implementation

- **Backend:** Python 3.12, FastAPI, `backend/app/main.py`, `app.main:app`, port `8000`.
- **Frontend:** Vue 3, TypeScript, Vite, npm, committed `package-lock.json`, output `frontend/dist/`.
- **API:** same-origin `/api`; health endpoints `/api/health/live` and `/api/health/ready`.
- **Data:** SQLite and a versioned, source-linked NASA demo corpus. Generated state stays outside Git.
- **AI:** disabled by default; a free API is enabled only after its model, quota, and failure behavior are verified. The current LLM budget is **USD 0**, with no paid fallback.
- **Deployment:** frontend on Vercel and API/SQLite on the VPS, as selected by the team.
  The API hostname, HTTPS and ingress are configured. The frontend includes the
  Vercel `/api` rewrite and SPA routing configuration; the public frontend and its proxied readiness are available at flareledger.fun.

The [technical contract](docs/TECHNICAL_CONTRACT.md) separates implemented commands from planned interfaces. Public project material uses English under the [language decision](docs/adr/0002-public-language.md).

## Scientific scope

Original values, units, source identifiers, missing values, and measurement limitations must remain visible. Liquid droplets, solid samples, smoke measurements, and historical incidents have different meanings. A chart or generated explanation must preserve those distinctions.

This is an independent hackathon project. NASA has not reviewed or endorsed FlareLedger or its generated conclusions.

## Working together

`main` is the shared integration branch. Use short-lived branches such as `feat/backend-health`, `feat/frontend-shell`, `infra/docker-ci`, or `docs/demo-script`, then open a pull request against `main`. See [CONTRIBUTING.md](CONTRIBUTING.md) for the commands and review process.

| Team member | Project responsibility |
| --- | --- |
| Denis / [Denofix](https://github.com/Denofix) | Team lead, AI integration, architecture, repository ownership |
| Timofey [Tymofii1912](https://github.com/Tymofii1912) | Infrastructure, Docker, CI, and deployment coordination |
| Sayat / [sayat228](https://github.com/sayat228) | Software development, AI integration, and application security |
| Ivan | UI/UX, graphic design, and presentation design |

Confirm task ownership and availability in the team before assigning implementation work. Additional code owners will be registered after their GitHub accounts and access are confirmed.

## License and attribution

Project code and original project documentation are licensed under the [MIT License](LICENSE). NASA datasets, publications, images, logos, and other third-party materials retain their own terms. See [DATA_LICENSES.md](DATA_LICENSES.md) before adding or redistributing source material.
