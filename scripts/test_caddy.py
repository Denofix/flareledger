"""Exercise the real Caddyfile in disposable containers, without application code."""

import json
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid


ROOT = Path(__file__).resolve().parents[1]
API_STUB = '''import json
from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.reply()

    def do_POST(self):
        self.reply()

    def reply(self):
        size = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(size).decode("utf-8")
        status = 404 if self.path == "/api/missing" else 200
        body = json.dumps({"path": self.path, "method": self.command, "body": payload}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
'''


def main():
    project = "flareledger-caddy-test-" + uuid.uuid4().hex[:12]
    with tempfile.TemporaryDirectory(prefix=project + "-") as directory:
        temporary = Path(directory)
        site = temporary / "site"
        site.mkdir()
        (site / "index.html").write_text("<html>FLARELEDGER_TEST_PAGE</html>\n", encoding="utf-8")
        (site / "asset.css").write_text("/* FLARELEDGER_TEST_ASSET */\n", encoding="utf-8")
        stub = temporary / "api_stub.py"
        stub.write_text(API_STUB, encoding="utf-8")
        configuration = {
            "services": {
                "api": {
                    "image": "python:3.12-slim",
                    "command": ["python", "/test/api_stub.py"],
                    "volumes": [{"type": "bind", "source": str(stub), "target": "/test/api_stub.py", "read_only": True}],
                },
                "web": {
                    "image": "caddy:2-alpine",
                    "depends_on": ["api"],
                    "ports": [{"target": 80, "host_ip": "127.0.0.1"}],
                    "volumes": [
                        {"type": "bind", "source": str(ROOT / "frontend/docker/Caddyfile"), "target": "/etc/caddy/Caddyfile", "read_only": True},
                        {"type": "bind", "source": str(site), "target": "/srv", "read_only": True},
                    ],
                },
            }
        }
        compose_file = temporary / "compose.json"
        compose_file.write_text(json.dumps(configuration), encoding="utf-8")
        command = ["docker", "compose", "-p", project, "-f", str(compose_file)]

        def compose(*args, capture=False):
            return subprocess.run(command + list(args), check=True, text=True, capture_output=capture)

        def request(path, expected_status=200, expected_type=None, body=None):
            data = body.encode() if body is not None else None
            req = urllib.request.Request(base + path, data=data)
            try:
                response = urllib.request.urlopen(req, timeout=5)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                content = response.read().decode()
                if response.code != expected_status:
                    raise AssertionError(f"{path}: expected {expected_status}, got {response.code}")
                if expected_type and expected_type not in response.headers.get("Content-Type", ""):
                    raise AssertionError(f"{path}: unexpected Content-Type")
            print(f"PASS {req.get_method()} {path}: HTTP {expected_status}")
            return content

        try:
            compose("up", "-d", "--wait", "--wait-timeout", "40")
            compose("exec", "-T", "web", "caddy", "validate", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile")
            address = compose("port", "web", "80", capture=True).stdout.strip()
            if not address.startswith("127.0.0.1:"):
                raise AssertionError("Test port must be bound to localhost")
            base = "http://" + address
            for path, media_type in (("/healthz", "text/plain"), ("/api", "application/json")):
                deadline = time.monotonic() + 15
                while True:
                    try:
                        request(path, expected_type=media_type)
                        break
                    except (OSError, AssertionError):
                        if time.monotonic() >= deadline:
                            raise
                        time.sleep(0.25)

            for path in ("/", "/compare", "/investigations/test-fixture"):
                if "FLARELEDGER_TEST_PAGE" not in request(path, expected_type="text/html"):
                    raise AssertionError(f"{path}: SPA fallback did not return the test page")
            if "FLARELEDGER_TEST_ASSET" not in request("/asset.css", expected_type="text/css"):
                raise AssertionError("Static asset was replaced by SPA fallback")
            for path in ("/api", "/api/trials?limit=2"):
                if json.loads(request(path, expected_type="application/json"))["path"] != path:
                    raise AssertionError("API prefix or query string changed")
            payload = json.loads(request("/api/ask", expected_type="application/json", body="test-body"))
            if payload["method"] != "POST" or payload["body"] != "test-body":
                raise AssertionError("Proxy changed POST method/body")
            request("/api/missing", expected_status=404, expected_type="application/json")
            compose("stop", "api")
            request("/api/trials", expected_status=502)
            request("/healthz", expected_type="text/plain")
            if "FLARELEDGER_TEST_PAGE" not in request("/compare", expected_type="text/html"):
                raise AssertionError("Static site failed with backend offline")
            print("Caddy routing checks passed. This is not an application or scientific-data test.")
        finally:
            # Scope is the unique disposable project above, never the app or VPS.
            compose("down", "--volumes", "--remove-orphans")


if __name__ == "__main__":
    main()
