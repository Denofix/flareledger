"""Read-only operator preflight: python -m app.ask_status. Never calls a model."""

import json
import math
import sqlite3
import time
from contextlib import closing
from typing import Any

from app.ask_store import AskStore
from app.config import Settings
from app.llm import SUPPORTED_MODELS, LLMSettings
from app.storage import CorpusUnavailable, Repository


def inspect_status(settings: Settings, config: LLMSettings, now: float | None = None) -> dict[str, Any]:
    now = time.time() if now is None else now
    result: dict[str, Any] = {
        "provider": "gemini" if config.provider == "gemini" else "unsupported",
        "model": config.model if config.model in SUPPORTED_MODELS else "unsupported",
        "enabled": config.enabled,
        "key_present": bool(config.key),
        "generation_configured": config.configured,
        "corpus_ready": False,
        "ask_state_ready": False,
        "ready_to_attempt_generation": False,
        "quota": None,
        "provider_probed": False,
    }
    try:
        result["corpus_version"] = Repository(settings).readiness()["corpus_version"]
        result["corpus_ready"] = True
    except CorpusUnavailable:
        result["reason"] = "corpus_unavailable"
        return result
    if not AskStore(settings.database_path).ready():
        result["reason"] = "ask_state_unavailable"
        return result
    try:
        with closing(sqlite3.connect(settings.database_path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            db.execute("BEGIN")
            version, last_seen = db.execute(
                "SELECT version, last_seen FROM fl_ask_schema WHERE id=1"
            ).fetchone()
            if version != 1 or not isinstance(last_seen, (int, float)) or not math.isfinite(last_seen):
                raise ValueError("unsupported state")
            active = db.execute(
                "SELECT MAX(lease_until) FROM fl_ask_calls WHERE finished=0 AND lease_until>?", (now,)
            ).fetchone()[0]
            retry_after = max(0, int(active - now) + 1) if active is not None else 0
            quota = {"daily_limit": config.daily, "minute_limit": config.minute}
            for window, limit, label in (
                (60, config.minute, "last_60s"),
                (86400, config.daily, "last_24h"),
            ):
                count, earliest = db.execute(
                    "SELECT COUNT(*), MIN(created_at) FROM fl_ask_calls WHERE created_at>?", (now - window,)
                ).fetchone()
                quota[label] = count
                quota[label.replace("last_", "remaining_")] = max(0, limit - count)
                if limit > 0 and count >= limit:
                    retry_after = max(retry_after, int(earliest + window - now) + 1)
            quota["retry_after_seconds"] = retry_after
            quota["active_generation"] = active is not None
            result.update(ask_state_ready=True, quota=quota)
    except (sqlite3.Error, OSError, TypeError, ValueError, OverflowError):
        result["reason"] = "ask_state_unavailable"
        return result
    if now < last_seen:
        reason = "server_clock_unavailable"
    elif not config.configured:
        reason = "disabled_or_invalid_configuration"
    elif retry_after:
        reason = "shared_limit_reached"
    else:
        reason = "ready"
    result.update(reason=reason, ready_to_attempt_generation=reason == "ready")
    return result


def main() -> None:
    print(json.dumps(inspect_status(Settings.from_env(), LLMSettings.from_env()), indent=2))


if __name__ == "__main__":
    main()
