# Development roadmap

Updated 17 November 2026. FlareLedger continues as an independent project after the hackathon. Team: **Denys Voloshyn and Tymofii Chernoivanov**. Submission and pitch preparation are historical work, not the current product release gate.

## Implemented foundation

- Frozen NASA corpus, explicit checksum-verified import, original source locators and measured series.
- Vue interface for browsing, search, records, sources, numerical plots and quantity-compatible comparison.
- Optional Gemini adapter with bounded context, claim-linked citations and persistent rolling limits.
- Vercel frontend, VPS API/SQLite, CI, monitoring and verified-backup tooling.

Source implementation, a passing test, a Vercel deployment and a running VPS revision are separate evidence. See [release status](RELEASE_STATUS.md) and [the repository review](REPOSITORY_REVIEW_2026-11-17.md).

## Current priorities

| Priority | Work | Acceptance |
| --- | --- | --- |
| P0 | Restore the flame and remove the sidebar scrollbar track | Consistent header/mobile/favicon/README assets; navigation remains scrollable and keyboard-reachable on short screens |
| P0 | Resolve the frontend development dependency advisory | Verified upstream fix or separately reviewed mitigation; no forced framework downgrade or silent audit suppression |
| P1 | Confirm the next release | Review and merge focused changes; identify frontend deployment and VPS revision separately; preserve database and quota history |
| P1 | Resume controlled answer evaluation | Current preflight, one exact question per request, retained receipt and manual semantic review; never turn old-release results into new-release grades |
| P1 | Improve retrieval and source/claim review | Separate independent review questions from development cases; retain source, unit and missing-value boundaries |
| P1 | Verify browser accessibility and responsive navigation | Desktop and mobile keyboard/touch, short-height menu, focus, route reload and disabled/unavailable generation states |
| P2 | Improve source discovery | Review lexical retrieval and the current 20-result search limit; add pagination only with corresponding API/UI checks |
| P2 | Plan hosting continuity | Confirm the operator's VPS lease/renewal and recovery ownership before the recorded 1 December 2026 end date |

## Evaluation and operation boundaries

The 15 development questions and 45 frozen anchors are not an independent scientific benchmark. Full live answer evaluation and independent scientific review remain unfinished. Readiness and citation-format checks do not establish scientific answer correctness.

The runtime budget remains USD 0. No paid fallback, provider-key change, database replacement, quota reset or additional domain purchase is part of the branding/layout cleanup. Runtime credentials remain backend-only. Historical preparation materials are under [presentation](../presentation/README.md) and [docs/submission](submission/FIELD_TEXT.md).
