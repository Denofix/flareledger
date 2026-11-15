# Technical release audit

Checked on 15 November 2026. Owner: Timofey. This records technical evidence for
the deployed application and the limits of that evidence. It is not scientific
acceptance, a full penetration test or confirmation of submission-rule compliance.
Denis owns the presentation and the separate submission-rule review.

## Release and runtime

| Item | Observed state |
| --- | --- |
| Backend | `969cb9460de9115fe0a16016bd02bf168aa7175e`, image `flareledger-api:969cb94`; checked through the managed checkout and running container |
| Frontend | https://flareledger.fun/ and https://flareledger.vercel.app/; the initial publication SHA is not a current source attestation |
| API | https://api.flareledger.fun; direct and frontend-proxied readiness both HTTP 200 / `ready` |
| Corpus | `2026-11-14:90be248ab23b24f6eaa51e3923ba5937631493630fd4833e18a2dbb51897bc52`; 10 investigations, 1,132 records including 647 trial rows, 6 series and 1,844 points |
| Source companion | `data/ask-context/69f32647792f54ab2a561e3cdafc6c87d854564fe487aed2b09265286bd84e1d.docx`; verified in the API's `/app/data` mount, 21,538 bytes and matching SHA256; text retrieval exercised without a model call |
| Ask | `gemini-3.6-flash`, explicitly enabled; persistent limits 10/rolling 24h, 3/rolling minute and one active lease; USD 0, no billing activation or paid fallback |
| Operational checks | Backup and monitor timers enabled; public `/api/meta` reports generation configured; read-only `app.ask_status` reports migrated state and no active lease at inspection |

The API revision was independently read from the deployment. The public frontend
does not expose its source SHA; this audit does not infer it from the backend SHA.
Readiness and `ready_to_attempt_generation` do not contact Google or prove current
provider access, remaining provider quota or scientific answer quality.

## Verification evidence

The frozen main release has successful GitHub Actions runs for
[backend](https://github.com/Denofix/flareledger/actions/runs/43754960308),
[frontend](https://github.com/Denofix/flareledger/actions/runs/43754960269),
[infrastructure](https://github.com/Denofix/flareledger/actions/runs/43754960273)
and [repository checks](https://github.com/Denofix/flareledger/actions/runs/43754960379).
The [scheduled readiness/TLS check](https://github.com/Denofix/flareledger/actions/runs/43759259261)
also passed. These links describe that release, not future PR checks.

Local validation on the same application baseline:

- Backend review: Python 3.12, Ruff check/format, mypy and 163 tests passed for
  PR22; the merged application tree was checked against the reviewed changes.
- Local-startup rehearsal: explicit corpus import into a new temporary database,
  followed by FastAPI readiness HTTP 200. Generation was disabled, credentials
  absent and container network disabled. The committed data was mounted read-only.
- Frontend: typecheck, lint, 34 tests and production build passed; Node 24 is the
  supported runtime. `npm audit` reported zero advisories on this date.
- Infrastructure: 100 Linux unit tests passed: backup 2, snapshots 18, replacement
  29, rehearsal ownership 6, deploy/monitor 32, cross-process locks 4 and alerts 9.
  These isolated tests had no network or production Docker access. Disposable
  Caddy/Nginx routing and image builds are separately covered by the linked CI.
- Development Compose validation and all ten production-isolation checks passed
  without starting services. Source corpus is read-only, SQLite has its own volume
  and the production API has no published host port.
- Repository structure checks and local Markdown file links passed. A narrow scan
  for obvious credential literals found none; tracked environment files are empty
  examples. This is not a comprehensive secret-history or security audit.

The backend Docker base uses the version tag `python:3.12-slim`, not a pinned
digest. Successful build checks do not establish byte-for-byte image
reproducibility across future upstream base-image updates.

## Interface review

Browser checks covered all ten investigation pages, all six measured series,
catalog filters, evidence search, record/source pages, comparison of two/four
compatible series, rejection of incompatible quantities, source-point selection,
chart enlargement and nested-page reload. Desktop and 360/390/768/1024 px layouts
were inspected. The team prepared a separate screenshot collection. No live Ask
was submitted for these UI checks.

Known follow-ups are visible in [PR23](https://github.com/Denofix/flareledger/pull/23):
missing-acronym fallback, stable labels, mobile skip-link and validation messaging.
The original audit predates integration of that PR. Check its current head, review
and merge state before release; a merge does not attest the published frontend by
itself. Its protected Vercel preview was not verified by this audit. Search currently shows at most 20 results without pagination;
the enlarged plot scrolls its numerical Y ticks with the SVG. Chrome/emulated
sizes do not establish Safari/Firefox, real-device touch or full accessibility
coverage. External NASA/DOI availability was not revalidated by this audit.

## Scientific evaluation remains open

PR20 added safe validation codes, PR21 added claim-bound citation drafts and PR22
improved scoped context retrieval. All three are merged and deployed. Original
table cells, source IDs, units, qualifiers and missing values were preserved.
Earlier AE-11 diagnostics and successful control calls belong to earlier releases;
they are not transferred as scientific grades for `969cb94`.

A separate local journal for `969cb94` was prepared using the supplied evaluation
package: 15 helper tests passed, all 45 frozen source anchors matched, all 15
contexts were recorded and zero model/API requests were made during preparation.
**All 15 live outcomes are NOT_RUN.** No scientific PASS has been assigned. The
operator has deferred live attempts; they must not be silently resumed by a test,
monitor, screenshot task or documentation change.

If the team resumes evaluation, recheck deployment identity, local/provider
allowance and active lease. Submit only the exact agreed question once, retain
its receipt and perform a semantic source/claim review before continuing. Keep
NOT_RUN, PENDING_REVIEW and NOT_EVALUABLE visible. If the team elects to omit the
full live run, describe scientific answer quality as unvalidated.

## Demo handoff still to confirm

The release is a technical baseline, not final demo approval. Agree the final
revision, curated screenshots and walkthrough with Denis. For local operation use
[backend setup](../backend/README.md) and [frontend setup](../frontend/README.md).
The fallback can demonstrate catalog, sources and charts with generation disabled;
it must not present saved or mock responses as a new live generation. Timofey owns
deployment/recovery using [deploy/rollback](DEPLOY_ROLLBACK.md) and
[backup/recovery](BACKUP_RECOVERY.md).

The PR22 pre-update snapshot was verified and copied off the VPS; its corpus and
nine existing reservation records were preserved through deployment. After any
later live attempts, take and verify a fresh off-VPS backup containing the latest
quota history. Do not restore an older allowance or reset counters. The VPS lease
ends on 1 December 2026; the exact shutdown hour remains unconfirmed.
