# Ingress configuration

The selected public route is Vercel frontend plus the existing QResto Nginx for
api.flareledger.fun. No second public listener is created on the host.

See [production preparation and required host inspection](PRODUCTION.md). The
HTTP bootstrap and HTTPS vhosts are alternative versions of one site, not files
to install simultaneously. The actual server configuration is not changed here.

Local checks:

```sh
python scripts/check_production.py
python scripts/test_nginx.py
```

The latter needs Docker Engine and OpenSSL. It uses disposable test fixtures and
an explicitly trusted local certificate, without disabling TLS verification.
It does not contact an ACME CA or test the actual QResto application.
