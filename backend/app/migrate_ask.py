"""Run explicitly after a backup: python -m app.migrate_ask. Never resets usage."""

from app.ask_store import migrate
from app.config import Settings
from app.storage import Repository


def main() -> None:
    settings = Settings.from_env()
    Repository(settings).readiness()
    migrate(settings.database_path)
    print("ASK_STATE_READY | additive version 1; corpus and existing usage preserved")


if __name__ == "__main__":
    main()
