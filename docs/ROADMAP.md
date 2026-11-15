# Implementation roadmap

Status checked on 15 November 2026. This roadmap distinguishes delivered software,
operator checks and unfinished scientific acceptance. See [release audit](RELEASE_AUDIT.md)
for exact evidence and [team rules](../TEAM_RULES.md) for review requirements.

## Delivered

| Area | State and evidence |
| --- | --- |
| Repository and collaboration | Monorepo, MIT code license, separate data-license notes, protected main and PR review workflow exist |
| Backend and corpus | FastAPI, explicit checksum-verified importer, SQLite, health routes, investigations, records, sources and six measured series implemented |
| Frontend | Vue application published at flareledger.fun; catalog, search, source pages, original charts and compatible comparison available |
| Hosting and HTTPS | Frontend on Vercel; API and SQLite on the VPS through the existing shared Nginx and dedicated ingress network; both public readiness routes return 200 / ready |
| Recovery and monitoring | Deploy/rollback, verified snapshots, off-VPS backup, recovery rehearsals, scheduled checks and Telegram incident transitions implemented |
| Gemini Ask | Explicitly enabled in production with gemini-3.6-flash, persistent quotas 10/24h and 3/minute, one active lease, USD 0 and no paid fallback; code defaults remain disabled |
| PR20 | Safe validation-reason diagnostics merged and deployed |
| PR21 | Claim-bound citations and server-rendered markers merged and deployed; earlier diagnostic success is not a grade for the new release |
| PR22 | Scoped evidence retrieval and hash-pinned ReadMe companion merged and deployed at 969cb9460de9115fe0a16016bd02bf168aa7175e |
| Offline acceptance preparation | Fifteen frozen questions and 45/45 source anchors checked without model calls; a separate journal for 969cb94 was prepared |

## Remaining work

| Task | Coordination | Acceptance condition |
| --- | --- | --- |
| Live answer evaluation | Timofey operates the journal; Denis reviews scientific results | Deferred by the operator. All 15 cases currently NOT_RUN. Resume only after an explicit decision and fresh quota preflight; preserve exact questions and receipts |
| Small UI corrections | Timofey, separate PR23 | Review and preview verification before merge; keep the evaluation baseline unchanged during any resumed run |
| Final technical documentation | Timofey | Review this audit/status update and reconcile remaining gaps without claiming scientific completion |
| Demo release and fallback | Timofey with Denis | Agree the exact release, startup procedure, curated screenshots, fallback route and recovery owner; keep a verified backup containing the latest quota history |
| Presentation, speech and submission requirements | Denis with the team | Check the official requirements separately; describe only demonstrated capabilities and visible limitations |
| Hosting continuity | Timofey with Denis | Plan before the VPS lease ends on 1 December 2026; exact shutdown hour remains unconfirmed |

## Evaluation boundary

Live evaluation is currently deferred, not completed or converted into PASS.
NOT_RUN, PENDING_REVIEW and NOT_EVALUABLE must remain visible in any handoff.
An HTTP 200, a matching citation marker, a prepared screenshot or 45 matching source
anchors cannot establish scientific answer quality. If the team elects to present
without the full live run, disclose that limitation explicitly.

Provider/model, public domains, hosting and ingress are selected. No additional
server purchase, billing activation or paid model fallback is authorized by this
roadmap. Keep private configuration on the backend and retain reservation history.
