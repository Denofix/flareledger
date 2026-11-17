"""Paths shared by the importer, read-only corpus API and explicit Ask state."""

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    database_path: Path
    data_dir: Path

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            Path(os.getenv("DATABASE_PATH", str(ROOT / "state/flareledger.sqlite3"))).resolve(),
            Path(os.getenv("DATA_DIR", str(ROOT / "data"))).resolve(),
        )

    @property
    def seed_path(self) -> Path:
        return self.data_dir / "demo/FlareLedger_NASA_Demo_Data.json"

    @property
    def manifest_path(self) -> Path:
        return self.data_dir / "demo/seed-reference.json"
