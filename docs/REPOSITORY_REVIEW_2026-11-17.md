# Repository review — 17 November 2026

Scope: restore the original flame identity, remove the separate visible sidebar scrollbar, reconcile stale repository instructions and identify current check failures. Development continues after the hackathon. Team: **Denys Voloshyn and Tymofii Chernoivanov**.

## Source and deployment evidence

The reviewed main source starts at `cf2e24b823d39272de26ba77607dda7432086cc1` (PR23). Vercel's latest production deployment at inspection is `dpl_Dg8JJRuoZrE8VTmveUZuEjkC6y5t`, READY and linked to that exact frontend source SHA. The account owns `flareledger.fun`; the other projects use verified subdomains of that apex.

Direct API readiness and frontend-proxied readiness both returned HTTP 200 / `ready`, with the frozen corpus version `2026-11-14:90be248ab23b24f6eaa51e3923ba5937631493630fd4833e18a2dbb51897bc52`. Metadata reported 10 investigations, 1,132 records, 6 series and 1,844 points, with generation configured. These GET requests made no model call. They do not expose or independently prove the VPS container's source SHA, current provider allowance or answer correctness. The last operator report for the backend remains `969cb94`; see [release status](RELEASE_STATUS.md).

## Changes

- Restore the original favicon exactly from `969cb94`; use the same flame in all five served SVGs, the mobile/desktop header and README. Retire the orbital F and its visible logo badge. Preserve prior SI assistance and hashes in documentation and Git history.
- Hide only the sidebar's scrollbar track. Keep vertical scrolling, prevent flex items from collapsing and provide a keyboard-focusable navigation region with a visible focus outline. The main page keeps its ordinary scrollbar.
- Reconcile outdated setup, domain, monorepo, container and recovery prose using the useful documentation work from PR24. Keep its operator report explicitly dated and historical. Existing host-specific parameters remain operator-local.
- Use the team's supplied English names consistently. Label old submission and pitch drafts as historical preparation rather than current development gates.
- Keep the full dependency audit blocking; move it after behavioral/build checks so its failure does not obscure their results. Record the unresolved Picomatch development advisory separately.

## Checks

| Check | Result |
| --- | --- |
| Backend tests | 163 passed; existing Starlette/httpx deprecation warning |
| Backend Ruff / formatting / mypy | Passed; 25 formatted files and 14 checked source files |
| Frontend tests | 44 passed |
| Frontend typecheck, ESLint and build | Passed |
| Infrastructure unit scripts | 100 passed across backup, snapshot, replacement, cleanup, deployment, locking and alert tests |
| Offline retrieval inspection | 15 questions and 45/45 frozen anchors passed; zero HTTP/model requests and zero scientific grades |
| Repository metadata and asset integrity | Passed; all five SVG hashes and all 66 original screenshot hashes verified |
| Production frontend dependency audit | Passed; zero reported advisories |
| Full frontend dependency audit | **Blocked** by the development-only Picomatch chain; [details](DEPENDENCY_SECURITY.md) |
| Docker and container integration | Not executed locally: Docker is unavailable in this environment; GitHub CI remains the execution path |
| Browser layout | Local Chromium could not launch because the runtime denies its process-singleton socket. A separate browser preview check is recorded below when available |

Original corpus, hash-pinned ReadMe, evaluation fixture and screenshot bytes are preserved. No backend schema, quota policy, runtime credential, DNS assignment or database was changed. No live Ask was submitted. Offline source-anchor coverage is not a scientific answer score.

## Remaining work and integration

Review the preview and browser evidence, resolve the blocking development dependency finding and obtain the other team member's review before squash merge. Vercel can then build from main; confirm the served flame, navigation and same-origin API after promotion. These static changes do not require a VPS update or migration.

PR24's useful runbook corrections are incorporated here; after this PR is reviewed and merged, reconcile or close the older overlapping documentation PR rather than merging stale README/roadmap text over the result. Dependabot PR1/2 remain separate dependency reviews, not automatically approved work.

Scientific evaluation remains unfinished. Resume it only as a deliberate task with fresh deployment/preflight evidence and retained receipts. Before the recorded 1 December VPS lease end, the operator should confirm continuity and a recoverable off-host backup containing current usage history.
