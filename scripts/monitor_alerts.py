"""Persistent Telegram incident transitions; credentials come only from the environment.

Uses Telegram Bot API sendMessage: https://core.telegram.org/bots/api#sendmessage
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path


class AlertError(RuntimeError):
    pass


def send(text: str) -> None:
    token = os.environ.get("BOT_TOKEN", "")
    chat = os.environ.get("CHAT_ID", "")
    if not token or not chat:
        raise AlertError("Telegram credentials are not configured")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat, "text": text}).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.load(response)
        if result.get("ok") is not True:
            raise ValueError("rejected")
    except Exception:
        # HTTP exceptions contain the token-bearing URL. Never log them.
        raise AlertError("Telegram delivery failed; incident state retained for retry") from None


def transition(directory: Path, healthy: bool, names: list[str], *, test: bool = False) -> bool:
    """Persist observed transitions before delivery; serialize sending and acknowledgements."""
    import fcntl  # VPS/Linux; same process holds the lock through send and state update.

    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (directory / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = directory / "incident.json"
        previous = json.loads(state.read_text()) if state.exists() else {"unhealthy": False}
        previous.setdefault("observed_unhealthy", previous["unhealthy"])
        previous.setdefault("pending", [])
        unhealthy = not healthy

        def save() -> None:
            temporary = directory / "incident.tmp"
            temporary.write_text(json.dumps(previous), encoding="utf-8")
            temporary.replace(state)

        if previous["observed_unhealthy"] != unhealthy:
            prefix = "[TEST] " if test else ""
            text = prefix + ("FlareLedger RECOVERED: all monitoring checks passed." if healthy else
                             "FlareLedger FAILURE after repeated checks: " + ", ".join(names))
            previous["pending"].append({"unhealthy": unhealthy, "text": text[:4000]})
            previous["observed_unhealthy"] = unhealthy
            save()  # An outage must survive delivery failure even if the next check is healthy.
        sent = False
        while previous["pending"]:
            event = previous["pending"][0]
            send(event["text"])
            previous["unhealthy"] = event["unhealthy"]
            previous["pending"].pop(0)
            save()  # A failed later send must not repeat an acknowledged earlier event.
            sent = True
        return sent


def main() -> int:
    parser = argparse.ArgumentParser(description="Send labelled test incident/recovery; never probes or changes the API")
    parser.add_argument("event", choices=("failure", "recovery"))
    parser.add_argument("--state", type=Path, required=True, help="separate test state directory")
    args = parser.parse_args()
    try:
        transition(args.state, args.event == "recovery", ["synthetic delivery check"], test=True)
    except (AlertError, OSError, ValueError, KeyError):
        print("ALERT_TEST_FAILED | check credentials, connectivity and test state", file=sys.stderr)
        return 1
    print("ALERT_TEST_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
