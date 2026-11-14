# FlareLedger

Explore NASA microgravity combustion research and trace fire safety explanations to their evidence.

FlareLedger is a team project for the **2026 NASA Space Apps Challenge**, addressing [Flame in Freefall](https://www.spaceappschallenge.org/2026/challenges/flame-in-freefall/?tab=resources). The planned workflow is to find an investigation, inspect its test conditions, compare suitable measurements, and read an explanation linked to the original sources.

## Current status

This repository bootstrap contains the monorepo layout, contribution rules, licensing, the reviewed NASA demo seed, technical handoff, and setup instructions. The backend, frontend, data importer, containers, and application CI are the next implementation milestones. Commands for those components are documented as a target contract, not as existing functionality.

The registered project domain is **flareledger.fun**. Hosting, DNS routing, and HTTPS still need to be connected and verified. [Deployment decisions](docs/DEPLOYMENT.md) describe the options.

## Start here

```bash
gh repo clone Denofix/flareledger
cd flareledger
python3 scripts/check_repository.py
```

For a new Ubuntu VM, follow the [Ubuntu and GitHub setup guide in Russian](docs/SETUP_UBUNTU_RU.md). It covers installation, GitHub device-code login, Git identity, invitations, branch rules, and your next tasks.

If you received the starter archive while the remote repository is still empty, follow [initial publication](docs/PUBLISH_BOOTSTRAP_RU.md) first. The included script publishes only the prepared files and refuses to overwrite an existing remote history.

- [Team rules](TEAM_RULES.md)
- [Contribution workflow](CONTRIBUTING.md)
- [Monorepo layout](docs/MONOREPO.md)
- [Backend and frontend contract](docs/TECHNICAL_CONTRACT.md)
- [Implementation roadmap](docs/ROADMAP.md)
- [Domain setup in Russian](docs/DOMAIN_SETUP_RU.md)
- [Data and licensing](DATA_LICENSES.md)

## Repository layout

| Path | Responsibility |
| --- | --- |
| `backend/` | Planned Python 3.12, FastAPI, SQLite, ingestion, retrieval, and optional LLM adapter |
| `frontend/` | Planned Vue 3, TypeScript, Vite, and evidence-aware charts |
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
- **Deployment:** QResto server reuse is a candidate pending an infrastructure review. Vercel frontend hosting is an alternative; purchasing a domain does not choose the application hosting platform.

The [technical contract](docs/TECHNICAL_CONTRACT.md) separates implemented commands from planned interfaces.

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
