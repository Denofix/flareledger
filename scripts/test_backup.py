"""Exercise the backup utility on disposable databases, including an active WAL."""

import os
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


BACKUP = Path(__file__).with_name("backup_sqlite.py").resolve()


class BackupTests(unittest.TestCase):
    def run_backup(self, source):
        return subprocess.run(
            [sys.executable, str(BACKUP)],
            env={**os.environ, "DATABASE_PATH": str(source)},
            capture_output=True,
            text=True,
            check=False,
        )

    def test_missing_database_does_not_create_one(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "missing.sqlite3"
            result = self.run_backup(source)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(source.exists())
            self.assertFalse((source.parent / "backups").exists())

    def test_active_wal_is_included_and_source_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "state.sqlite3"
            with closing(sqlite3.connect(source)) as writer:
                writer.execute("PRAGMA journal_mode=WAL")
                writer.execute("PRAGMA wal_autocheckpoint=0")
                writer.execute("CREATE TABLE corpus (version TEXT)")
                writer.execute("INSERT INTO corpus VALUES (?)", ("verified-v1",))
                writer.commit()
                self.assertTrue(Path(str(source) + "-wal").is_file())
                result = self.run_backup(source)
                self.assertEqual(result.returncode, 0, result.stderr)
                destination = Path(result.stdout.splitlines()[0])
                self.assertNotEqual(source, destination)
                with closing(sqlite3.connect(destination)) as restored:
                    self.assertEqual(
                        restored.execute("SELECT version FROM corpus").fetchall(),
                        [("verified-v1",)],
                    )
                self.assertEqual(writer.execute("SELECT COUNT(*) FROM corpus").fetchone(), (1,))


if __name__ == "__main__":
    unittest.main()
