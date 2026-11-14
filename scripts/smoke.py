"""Check the real local application without invoking an external LLM."""

import argparse
import json
import sys
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    failures = []

    def check(path, expected, content_type, require_json=False):
        try:
            try:
                response = urllib.request.urlopen(base + path, timeout=10)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                status = response.code
                media_type = response.headers.get("Content-Type", "")
                body = response.read()
            if status != expected:
                raise ValueError(f"expected HTTP {expected}, received {status}")
            if content_type not in media_type:
                raise ValueError(f"expected {content_type}, received {media_type}")
            if require_json:
                json.loads(body)
            print(f"PASS {path}")
        except (OSError, ValueError) as error:
            failures.append(path)
            print(f"FAIL {path}: {error}")

    check("/healthz", 200, "text/plain")
    check("/api/health/live", 200, "application/json", True)
    check("/api/health/ready", 200, "application/json", True)
    check("/compare", 200, "text/html")
    check("/api/investigations", 200, "application/json", True)
    check("/api/investigations/__infra_unknown_id__", 404, "application/json", True)
    print("Not checked: scientific validity, Ask responses, persistence, backup restore.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
