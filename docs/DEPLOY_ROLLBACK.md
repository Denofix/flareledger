# Deploy, rollback and monitoring

Scope: the FlareLedger API on the VPS (Compose project flareledger, compose.yaml plus
compose.prod.yaml). The frontend is deployed by Vercel and rolled back there. Denys confirmed frontend
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

Run them from the deployment account's tooling checkout (`$HOME/flareledger-ops`,
kept on main with `git pull --ff-only`), not from the managed application checkout
(`$HOME/flareledger`). These are account-relative defaults; keep any installation-
specific account and paths in the private operator inventory. The managed checkout
must have no uncommitted changes.
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
2. Pre-checks: local and public readiness agree, certificates are valid and
   existing ingress services remain reachable. A failure refuses the release.
3. Takes a pre-update snapshot (see [backup and recovery](BACKUP_RECOVERY.md)).
4. Checks out the commit, builds the image flareledger-api:<7-character SHA> if it is
   missing and recreates only the api container.
5. Post-checks: ready, unchanged corpus and counts, overlapping catalogue reads
   (any 5xx fails, which would have caught the concurrency fault fixed in PR 8),
   plus existing shared-service reachability and TLS.
6. On failure returns to the previous image without rebuilding and checks again.

**Generation is disabled by the helper.** Deploy, explicit rollback and automatic
return all create the API with `LLM_ENABLED=false`, even if the private environment
previously enabled Gemini. `DEPLOY_OK` or healthy readiness does not mean generation
was restored. After verifying state and the selected image, follow the explicit
[operator restoration step](AI_SETUP.md#production-handoff-after-pr-review) with
the same database and quota history. Run read-only `app.ask_status` again; no Ask
is needed to confirm configuration. Re-enabling generation is a separate deliberate
operator action, never an automatic retry or counter reset.

rollback is the same without the build: the target image must already exist on the
host (older images are kept). Use it to go back to a known revision, for example
rollback --revision <previous sha> --execute. Results are appended to
/var/backups/flareledger/snapshots/deploy.log as JSON lines.

### Recovery when the current API is down

Normal deploy/rollback still require a healthy baseline. For an unavailable or
stopped API, explicitly use the recovery path and the full corpus version from a
known verified snapshot or release record:

```sh
python3 scripts/deploy_production.py rollback --revision <known-good-sha> \
  --recover --expected-corpus-version '<verified-corpus-version>' --execute
```

This still validates the target commit against origin/main, requires an existing
image and a clean application checkout, checks TLS and neighbouring sites, and
verifies readiness, corpus identity and catalogue reads afterwards. Current API
health is not a precondition. A pre-update backup is attempted, but a failed backup
does not block explicit recovery; the state volume is retained, and no database is
replaced by this command. If local probes work, their counts are also preserved.
The same stopped image can be restarted with this path. An unsuccessful return is
reported as ROLLBACK_FAILED / exit 2, not a healthy recovery.

### Shared operation lock

Backup and deploy/rollback share `.operation-<project>.lock` in the snapshots
directory. Use the same snapshots path for every operation on a project. Do not
unlink the file while operations may run. Nested pre-update backup receives the
parent's locked descriptor via subprocess pass_fds; it cannot bypass the lock
with a standalone skip flag. All tool users, including the scheduled backup,
must use the updated tooling checkout before these commands are enabled.
Database replacement in PR13 must adopt this helper after PR12 is merged; do not
run the old independently locked replacement script alongside the new tools.

If a release changed the database schema, rolling the image back is not enough:
restore the matching pre-update snapshot first. Releases that intentionally change the
corpus use --allow-corpus-change, which then requires only that the API is ready.

## Monitoring

scripts/monitor_production.py checks the frontend HTML application shell and HTTPS
certificate at https://flareledger.fun/, plus /api/health/ready through that origin.
The proxied corpus_version must equal the directly queried API version. A 200 SPA
HTML response on the readiness path fails. --web-url selects another frontend
origin for a one-off check; the production default remains the primary domain.
The monitor never calls /api/ask. Enabled generation, exhausted quota and provider
availability are separate from readiness; monitoring must not consume LLM quota.

It also checks direct API readiness (HTTP 200 and status ready), a round of
catalogue reads and the certificate (failure under 10 days left, warning under 21).
Each run tries three times, one minute apart, and fails only if all attempts fail, so
one blip does not alert.

| Where | What | How you see a problem |
| --- | --- | --- |
| GitHub Actions, every 30 minutes (.github/workflows/production-monitor.yml) | Frontend page/TLS, proxied readiness/corpus agreement, direct API readiness and certificate; read-only requests, no secrets | The failed workflow run, with GitHub's own notification to the people watching Actions |
| VPS, every 30 minutes (flareledger-monitor.timer) | The same plus the age of the newest daily snapshot (limit 26 hours) and free disk (limit 10%) | systemctl --failed, journalctl -u flareledger-monitor.service |

The optional Telegram integration below reports incident transitions. Scheduled
GitHub workflows pause after 60 days without repository activity.

Install the VPS monitor like the backup timer:

```sh
cd ~/flareledger-ops && git pull --ff-only
sudo install -m 644 "${PRIVATE_UNIT_DIR:?Set the adapted unit directory}/flareledger-monitor.service" "$PRIVATE_UNIT_DIR/flareledger-monitor.timer" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now flareledger-monitor.timer
sudo systemctl start flareledger-monitor.service
```

Use private, host-adapted copies of the monitor service/timer and Telegram drop-in;
set `PRIVATE_UNIT_DIR` as in [backup installation](BACKUP_RECOVERY.md#automatic-backup-on-the-vps).
Check account, WorkingDirectory, ExecStart and EnvironmentFile together before
installation. This runbook does not change the installed services.

### Telegram incident and recovery messages

Use the agreed private group and a dedicated bot that can send messages there.
Keep BOT_TOKEN and CHAT_ID only on the VPS in
`$HOME/.config/flareledger/telegram.env` for the deployment account (directory
mode 700, file mode 600, owned by that account). Set the values using a server-side editor. Do not paste them
into Git, terminal commands, logs or chat. The file contains KEY=value lines.

After review and updating the tooling checkout, install the drop-in:

```sh
sudo install -d -m 755 /etc/systemd/system/flareledger-monitor.service.d
sudo install -m 644 "${PRIVATE_UNIT_DIR:?Set the adapted unit directory}/flareledger-monitor-telegram.conf" /etc/systemd/system/flareledger-monitor.service.d/telegram.conf
sudo systemctl daemon-reload
sudo systemctl start flareledger-monitor.service
```

Failure is reported after all monitor retries fail; repeated failures are suppressed,
then recovery is reported when every check passes. A locked persistent state
directory serializes updates. Observed transitions are queued on disk before sending,
separately from confirmed delivery. If an outage ends before Telegram becomes
reachable, the queued failure and recovery are delivered in order on the next run.
Each acknowledgement removes only that event; a failed recovery send does not
repeat the already delivered failure. Existing delivered-state files remain supported.
An ambiguous network timeout or process interruption after delivery can still cause
a duplicate. Exceptions and Telegram response bodies are not logged because URLs
contain the bot token. The implementation uses the official
[sendMessage API](https://core.telegram.org/bots/api#sendmessage).

Verify delivery in a private SSH shell, without tracing, using separate test state:

```sh
set +x
set -a
. "$HOME/.config/flareledger/telegram.env"
set +a
test_state=$(mktemp -d "$HOME/flareledger-alert-test.XXXXXX")
python3 scripts/monitor_alerts.py failure --state "$test_state"
python3 scripts/monitor_alerts.py failure --state "$test_state"
python3 scripts/monitor_alerts.py recovery --state "$test_state"
unset BOT_TOKEN CHAT_ID
```

Expect one TEST FAILURE and one TEST RECOVERED in the group; confirm receipt.
The second failure sends nothing. No production incident state, service or database
is changed. If delivery fails, check bot membership and the private file without
printing its contents.

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
