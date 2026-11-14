"""Check repository text hygiene, JSON, and local Markdown file links."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".py", ".sh", ".toml", ".txt"}
LINK = re.compile(r"!?\[[^\]]*\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)")
CONFLICT = re.compile(r"^(?:<{7} |={7}$|>{7} )", re.MULTILINE)


def main() -> int:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
        )
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Cannot list tracked repository files: {error}", file=sys.stderr)
        return 1
    names = [name for name in result.stdout.decode("utf-8").split("\0") if name]
    if not names:
        print("No tracked files found. Stage the repository files before checking.")
        return 1
    errors = []
    checked = 0
    for name in names:
        path = ROOT / name
        if not path.is_file() or (path.suffix not in TEXT_SUFFIXES and not path.name.startswith(".") and path.name != "LICENSE"):
            continue
        try:
            body = path.read_bytes()
            text = body.decode("utf-8")
        except (OSError, UnicodeDecodeError) as error:
            errors.append(f"{name}: {error}")
            continue
        checked += 1
        if body and not body.endswith(b"\n"):
            errors.append(f"{name}: missing final newline")
        if b"\r\n" in body:
            errors.append(f"{name}: use LF line endings")
        if CONFLICT.search(text):
            errors.append(f"{name}: unresolved merge conflict marker")
        if path.suffix == ".json":
            try:
                json.loads(text, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
            except (json.JSONDecodeError, ValueError) as error:
                errors.append(f"{name}: invalid JSON: {error}")
        if path.suffix == ".md":
            outside_code = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
            for match in LINK.finditer(outside_code):
                target = match[1].strip("<>")
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                link_path = unquote(parsed.path)
                destination = (ROOT / link_path.lstrip("/")) if link_path.startswith("/") else path.parent / link_path
                if not destination.exists():
                    errors.append(f"{name}: missing linked path {target}")
    for error in errors:
        print(error, file=sys.stderr)
    print(f"Checked {checked} tracked text files; {len(errors)} problem(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
