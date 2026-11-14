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
| manifest.json | Corpus version and counts, application revision (full SHA), image reference and ID, database SHA-256 |
| seed-reference.json | The corpus manifest the database was imported from, copied from the running container |
| SHA256SUMS | Checksums of the three files above |

Creation fails, and nothing is kept, unless SQLite integrity_check passes, the corpus
metadata and entity counts match, every measured point is present, and the seed
manifest matches the database. The same offline verification runs again on the
laptop and before every restore. It does not need the API or Docker.

The application revision is resolved from the running image's tag (the release tag is
a commit abbreviation), never from whichever folder is checked out, so a rollback or a
moved checkout cannot mislabel a snapshot. If the tag is not a commit SHA, unknown or
ambiguous, the backup fails and logs why; pass --revision with the full SHA instead.
To restore, the snapshot's revision must be available as an application checkout and
the image must exist or be built from it.

## Automatic backup on the VPS

scripts/backup_production.py runs on the Docker host from a tooling checkout that is
kept separate from the checkout the API is deployed from, so rolling the application
back to an older commit never removes the backup scripts. It runs
scripts/backup_sqlite.py inside the API container, copies the result and the container's
seed-reference.json out of the Docker volume, writes the
manifest and checksums, verifies the snapshot, moves it into place atomically, removes
the temporary file from the volume and keeps the newest 7 snapshots of each kind.
Older snapshots of the same kind are the only thing it ever deletes. A lock prevents
two backups from running at once.

Results: /var/backups/flareledger/snapshots/backup.log (one JSON line per run) and
last-success-daily.json / last-success-pre-update.json, whose created_at shows how
old the newest good snapshot is.

Install once (systemd units are in [infra/systemd](../infra/systemd)). The unit files
assume user tymofii and the tooling checkout /home/tymofii/flareledger-ops; edit them
otherwise. Keep that checkout on main and update it with git pull --ff-only.

```sh
git clone https://github.com/Denofix/flareledger.git ~/flareledger-ops
cd ~/flareledger-ops
sudo install -d -o tymofii -g tymofii -m 700 /var/backups/flareledger/snapshots
sudo install -m 644 infra/systemd/flareledger-backup.service infra/systemd/flareledger-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now flareledger-backup.timer
sudo systemctl start flareledger-backup.service
systemctl status flareledger-backup.service --no-pager
systemctl list-timers flareledger-backup.timer
```

The timer runs daily at 03:10 UTC (UTC is written in the unit, so the server timezone
does not matter), with Persistent=true so a missed run happens after a reboot. Before every API update, take a snapshot of the running version first:

```sh
cd ~/flareledger-ops
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

scripts/restore_snapshot.py restores a snapshot into a new Compose project named
flareledger-restore-<random> with its own state volume, no published port and no
ingress network, so the live API is not touched. Run it from a current checkout (it
carries the tooling) and point --project-dir at a checkout of the snapshot's
application revision: that checkout supplies compose.yaml, the corpus under data/ and
the image build. A separate git worktree keeps the tooling and the old revision apart.

The script refuses, before running any Docker command, when the snapshot fails
verification, when --project-dir is not at the snapshot's revision, when the corpus
differs, or when the snapshot records no revision. It also refuses to use a Compose
project or volume that already exists, and --cleanup removes only what that run
created. An unsuccessful or refused run therefore never deletes someone else's project.

From a computer with Docker and a pulled snapshot (Windows users can run the same
commands in WSL or Git Bash):

```sh
git clone https://github.com/Denofix/flareledger.git && cd flareledger
REV=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['application']['revision'])" /path/to/snapshot/manifest.json)
git worktree add ../flareledger-at-snapshot "$REV"
python3 scripts/restore_snapshot.py /path/to/flareledger-daily-<stamp> --project-dir ../flareledger-at-snapshot --build --cleanup
```

--build builds the image from the worktree when it is not already present. The image
name is flareledger-api:<release tag>; Compose takes only the tag as IMAGE_TAG, and the
script does this itself. Do not pass the full image reference as IMAGE_TAG.

Expected output ends with OK lines for ready, corpus_version, investigations, records,
trial_rows, series and points, then RESTORE_OK. For the current corpus those are
10 investigations, 1132 records of which 647 are trial_row, 6 series and 1844 points.
The script compares the restored API with the verified snapshot and exits non-zero on
any difference. Omit --cleanup to inspect the restored API; remove it later with
docker compose --project-name <name> down --volumes. A snapshot taken before the
revision field existed needs --revision <full SHA> after you confirm which release was
running.

## Replace the live database

scripts/replace_database.py puts a verified snapshot into the running API's state
volume. It was rehearsed on a separate project and volume (see below); it has not been
run against the live project, and it should only be used when the live database is
damaged, lost or must be rolled back to a snapshot. Normal releases never touch the
database.

```sh
cd ~/flareledger-ops
python3 scripts/replace_database.py replace /path/to/flareledger-daily-<stamp>
python3 scripts/replace_database.py replace /path/to/flareledger-daily-<stamp> --execute --public-url https://api.flareledger.fun
python3 scripts/replace_database.py rollback --execute --public-url https://api.flareledger.fun
```

Without --execute the command only verifies the snapshot and prints the target
project, container, volume and image. With --execute it:

1. verifies the snapshot offline (checksums, integrity, corpus counts and points) and
   refuses it if its corpus is not the one the running API serves
   (--allow-corpus-change is for a deliberate corpus change only);
2. takes a pre-update snapshot of the current database;
3. stops only the API container (the public API is down for about half a minute);
4. copies the snapshot file next to the live one, checks its SHA-256, moves the live
   file aside as flareledger.sqlite3.replaced-<stamp> (kept, never deleted) and renames
   the new file into place;
5. starts the API and requires it to be ready and to serve exactly the snapshot's
   investigations, records, trial_row records, series and points, and the public URL to
   serve the same corpus version;
6. if the swap or any check fails, stops the API, puts the kept file back and checks
   that the state matches what it was before. A failure to put it back is reported as
   ROLLBACK_FAILED with the safety backup's name.

rollback restores the newest kept file (--stamp chooses another) with the same stop,
restore, start and check. Kept files accumulate inside the volume (about the size of
the database each); remove old ones by hand once they are no longer needed. The tool
cannot judge schema compatibility between releases: it refuses a snapshot with a schema
version the tooling does not know, and a snapshot from a different release than the
running one is the operator's responsibility.

### Rehearsal

scripts/rehearse_replace.py drives the same commands against a new project named
flareledger-restore-rehearsal-<id> with its own volume, no published port and no
ingress, never the live project. Run it from the tooling checkout with --project-dir at
a checkout of the snapshot's application revision, exactly as for restore_snapshot.py:

```sh
git worktree add ../flareledger-at-snapshot <revision from manifest.json>
python3 scripts/rehearse_replace.py /path/to/flareledger-daily-<stamp> --project-dir ../flareledger-at-snapshot
```

It checks that a tampered snapshot is refused with the database unchanged, that a
snapshot of another corpus is refused, that a valid snapshot replaces the database,
that rollback restores the original file byte for byte, and that an accepted
other-corpus snapshot which the API rejects is rolled back automatically. It prints
REHEARSAL_OK only if all six steps pass and removes the rehearsal project afterwards
(--keep leaves it). The variants are built in a temporary folder and never enter the
real snapshot directory.

Rehearsed on the VPS on 14 November 2026 from a fresh clone of this branch with the
snapshot made by the daily timer: all six steps passed, the rehearsal project and
volume were removed, and the live container and the list of Docker volumes were
unchanged.

If the whole volume is lost, create it from a snapshot with the separate-project
restore above, then follow the steps for a new live project in the migration order below.
Never run docker compose down -v or system prune against the live project. A snapshot
placed in a read-only directory fails with 503 because a WAL-mode database needs a
writable directory; the tools always use the writable state volume.

## VPS lease

The VPS lease ends on 1 December 2026; the exact hour is not yet confirmed. Plan
around the earlier of that date and the confirmed time, and record the confirmed time
here once known.

Migration order if the API must keep running elsewhere:

1. Pull a fresh snapshot to the laptop and verify it.
2. On the new host, clone the repository (the current main carries the recovery
   tools) and create a separate application worktree at the snapshot's revision:
   git worktree add ../flareledger-at-snapshot <revision from manifest.json>.
3. From the tooling checkout, run scripts/restore_snapshot.py <snapshot>
   --project-dir ../flareledger-at-snapshot --build, the same command as in the
   restore section above, and confirm the counts. Do not use --cleanup if you want to
   keep the result to inspect. Creating the live project's state volume from the
   verified snapshot is then the unscripted step described under "Recover the live
   service"; do not run the recovery tools from the old revision's checkout, which
   does not contain them.
4. Point api.flareledger.fun at the new host (A record), obtain a certificate, and
   configure ingress as in [the production runbook](../infra/proxy/PRODUCTION.md).
5. Verify ready and the counts, update the Vercel rewrite target if the hostname
   changes, and only then stop the old API.

If the API will not be moved, pull the last snapshot before the shutdown, keep the
repository (the corpus is in Git), and note that the public API will be unavailable.

## Checks

python scripts/test_snapshots.py tests verification, tampering detection, retention
and the restore project-name guard with synthetic databases (no NASA data); it runs in
the infrastructure workflow. The tests cover revision resolution
(the image tag wins over the checked-out folder) and refusals: a wrong snapshot path, a
revision mismatch, an existing restore project and a missing revision all fail with no
destructive Docker command. The end-to-end backup, laptop pull and restore were
exercised against the real database on the VPS on 14 November 2026; they are repeated
for this revision of the tooling in INFRA_STATUS.md. Scheduled runs
and the first systemd execution are recorded in INFRA_STATUS.md once observed.

python scripts/test_replace.py runs the replacement swap and undo scripts for real against
temporary directories and the replacement flow against a fake Docker host: refusal of
tampered snapshots and other corpora, the order backup, stop, swap, start, return to the
previous file after a failed check or swap, the manual-recovery report and the rollback
command. It runs in the infrastructure workflow.
