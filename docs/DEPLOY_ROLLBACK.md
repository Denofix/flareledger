# Deploy, rollback and monitoring

Scope: the FlareLedger API on the VPS (Compose project flareledger, compose.yaml plus
compose.prod.yaml). The frontend is deployed by Vercel and rolled back there. Denis confirmed frontend
commit 1d258c9 from main at https://flareledger.fun/ (primary) and
https://flareledger.vercel.app/ (Vercel alias). The backend image revision is independent.

## Principles

- Every deploy or rollback names an explicit commit. The commit must be part of
  origin/main, so only reviewed code can be released. Branch names and tags such as
  main or latest are refused.
- The script prints the running image and the target image before it acts, and acts
  only when --execute is given. Without it the command is a plan.
- A release never changes the corpus or the database file. By default the post-checks
  require the same corpus version, counts and measured points as before.
- If a post-check fails, the script returns to the previous image on its own and
  repeats the checks. Exit code 1 means refused or returned; exit code 2 means the
  return failed too and a person must recover (the pre-update snapshot is named in
  the message).

## Where the scripts run

Run them from the tooling checkout (/home/tymofii/flareledger-ops, kept on main with
git pull --ff-only), not from the application checkout they manage
(/home/tymofii/flareledger). The managed checkout must have no uncommitted changes.
The tooling checkout supplies the pre-update backup script.

```sh
cd ~/flareledger-ops
python3 scripts/deploy_production.py status
python3 scripts/deploy_production.py plan --revision <sha>
python3 scripts/deploy_production.py deploy --revision <sha> --execute
python3 scripts/deploy_production.py rollback --revision <sha> --execute
```

status shows the running image and revision, whether the application checkout
matches it, readiness, certificate days left, the neighbouring sites and the age of
the last backup. It exits non-zero if any of these is bad.

## What deploy does

1. Resolves the commit, requires it to be on origin/main, shows current and target.
2. Pre-checks: local and public readiness agree, certificate valid, QResto and Feloza
   answer 200. A failure refuses the release before anything is changed.
3. Takes a pre-update snapshot (see [backup and recovery](BACKUP_RECOVERY.md)).
4. Checks out the commit, builds the image flareledger-api:<7-character SHA> if it is
   missing and recreates only the api container.
5. Post-checks: ready, unchanged corpus and counts, overlapping catalogue reads
   (any 5xx fails, which would have caught the concurrency fault fixed in PR 8),
   QResto and Feloza, certificate.
6. On failure returns to the previous image without rebuilding and checks again.

rollback is the same without the build: the target image must already exist on the
host (older images are kept). Use it to go back to a known revision, for example
rollback --revision <previous sha> --execute. Results are appended to
/var/backups/flareledger/snapshots/deploy.log as JSON lines.

If a release changed the database schema, rolling the image back is not enough:
restore the matching pre-update snapshot first. Releases that intentionally change the
corpus use --allow-corpus-change, which then requires only that the API is ready.

## Monitoring

scripts/monitor_production.py checks the frontend HTML application shell and HTTPS
certificate at https://flareledger.fun/, plus /api/health/ready through that origin.
The proxied corpus_version must equal the directly queried API version. A 200 SPA
HTML response on the readiness path fails. --web-url selects another frontend
origin for a one-off check; the production default remains the primary domain.
The monitor never calls /api/ask: its current 503 llm_unavailable is expected, and
monitoring must not consume future LLM quota.

It also checks direct API readiness (HTTP 200 and status ready), a round of
catalogue reads and the certificate (failure under 10 days left, warning under 21).
Each run tries three times, one minute apart, and fails only if all attempts fail, so
one blip does not alert.

| Where | What | How you see a problem |
| --- | --- | --- |
| GitHub Actions, every 30 minutes (.github/workflows/production-monitor.yml) | Frontend page/TLS, proxied readiness/corpus agreement, direct API readiness and certificate; read-only requests, no secrets | The failed workflow run, with GitHub's own notification to the people watching Actions |
| VPS, every 30 minutes (flareledger-monitor.timer) | The same plus the age of the newest daily snapshot (limit 26 hours) and free disk (limit 10%) | systemctl --failed, journalctl -u flareledger-monitor.service |

There is no chat or e-mail channel for the VPS-side check yet. Choose one before
relying on it for judging day (for example a chat webhook or a mail relay) and add it
as OnFailure= on the monitor service. Scheduled GitHub workflows pause after 60 days
without repository activity.

Install the VPS monitor like the backup timer:

```sh
cd ~/flareledger-ops && git pull --ff-only
sudo install -m 644 infra/systemd/flareledger-monitor.service infra/systemd/flareledger-monitor.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now flareledger-monitor.timer
sudo systemctl start flareledger-monitor.service
```

## Checks

python scripts/test_deploy.py tests the release logic with in-memory Docker and HTTP
fakes and a real temporary git repository: refusal of commits outside origin/main,
non-commit revisions, uncommitted changes and failed pre-checks (nothing changed, no
backup); backup before build before restart; return to the previous image after a
failed post-check or a failed restart; manual-recovery reporting when the return
fails; rollback without a build; and the monitor thresholds and retry rule. It runs in
the infrastructure workflow. See [INFRA_STATUS.md](INFRA_STATUS.md) for what has and
has not been exercised on the server. The overlapping-read check was shown to work on the
real server: the deliberate rollback to the revision before PR 8 failed it and the script
returned to the newer image on its own.
