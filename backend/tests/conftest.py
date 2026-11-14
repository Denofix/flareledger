import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import ROOT, Settings
from app.ingest import import_corpus
from app.main import create_app


@pytest.fixture(scope="session")
def seed():
    return json.loads((ROOT / "data/demo/FlareLedger_NASA_Demo_Data.json").read_text())


@pytest.fixture(scope="session")
def initialized_database(tmp_path_factory):
    settings = Settings(tmp_path_factory.mktemp("corpus") / "state.sqlite3", ROOT / "data")
    import_corpus(settings)
    return settings.database_path


@pytest.fixture
def settings(tmp_path, initialized_database):
    destination = tmp_path / "state.sqlite3"
    # All writer connections are closed; SQLite has checkpointed the WAL.
    shutil.copyfile(initialized_database, destination)
    return Settings(Path(destination), ROOT / "data")


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as value:
        yield value
