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
| Browser layout | Passed the scoped Chromium preview review below: restored flame, hidden sidebar track, keyboard/wheel access and narrow-layout navigation |

## GitHub CI and Vercel preview

For application commit `5e52539c5538aac7bdd64406e029baef07f388f8` in [PR26](https://github.com/Denofix/flareledger/pull/26):

- [Backend and image checks](https://github.com/Denofix/flareledger/actions/runs/44142300051) passed.
- [Infrastructure and isolated routing checks](https://github.com/Denofix/flareledger/actions/runs/44142299978) passed.
- [Repository metadata](https://github.com/Denofix/flareledger/actions/runs/44142299912) passed.
- [Frontend job](https://github.com/Denofix/flareledger/actions/runs/44142300194) passed installation, typecheck, lint, tests and production build, then failed at the full dependency audit. Its frontend container build was consequently skipped. The audit gate was not disabled.
- Vercel preview deployment `dpl_9XV6XGEenhBjzERnRNEk8xBmqjhs` reached READY and reports the same source commit.

The production page was visually observed with the previous orbital F. Initial preview inspection reached Vercel Authentication. After Denys explicitly authorized one share link lasting 23 hours, Vercel created a new expiring link for deployment `dpl_A3JyAe4ieMLonQcSxucwgm56cscf`, source `2eadd1a6d786aa4b4c03d351f379c2aaf76f2961`. The reviewed [deployment](https://flareledger-2j9czwvbn-denofix-2940.vercel.app/) then opened successfully. The access parameter is deliberately omitted from this repository. Project-wide Deployment Protection remains enabled; production was not promoted.

## Scoped visual acceptance

Chromium review on 17 November 2026 confirmed:

- The desktop wordmark and mobile flame load correctly; the former visible logo disclosure badge is absent. The favicon points to `/favicon.svg?v=flame`.
- At a CSS viewport of 1363 by 936, the main page retains its scrollbar and the sidebar has no separate visible track.
- In the shorter 909 by 624 CSS viewport, wheel scrolling moves the sidebar to its bottom while the main page remains at scroll position zero. The source-code link remains reachable. PageDown, PageUp and End also scroll the focused sidebar, with a visible keyboard focus outline.
- At CSS widths 545 and 340, the mobile navigation opens. Selecting Measurements closes it and loads the measured-series page. Investigation and measurement views showed no document-level horizontal overflow at the checked widths; the selected measurement chart rendered from the existing data.

Narrow CSS viewports were obtained with ordinary browser zoom (100 to 400 percent), not physical mobile devices or touch emulation. The browser's DevTools policy was left unchanged. No independent Safari/Firefox or real-phone acceptance is implied. The captured console errors were from the browser extension; no application-origin error was observed in the inspected log window.

[Original review screenshots and capture metadata](assets/review-2026-11-17/README.md) preserve the desktop view, narrow header and independently scrolled sidebar. These are genuine application captures, not generated measurements. No live Ask was submitted. The follow-up evidence commit changes documentation and captures only; application code is unchanged from the tested preview.

Original corpus, hash-pinned ReadMe, evaluation fixture and screenshot bytes are preserved. No backend schema, quota policy, runtime credential, DNS assignment or database was changed. No live Ask was submitted. Offline source-anchor coverage is not a scientific answer score.

## Remaining work and integration

The scoped visual preview review is complete. Resolve the blocking development dependency finding and obtain the other team member's review before squash merge. Vercel can then build from main; confirm the served flame, navigation and same-origin API after promotion. These static changes do not require a VPS update or migration.

PR24's useful runbook corrections are incorporated here; after this PR is reviewed and merged, reconcile or close the older overlapping documentation PR rather than merging stale README/roadmap text over the result. Dependabot PR1/2 remain separate dependency reviews, not automatically approved work.

Scientific evaluation remains unfinished. Resume it only as a deliberate task with fresh deployment/preflight evidence and retained receipts. Before the recorded 1 December VPS lease end, the operator should confirm continuity and a recoverable off-host backup containing current usage history.
