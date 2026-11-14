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
| deploy_production.py | VPS host | status, plan, deploy and rollback to an explicit commit with checks and automatic return |
| monitor_production.py | GitHub Actions, VPS | Readiness, certificate and backup-age checks with retries |
| deploy_tools.py | Shared | HTTP, TLS and backup-age checks used by the two scripts above |
| test_deploy.py | CI, local | Tests the release logic and monitor rules with fakes |
