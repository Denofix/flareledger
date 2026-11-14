# Infrastructure status

Owner: Timofey. Updated 14 November 2026. Each line states what was actually
verified; planned work is labelled as such.

## Deployed

| Item | State | Evidence |
| --- | --- | --- |
| API on the VPS | Running application commit 8be005f (image flareledger-api:8be005f) | /api/health/ready returns 200 with status ready; corpus 2026-11-14:90be248a... |
| Compose project | flareledger, compose.yaml plus compose.prod.yaml, checkout /home/tymofii/flareledger | API is the only service; no host port is published |
| Corpus import | Explicit python -m app.ingest, run once | 10 investigations, 1132 records (647 trial_row), 6 series, 1844 points |
| SQLite state | Named volume flareledger_app_state; corpus mounted read-only | State survived recreating the API container and the update from bc4c681 to 8be005f |
| DNS | api.flareledger.fun A record to the VPS | Public DNS resolves; no AAAA record |
| HTTPS | Existing QResto Nginx, certificate issued by the existing Certbot | Public TLS validates; HTTP redirects with 308; scoped renewal dry-run passed |
| Ingress | Nginx attached to the external network flareledger_ingress, alias flareledger-api | Persisted in the host edge.yml override; backup of the previous file kept on the host |
| QResto and Feloza | Unchanged | qresto.cfd and feloza.pl return 200 after each change |
| Concurrent catalog reads | 60 parallel external requests after 8be005f | Only 200 and expected JSON 404 responses |

The LLM is disabled and the budget is USD 0. Ask returns a structured 503.

## Backup and recovery

| Item | State |
| --- | --- |
| Verified snapshot script and offline verification | Implemented; tested against the real database on the VPS |
| Retention | Newest 7 snapshots per kind (daily, pre-update) |
| Daily systemd timer | Enabled on the VPS on 14 November 2026 (flareledger-backup.timer, 03:10 UTC, tooling checkout /home/tymofii/flareledger-ops at main 2d8e60c). First run by systemd succeeded at 21:10 UTC (BACKUP_OK, exit 0); the next scheduled run is 15 November about 03:11 UTC and its result is not yet observed |
| Copy outside the VPS | Pulled by the team laptop with scripts/pull-backup.ps1; verified end to end |
| Restore from the off-VPS copy | Verified on 14 November 2026 from a fresh clone of this branch: tooling checkout plus a separate worktree at the snapshot revision (8be005f, which has no recovery scripts), restoring the copy pulled to the laptop into a new project and volume: ready, 10 investigations, 1132 records (647 trial_row), 6 series, 1844 points. Refusals checked: wrong snapshot path and wrong application checkout both stop before any Docker command; the volume list was identical before and after |
| Live database replacement | Scripted (scripts/replace_database.py: verify, safety backup, swap inside the volume with the previous file kept, checks, automatic return, rollback command) and rehearsed on 14 November 2026 on a separate project and volume: tampered snapshot refused, other corpus refused, valid replacement, rollback byte-identical, rejected corpus change rolled back automatically. Not yet run against the live project |
| Second off-site location | Not configured |
| Snapshot made by the timer's service | Pulled to the laptop with scripts/pull-backup.ps1 and restored from that copy (fresh worktree at the snapshot revision, tooling from main): ready, 10 investigations, 1132 records (647 trial_row), 6 series, 1844 points; live volumes unchanged |

See [backup and recovery](BACKUP_RECOVERY.md).

## Not done

- Frontend, and the Vercel rewrite of /api to https://api.flareledger.fun plus any CORS policy.
- Application CI for the frontend; the backend and infrastructure workflows run.
- Explicit deploy and rollback commands, pre/post-update checks, external monitoring
  of readiness and TLS, and alerting when the newest successful backup is too old.
- Confirmed shutdown time. The VPS lease ends on 1 December 2026; the exact hour is
  not confirmed.
- Independent scientific review of the corpus.

## Validation in CI

The infrastructure workflow validates Compose configuration, the SQLite backup
utility, snapshot verification and retention, Caddy and Nginx routing with disposable
fixtures, and the production Compose boundary. It does not verify the deployed
server, public certificates, application behaviour or scientific data.
