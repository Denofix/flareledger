"""Linux cross-process contention and inherited backup lock regression tests."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import operation_lock
import backup_production as backup
import deploy_production as deploy


@unittest.skipUnless(sys.platform == "linux", "host operation locks use Linux flock")
class LockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)

    def child(self, code, handle=None, project="flareledger", fd=None):
        return subprocess.run(
            [sys.executable, "-c", code, str(self.path), project, str(fd if fd is not None else handle.fileno() if handle else -1)],
            cwd=Path(__file__).resolve().parent, capture_output=True, text=True,
            pass_fds=(handle.fileno(),) if handle else (), timeout=10,
        )

    def test_deploy_blocks_scheduled_backup_in_another_process(self):
        with deploy.lock(self.path):
            code = "import backup_production as b,sys; sys.exit(b.main(['--dest',sys.argv[1]]))"
            result = self.child(code)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("Another backup, deploy or database operation", result.stderr)

    def test_backup_blocks_deploy_and_database_operation(self):
        for code in (
            "import deploy_production as d,sys; from pathlib import Path; d.lock(Path(sys.argv[1])).__enter__()",
            "import operation_lock as l,sys; from pathlib import Path; l.acquire(Path(sys.argv[1]),sys.argv[2])",
        ):
            with backup.lock(self.path):
                result = self.child(code)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Another backup, deploy or database operation", result.stderr)

    def test_inherited_nested_backup_does_not_deadlock_or_release_parent(self):
        with deploy.lock(self.path) as handle:
            code = "import backup_production as b,sys; from pathlib import Path; b.lock(Path(sys.argv[1]),sys.argv[2],int(sys.argv[3])).close()"
            result = self.child(code, handle)
            self.assertEqual(result.returncode, 0, result.stderr)
            blocked = self.child("import operation_lock as l,sys; from pathlib import Path; l.acquire(Path(sys.argv[1]),sys.argv[2])")
            self.assertNotEqual(blocked.returncode, 0)
        with operation_lock.acquire(self.path, "flareledger"):
            pass

    def test_another_project_is_independent_and_wrong_inherited_lock_is_refused(self):
        with deploy.lock(self.path) as handle:
            result = self.child("import operation_lock as l,sys; from pathlib import Path; l.acquire(Path(sys.argv[1]),sys.argv[2]).close()", project="test-project")
            self.assertEqual(result.returncode, 0, result.stderr)
            with operation_lock.acquire(self.path, "test-project"):
                rejected = self.child("import operation_lock as l,sys; from pathlib import Path; l.acquire(Path(sys.argv[1]),sys.argv[2],int(sys.argv[3]))", handle, "test-project")
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("another project/directory", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
