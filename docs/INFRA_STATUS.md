# Infrastructure status

Owner: Tymofii. Updated 15 November 2026. Each line states what was actually
verified; planned work is labelled as such.

## Deployed

| Item | State | Evidence |
| --- | --- | --- |
| Frontend on Vercel | Published at https://flareledger.fun/ and https://flareledger.vercel.app/; 1d258c9 was the initial publication reported by Denys, not an assertion of the current frontend SHA | Public HTML and frontend-domain readiness/meta independently checked; readiness is HTTP 200 / ready, original corpus version retained |
| API on the VPS | Running application commit 969cb9460de9115fe0a16016bd02bf168aa7175e (image flareledger-api:969cb94), verified on 15 November 2026 | /api/health/ready returns 200 with status ready; corpus 2026-11-14:90be248a... |
| Compose project | flareledger, compose.yaml plus compose.prod.yaml, checkout $HOME/flareledger | API is the only service; no host port is published |
| Corpus import | Explicit python -m app.ingest, run once | 10 investigations, 1132 records (647 trial_row), 6 series, 1844 points |
| SQLite state | Named volume flareledger_app_state; corpus mounted read-only | Corpus entities, Ask schema and all nine reservation records were unchanged across the PR22 update; state volume was preserved |
| DNS | api.flareledger.fun A record to the VPS | Public DNS resolves; no AAAA record |
| HTTPS | Existing QResto Nginx, certificate issued by the existing Certbot | Public TLS validates; HTTP redirects with 308; scoped renewal dry-run passed |
| Ingress | Nginx attached to the external network flareledger_ingress, alias flareledger-api | Persisted in the host edge.yml override; backup of the previous file kept on the host |
| Shared ingress | Preserved | API-only releases leave the existing Nginx instance running |
| Concurrent catalog reads | 60 parallel external requests after 8be005f | Only 200 and expected JSON 404 responses |

Gemini 3.6 Flash is explicitly enabled on this deployment. The shared limits are
10 reservations per rolling 24 hours, 3 per minute and one active lease; budget
is USD 0 with no paid fallback. Code defaults remain disabled. Read-only preflight
checks configuration and local allowance, not provider availability. The new
15-question journal remains entirely NOT_RUN. See [release audit](RELEASE_AUDIT.md).

## Backup and recovery

| Item | State |
| --- | --- |
| Verified snapshot script and offline verification | Implemented; tested against the real database on the VPS |
| Retention | Newest 7 snapshots per kind (daily, pre-update) |
| Daily systemd timer | Enabled on the VPS (flareledger-backup.timer, 03:10 UTC). The scheduled run on 15 November 2026 completed at 03:11:21 UTC with Result=success and exit 0. Tooling checkout $HOME/flareledger-ops was updated to reviewed main 969cb94 for the PR22 release |
| Copy outside the VPS | Pulled by the team laptop with scripts/pull-backup.ps1; verified end to end |
| Restore from the off-VPS copy | Verified on 14 November 2026 from a fresh clone of this branch: tooling checkout plus a separate worktree at the snapshot revision (8be005f, which has no recovery scripts), restoring the copy pulled to the laptop into a new project and volume: ready, 10 investigations, 1132 records (647 trial_row), 6 series, 1844 points. Refusals checked: wrong snapshot path and wrong application checkout both stop before any Docker command; the volume list was identical before and after |
| Live database replacement | Scripted (scripts/replace_database.py: verify, safety backup, swap inside the volume with the previous file kept, checks, automatic return, rollback command) and rehearsed on 14 November 2026 on a separate project and volume: tampered snapshot refused, other corpus refused, valid replacement, rollback byte-identical, rejected corpus change rolled back automatically. Not yet run against the live project |
| Second off-site location | Not configured |
| Snapshot made by the timer's service | Pulled to the laptop with scripts/pull-backup.ps1 and restored from that copy (fresh worktree at the snapshot revision, tooling from main): ready, 10 investigations, 1132 records (647 trial_row), 6 series, 1844 points; live volumes unchanged |

See [backup and recovery](BACKUP_RECOVERY.md).

## Recovery review fixes

`recover` explicitly supports missing/corrupt SQLite and a stopped API without a
healthy baseline or successful SQLite backup. Remaining database/WAL/SHM files are
preserved. Manual rollback failures attempt to restart the last working state and
otherwise print ROLLBACK_FAILED with recovery locations. The public-check helper
and common operation lock are included. PR12 is merged in main at 3fdd06f; this
branch includes that main and retains deploy, lock and replacement workflow tests.

Validation of these fixes: 29 replacement/lock tests passed in Python 3.12 on Linux;
18 snapshot tests and 2 backup tests passed on the Windows host with Git. API, file
swaps and HTTP were also exercised on a separate local Docker Compose project for
missing, corrupt and stopped cases, plus injected helper and post-check rollback
failures. Host flock was substituted in that Windows rehearsal and tested separately
with real Linux cross-process locks. It did not exercise live ingress, TLS or the VPS.
All test projects and their volumes were removed; no live database was replaced.

Rehearsal cleanup review: each wrapper invocation passes a random ownership token
to restore. Its new container, volume and network receive that label. Cleanup filters
by both project and token and rechecks the owner before individual removals; no
project-wide compose down is used by the wrapper. Partial failed restores can be
cleaned while pre-existing resources remain untouched. Six regression tests cover
refusal, existing volumes, partial creation, later failure, --keep and wrong ownership.

Local Docker verification also exercised the real restore and rehearsal commands:
refusal preserved an existing running container and the exact SQLite bytes; a new
restore passed readiness and corpus-count checks and removed its owned resources;
an injected startup failure removed only that failed run's resources. The combined
Linux replacement, cleanup and operation-lock suite passed 39 tests. These checks
used disposable local projects and did not touch the VPS or production data.

## Deploy, rollback and monitoring

| Item | State |
| --- | --- |
| deploy, rollback, plan and status commands with explicit commit, pre/post-checks and automatic return | Implemented and unit-tested (scripts/test_deploy.py in CI). On the VPS, status, plan and refusal paths were run read-only on 14 November 2026 against the real deployment (running 8be005f, all checks passing). A live rollback to bc4c681 was run on 14 November 2026 at 22:39 UTC: the pre-checks passed, a pre-update snapshot was taken, bc4c681 was started and the overlapping-read post-check failed (22 of 42 requests returned 503, the concurrency fault fixed in PR 8), and the script returned to 8be005f by itself; all checks passed again afterwards and the data was unchanged. Later live success-path deployments completed for PR20, PR21 and PR22; PR22 now runs 969cb94 with unchanged corpus and quota history |
| External monitor (GitHub Actions every 30 minutes) | Enabled; the scheduled run created at 08:00:05 UTC on 15 November 2026 completed successfully ([run evidence](https://github.com/Denofix/flareledger/actions/runs/43692431372)) |
| VPS monitor timer (readiness, certificate, backup age, disk) | Installed and enabled. Telegram drop-in loaded; manual run at 11:29 UTC and scheduled run at 11:30 UTC on 15 November 2026 completed successfully with exit 0 |
| Alert channel for the VPS-side monitor | Agreed private Telegram group. Credentials remain in the server-only mode-600 env file; persistent incident directory is mode 700. Tymofii confirmed receipt of one labelled TEST failure and one TEST recovery; repeated failure was suppressed. Production monitor uses reviewed PR14 pending-event persistence, not the temporary test script |

See [deploy, rollback and monitoring](DEPLOY_ROLLBACK.md).

Review fixes: explicit recovery rollback no longer requires current readiness and
can restart a stopped API. It requires a known-good image/revision and an explicit
expected corpus version. Backup and deploy share one per-project operation lock,
including safe inheritance by nested backup. Regression checks: 32 deploy/monitor
tests, 18 snapshot tests and 2 SQLite backup tests passed locally; 4 additional real
Linux cross-process lock tests passed inside an isolated Python 3.12 container.
These new recovery paths have not yet been run against the live deployment.

Isolated deployment rehearsal on 15 November 2026 used the real reviewed main
tooling (410d82b), local Linux orchestration, Docker Compose and Python 3.12 API
images. Starting from 1d258c9, deploy built the missing 410d82b image and passed
post-checks; explicit rollback returned to 1d258c9. An injected failing post-check
on a subsequent deploy triggered automatic return to the previous image. Finally,
explicit recovery restarted an intentionally stopped API using the existing target
image without requiring a successful backup of the stopped container.

All four paths preserved the state volume, exact SQLite bytes, corpus identity and
counts. Three pre-update snapshots passed offline verification. The nested backup
used the real Linux inherited operation lock. API/catalogue HTTP requests were real
and issued inside the disposable API container; external TLS and neighbouring-site
checks were excluded at the test boundary. This is local release-flow evidence,
not a live deploy, a public-ingress test or evidence about Gemini/schema migration.
The random test Compose project, its network and volume were removed afterwards.

Frontend monitor extension verified externally on 14 November 2026 at 23:06 UTC:
frontend HTML shell, frontend and direct API TLS, readiness through flareledger.fun,
matching corpus_version and all seven direct API read probes passed. The 28 local
deploy/monitor regression tests passed. These were the initial manual checks. The scheduled monitor and VPS timer were
subsequently installed and verified as recorded above.

## Not done

- Full live scientific acceptance of the 15-question set. The prepared journal
  contains 15 NOT_RUN cases; offline context checks are not answer grades.
- Final demo-release approval, curated screenshots and an agreed demo sequence.
- UI follow-ups are tracked in PR23. Check its current head and review/merge state
  before integration; this audit does not attest its publication on the frontend.
- Confirmed shutdown time. The VPS lease ends on 1 December 2026; the exact hour is
  not confirmed.
- Independent scientific review of the corpus.

## Validation in CI

The infrastructure workflow validates Compose configuration, the SQLite backup
utility, snapshot verification and retention, Caddy and Nginx routing with disposable
fixtures, and the production Compose boundary. It does not verify the deployed
server, public certificates, application behaviour or scientific data.
