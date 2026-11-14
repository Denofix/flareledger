# Backup and recovery

Scope: the FlareLedger SQLite state on the VPS. The corpus under data/demo is in Git
and is not part of the backup, but every snapshot records which corpus it belongs to.
Last verified on 14 November 2026 with application commit 8be005f.

## What a snapshot is

Each snapshot is one directory, flareledger-daily-YYYYMMDDTHHMMSSZ-xxxxxxxx (or
flareledger-pre-update-...), containing:

| File | Purpose |
| --- | --- |
| flareledger.sqlite3 | Consistent copy made with the SQLite backup API, including committed WAL data |
| manifest.json | Corpus version and counts, application checkout SHA, image tag and image ID, database SHA-256 |
| seed-reference.json | The corpus manifest the database was imported from |
| SHA256SUMS | Checksums of the three files above |

Creation fails, and nothing is kept, unless SQLite integrity_check passes, the corpus
metadata and entity counts match, every measured point is present, and the seed
manifest matches the database. The same offline verification runs again on the
laptop and before every restore. It does not need the API or Docker.

The manifest ties a snapshot to its image tag. To restore, the same image tag must
exist and the checkout must carry the same data/demo corpus.

## Automatic backup on the VPS

scripts/backup_production.py runs on the Docker host. It runs scripts/backup_sqlite.py
inside the API container, copies the result out of the Docker volume, writes the
manifest and checksums, verifies the snapshot, moves it into place atomically, removes
the temporary file from the volume and keeps the newest 7 snapshots of each kind.
Older snapshots of the same kind are the only thing it ever deletes. A lock prevents
two backups from running at once.

Results: /var/backups/flareledger/snapshots/backup.log (one JSON line per run) and
last-success-daily.json / last-success-pre-update.json, whose created_at shows how
old the newest good snapshot is.

Install once (systemd units are in [infra/systemd](../infra/systemd)). The unit files
assume user tymofii and the checkout /home/tymofii/flareledger; edit them otherwise.

```sh
sudo install -d -o tymofii -g tymofii -m 700 /var/backups/flareledger/snapshots
sudo install -m 644 infra/systemd/flareledger-backup.service infra/systemd/flareledger-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now flareledger-backup.timer
sudo systemctl start flareledger-backup.service
systemctl status flareledger-backup.service --no-pager
systemctl list-timers flareledger-backup.timer
```

The timer runs daily at 03:10 UTC, with Persistent=true so a missed run happens after
a reboot. Before every API update, take a snapshot of the running version first:

```sh
cd ~/flareledger
python3 scripts/backup_production.py --dest /var/backups/flareledger/snapshots --kind pre-update
```

## Copy outside the VPS

The off-VPS copy is pulled by the team's laptop over SSH, the same way the QResto
backups are pulled. The VPS holds no credentials for the laptop. On the laptop
(Windows PowerShell, with the existing SSH key and scp):

```powershell
powershell -File scripts\pull-backup.ps1
```

It finds the newest daily snapshot, copies it into a temporary folder, checks the
file set, SHA256SUMS and manifest (plus the full offline verification when Python is
installed), then moves it to Documents\FlareLedger-backups and keeps the newest 7.
Use -Kind pre-update for pre-update snapshots. Run it at least once a day while the
API is needed, and always before the VPS lease ends. A copy on the same server is not
disaster recovery, and a single laptop is a single copy: add a second private location
if the data matters beyond the demo.

Never commit snapshots, databases or logs. Snapshots contain the full database.

## Restore into a separate project

scripts/restore_snapshot.py restores a snapshot into the Compose project
flareledger-restore with its own state volume, no published port and no ingress
network, so the live API is not touched. It needs Docker, a checkout of the
snapshot's application SHA (the data/demo corpus must match) and the snapshot's image
tag, either already built or built from that checkout with docker compose build api.

From a computer with Docker, restoring a pulled snapshot:

```sh
git clone https://github.com/Denofix/flareledger.git && cd flareledger
git checkout --detach <checkout_sha from manifest.json>
IMAGE_TAG=<tag from manifest.json> docker compose -f compose.yaml build api
python3 scripts/restore_snapshot.py /path/to/flareledger-daily-<stamp> --cleanup
```

Expected output ends with OK lines for ready, corpus_version, investigations, records,
trial_rows, series and points, then RESTORE_OK. For the current corpus those are
10 investigations, 1132 records of which 647 are trial_row, 6 series and 1844 points.
The script compares the restored API with the verified snapshot and exits non-zero on
any difference. --cleanup removes only the flareledger-restore containers, network and
volume afterwards; omit it to inspect the restored API. The project name must start
with flareledger-restore.

## Recover the live service

Replacing the live database is not scripted and has not been rehearsed; only the
separate-project restore above is verified. If the live volume is lost, the safest
path is:

1. Pull or locate the newest verified snapshot and run
   python scripts/snapshot_tools.py verify on it.
2. Check out its application SHA and build or select its image tag.
3. Rehearse with restore_snapshot.py without --cleanup and confirm the counts.
4. Stop only the FlareLedger API: docker compose -f compose.yaml -f compose.prod.yaml stop api.
5. Rename nothing and delete nothing. Create a new state volume by the same copy step
   as restore_snapshot.py (flareledger.sqlite3 into /app/state, owner 10001), point
   the live project at it, and keep the old volume until the new one is proven.
6. Start the API, check the counts above, then check
   https://api.flareledger.fun/api/health/ready from outside.

Never run docker compose down -v or system prune against the live project.
A snapshot restored into a read-only directory fails with 503 because a WAL-mode
database needs a writable directory; the restore script uses the writable state volume.

## VPS lease

The VPS lease ends on 1 December 2026; the exact hour is not yet confirmed. Plan
around the earlier of that date and the confirmed time, and record the confirmed time
here once known.

Migration order if the API must keep running elsewhere:

1. Pull a fresh snapshot to the laptop and verify it.
2. On the new host, clone the repository at the snapshot's application SHA and
   build the image.
3. Run scripts/restore_snapshot.py there, then restore into the live project's volume.
4. Point api.flareledger.fun at the new host (A record), obtain a certificate, and
   configure ingress as in [the production runbook](../infra/proxy/PRODUCTION.md).
5. Verify ready and the counts, update the Vercel rewrite target if the hostname
   changes, and only then stop the old API.

If the API will not be moved, pull the last snapshot before the shutdown, keep the
repository (the corpus is in Git), and note that the public API will be unavailable.

## Checks

python scripts/test_snapshots.py tests verification, tampering detection, retention
and the restore project-name guard with synthetic databases (no NASA data); it runs in
the infrastructure workflow. The end-to-end backup, laptop pull and restore were
exercised against the real database on the VPS on 14 November 2026. Scheduled runs
and the first systemd execution are recorded in INFRA_STATUS.md once observed.
