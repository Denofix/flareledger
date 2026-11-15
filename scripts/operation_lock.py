"""One Linux host lock per Compose project for backup, deploy and DB replacement.

All commands must use the same snapshots directory. A nested backup inherits the
parent's locked descriptor via pass_fds; it never skips locking on a bare flag.
Do not unlink lock files: another process may still hold their inode.
"""

from __future__ import annotations

import os
import re
from pathlib import Path


def acquire(directory: Path, project: str, inherited_fd: int | None = None):
    import fcntl

    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", project):
        raise ValueError("Invalid Compose project name for operation lock")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = directory / f".operation-{project}.lock"
    if inherited_fd is None:
        handle = path.open("a")
    else:
        expected, inherited = path.stat(), os.fstat(inherited_fd)
        if (expected.st_dev, expected.st_ino) != (inherited.st_dev, inherited.st_ino):
            raise OSError("Inherited operation lock belongs to another project/directory")
        handle = os.fdopen(os.dup(inherited_fd), "a")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise OSError(f"Another backup, deploy or database operation holds {path.name}") from None
    return handle
