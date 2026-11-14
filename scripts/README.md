# Repository scripts

Run the currently implemented check from the repository root:

```bash
python3 scripts/check_repository.py
```

It checks tracked text files, JSON syntax, Markdown relative file links, and conflict markers. It has no third-party Python dependencies.

Backup and recovery tools, described in [backup and recovery](../docs/BACKUP_RECOVERY.md):

| Script | Where it runs | Purpose |
| --- | --- | --- |
| backup_production.py | VPS host | Verified SQLite snapshot with manifest, checksums and retention |
| pull-backup.ps1 | Windows laptop | Pull and verify the newest snapshot off the VPS |
| restore_snapshot.py | Any Docker host | Restore into a separate Compose project and verify it |
| snapshot_tools.py | Anywhere | Shared verification; `verify DIRECTORY` checks a snapshot offline |
| test_snapshots.py | CI, local | Tests verification, tampering detection and retention |
| replace_database.py | VPS host | Replace the running API's database from a verified snapshot, with rollback |
| rehearse_replace.py | Any Docker host | Rehearse replacement and rollback on a separate project and volume |
| test_replace.py | CI, local | Tests the swap scripts for real and the replacement flow with a fake Docker host |
