"""Test the proposed Nginx vhosts locally with disposable TLS and an HTTP stub."""

import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid

from test_caddy import API_STUB


ROOT = Path(__file__).resolve().parents[1]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    openssl = shutil.which("openssl")
    if not openssl:
        candidate = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/usr/bin/openssl.exe"
        if not candidate.is_file():
            raise SystemExit("OpenSSL is required to generate the disposable test certificate.")
        openssl = str(candidate)
    project = "flareledger-nginx-test-" + uuid.uuid4().hex[:12]
    with tempfile.TemporaryDirectory(prefix=project + "-") as directory:
        temp = Path(directory)
        conf = temp / "conf"
        conf.mkdir()
        challenge = temp / "webroot/.well-known/acme-challenge"
        challenge.mkdir(parents=True)
        (challenge / "local-test").write_text("TEST_CHALLENGE", encoding="utf-8")
        cert = temp / "certs/live/api.flareledger.fun"
        cert.mkdir(parents=True)
        active = conf / "flareledger-api.conf"
        shutil.copyfile(ROOT / "infra/proxy/api-bootstrap.conf", active)
        (conf / "other.conf").write_text(
            'server { listen 80; server_name other.test; location / { return 200 "OTHER_TEST_SITE"; } }\n',
            encoding="utf-8",
        )
        stub = temp / "api.py"
        stub.write_text(API_STUB, encoding="utf-8")

        def mount(source, target):
            return {"type": "bind", "source": str(source), "target": target, "read_only": True}

        configuration = {"services": {
            "api": {"image": "python:3.12-slim", "command": ["python", "/test/api.py"],
                    "volumes": [mount(stub, "/test/api.py")],
                    "networks": {"default": {"aliases": ["flareledger-api"]}}},
            "nginx": {"image": "nginx:stable-alpine", "depends_on": ["api"],
                      "ports": [{"target": p, "host_ip": "127.0.0.1"} for p in (80, 443)],
                      "volumes": [mount(conf, "/etc/nginx/conf.d"),
                                  mount(temp / "webroot", "/var/www/certbot"),
                                  mount(temp / "certs", "/etc/letsencrypt")]},
        }}
        compose_file = temp / "compose.json"
        compose_file.write_text(json.dumps(configuration), encoding="utf-8")
        command = ["docker", "compose", "-p", project, "-f", str(compose_file)]

        def compose(*args, capture=False):
            return subprocess.run(command + list(args), check=True, capture_output=capture, text=True)

        def address(port):
            value = compose("port", "nginx", str(port), capture=True).stdout.strip()
            if not value.startswith("127.0.0.1:"):
                raise AssertionError("Test listeners must stay on localhost")
            return value

        def check(opener, url, status, host="api.flareledger.fun", body=None):
            req = urllib.request.Request(url, headers={"Host": host}, data=body)
            try:
                response = opener.open(req, timeout=3)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                content, headers = response.read().decode(), response.headers
                if response.code != status:
                    raise AssertionError(f"{url}: expected {status}, received {response.code}")
            return content, headers

        def eventually(operation):
            deadline = time.monotonic() + 20
            while True:
                try:
                    return operation()
                except (OSError, AssertionError):
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.25)

        try:
            compose("up", "-d", "--wait", "--wait-timeout", "40")
            http = "http://" + address(80)
            plain = urllib.request.build_opener(NoRedirect())
            eventually(lambda: check(plain, http + "/api", 503))
            content, _ = check(plain, http + "/.well-known/acme-challenge/local-test", 200)
            assert content == "TEST_CHALLENGE"
            print("PASS HTTP bootstrap without any certificate; challenge is served")

            subprocess.run([
                openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                "-keyout", str(cert / "privkey.pem"), "-out", str(cert / "fullchain.pem"),
                "-subj", "/CN=api.flareledger.fun",
                "-addext", "subjectAltName=DNS:api.flareledger.fun,IP:127.0.0.1",
            ], check=True, capture_output=True)
            shutil.copyfile(ROOT / "infra/proxy/api-https.conf", active)
            compose("exec", "-T", "nginx", "nginx", "-t")
            compose("exec", "-T", "nginx", "nginx", "-s", "reload")
            trusted = ssl.create_default_context(cafile=str(cert / "fullchain.pem"))
            secure = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=trusted))
            https = "https://" + address(443)
            eventually(lambda: check(secure, https + "/api", 200))
            print("PASS TLS with an explicitly trusted local test certificate")
            _, headers = eventually(lambda: check(plain, http + "/api/trials?limit=2", 308))
            assert headers["Location"] == "https://api.flareledger.fun/api/trials?limit=2"
            content, _ = check(plain, http + "/.well-known/acme-challenge/local-test", 200)
            assert content == "TEST_CHALLENGE"
            print("PASS HTTP redirect and HTTP-01 challenge after TLS switch")
            for path in ("/api", "/api/trials?limit=2"):
                content, headers = check(secure, https + path, 200)
                assert json.loads(content)["path"] == path
                assert headers["Cache-Control"] == "no-store"
            content, _ = check(secure, https + "/api/ask", 200, body=b"test-body")
            assert json.loads(content)["method"] == "POST"
            assert json.loads(content)["body"] == "test-body"
            content, headers = check(secure, https + "/api/missing", 404)
            assert "application/json" in headers["Content-Type"]
            check(secure, https + "/apiary", 404)
            check(secure, https + "/", 404)
            print("PASS API prefix/query/POST, JSON 404, no SPA fallback and no-store")
            compose("stop", "api")
            check(secure, https + "/api", 502)
            compose("exec", "-T", "nginx", "nginx", "-t")
            content, _ = check(plain, http + "/", 200, host="other.test")
            assert content == "OTHER_TEST_SITE"
            print("PASS upstream outage preserves another test vhost; Nginx config stays valid")
            compose("up", "-d", "--force-recreate", "api")
            eventually(lambda: check(secure, https + "/api", 200))
            print("PASS API recovery after recreation without reloading Nginx")
            print("No real ACME issuance, VPS configuration or QResto application was tested.")
        finally:
            compose("down", "--volumes", "--remove-orphans")


if __name__ == "__main__":
    main()
