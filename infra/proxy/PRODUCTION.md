# API production deployment preparation

The team selected frontend hosting on Vercel and API/SQLite on the existing VPS.
The existing qresto-production-nginx-1 keeps ports 80/443. This package is a proposed
configuration and local test, not proof of a deployment or certificate issuance.
The backend application, importer and dependency files are still pending.

## Required read-only host inspection

Before applying any command below, inspect the host and save the current config:

```sh
free -h
nproc
df -h /
docker stats --no-stream
docker exec qresto-production-nginx-1 nginx -v
docker exec qresto-production-nginx-1 nginx -T
docker inspect qresto-production-nginx-1 --format '{{json .Mounts}}'
docker inspect qresto-production-nginx-1 --format '{{json .NetworkSettings.Networks}}'
docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
systemctl list-timers --all
```

Do not paste secrets or private key contents. Confirm which Compose file owns
Nginx, the exact include pattern for conf.d, the existing certificate renewal job,
volume names, certificate client version and a working reload command. The observed
mounts were /opt/feloza-edge/nginx/conf.d -> /etc/nginx/conf.d,
qresto-production_certbot-certs -> /etc/letsencrypt, and
qresto-production_certbot-webroot -> /var/www/certbot. Recheck them on the host.
Do not upgrade the running Nginx or install a second renewal scheduler by default.

Host output supplied on 14 November confirms Nginx 1.28.3, the conf.d/*.conf
include and the existing qresto-certbot-renew.timer. Its service invokes
/opt/qresto/infra/scripts/certbot/renew-production-certificates.sh, which runs
unscoped certbot renew --quiet and reloads Nginx only when that command succeeds.
It uses /opt/qresto/infra/docker-compose.production.yml and .env.production under
project qresto-production. The running edge Nginx instead records the base.yml,
release.yml and edge.yml files under /opt/feloza-edge. Confirm the effective
Certbot mounts match the running Nginx mounts before issuance. Do not print the
full interpolated Compose model or environment secrets to perform that check.

## Routing and persistence

Production uses only compose.yaml plus compose.prod.yaml. Never add compose.dev.yaml.
The web service has an inactive local-web profile; normal production startup starts
only api. No API host port is published. SQLite remains on the separate app_state
volume and ./data is mounted read-only. The external flareledger_ingress network
connects only Nginx and FlareLedger API; do not attach other QResto services.

After host inspection and agreement, create the network once and record it in the
existing Nginx Compose service as an additional external network. A live network
connect can bootstrap this, but is not persistent configuration:

```sh
docker network create flareledger_ingress
docker network connect flareledger_ingress qresto-production-nginx-1
```

Skip these commands if the network or attachment already exists. Do not replace
Nginx's other networks. The unique upstream alias is flareledger-api:8000. Leave
proxy configuration inactive until the network is prepared. Record a fixed image
tag/digest after real builds. Reuse the existing Certbot image and volume setup;
this project does not introduce another certificate client or scheduler.

For persistent attachment, the host edge.yml is the maintained override; state/base.yml
and state/release.yml are recorded snapshots and should not be edited for this task.
Merge these fields into edge.yml without removing its current image, mounts or
entrypoint (it currently uses JSON syntax, which is valid YAML):

```yaml
services:
  nginx:
    networks:
      - outside
      - flareledger_ingress
networks:
  flareledger_ingress:
    name: flareledger_ingress
    external: true
```

Validate the same three-file edge model with its original env file before applying.
The existing outside network must remain. Do not run an unrestricted up command:
the base snapshot contains stopped QResto services and dependency chains. A manual
network connect can avoid recreating Nginx now; edge.yml preserves the intent for
future approved recreations. Current host files have not been edited by this PR.

Start the API only after its source/dependencies and explicit importer are verified:

```sh
docker compose -f compose.yaml -f compose.prod.yaml config --quiet
docker compose -f compose.yaml -f compose.prod.yaml up -d --build api
```

Set IMAGE_TAG to the release SHA and keep LLM disabled until the quota is confirmed.
Run the actual backend import command separately. Check ready and corpus version
from inside api before external acceptance. No guessed ingestion CLI is provided.

## DNS and first certificate

The DNS owner adds api.flareledger.fun A -> 57.129.163.115. Do not add AAAA until
IPv6 is verified. The apex frontend domain remains on Vercel.

Back up the current proxy files outside conf.d. Install only api-bootstrap.conf as
/opt/feloza-edge/nginx/conf.d/flareledger-api.conf. Never install both vhost files
at once, and do not put backup .conf files inside the active include directory.
After every edit, test before reload:

```sh
docker exec qresto-production-nginx-1 nginx -t
docker exec qresto-production-nginx-1 nginx -s reload
```

Verify a temporary challenge file is reachable from another device at
http://api.flareledger.fun/.well-known/acme-challenge/TEST_NAME. Certbot must write
to the same webroot seen by Nginx. Only after DNS and HTTP are confirmed, use the
existing Certbot service, after verifying its effective volume names:

```sh
sudo docker compose --project-name qresto-production --env-file /opt/qresto/infra/.env.production --file /opt/qresto/infra/docker-compose.production.yml run --rm --no-deps certbot certonly --webroot -w /var/www/certbot --cert-name api.flareledger.fun -d api.flareledger.fun
```

The account owner supplies the contact address and accepts any applicable ACME
terms interactively; do not hard-code consent. No request to a real ACME CA is part
of the local test. After issuance, verify fullchain.pem and privkey.pem are present
in the named lineage, then replace the active bootstrap with api-https.conf.
Run nginx -t before reload; keep the previous working configuration for rollback.

## Renewal

The existing timer checks twice daily (03:17 and 15:17 in the server's configured
timezone, with up to 30 minutes random delay). Its script renews all due lineages,
then reloads Nginx. Once the new webroot lineage is issued into the same certificate
volume, it should be covered by that renewal command. Confirm with a scoped dry-run:

```sh
sudo docker compose --project-name qresto-production --env-file /opt/qresto/infra/.env.production --file /opt/qresto/infra/docker-compose.production.yml run --rm --no-deps certbot renew --cert-name api.flareledger.fun --dry-run
```

Do not install a FlareLedger timer or restart/replace the QResto schedule. The
existing script does not run nginx -t before its reload; manually validate every
proxy edit before reloading. Any change to shared renewal behavior belongs in the
host infrastructure workflow. No issuance, renewal dry-run or scheduler change has
been executed by this PR. Record the dry-run result and inspect the existing service
journal after the first scheduled run containing this lineage.

## Frontend and acceptance

Configure a Vercel external rewrite /api/:path* ->
https://api.flareledger.fun/api/:path* before any SPA catch-all. Keep VITE_API_BASE_URL
as /api. The backend API must not receive an HTML fallback. No Vercel setting is
changed here. Direct cross-origin browser calls require a separately agreed CORS
policy; this package adds no wildcard CORS headers. Do not trust arbitrary forwarded
client headers for rate limits; verify the Vercel and proxy trust chain with the
backend owner. The API hostname itself remains publicly accessible through Nginx.

External checks: valid public TLS/hostname without disabling verification, health,
catalog, unknown ID, Ask failure states and QResto's usual URLs before/after reload.
Test /api through Vercel as well as the direct API hostname. Record the availability
end date with the owner; it is not yet fixed.

Use the backup utility from [the local operations guide](../README.md), substituting
compose.prod.yaml for compose.dev.yaml. Copy backups off the working volume with
their matching corpus/version. Rehearse a separate restore before calling recovery
verified. A deploy backup cannot replace a scientific review of the corpus.

Rollback affects only this vhost, API containers and corpus/image version. Remove
or restore the FlareLedger vhost, test then reload Nginx, and stop only the FlareLedger
API if needed. Do not stop QResto, remove shared certificates/volumes, or prune Docker.

## References

- [Nginx proxy module](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
- [Certbot webroot and renewal](https://eff-certbot.readthedocs.io/en/stable/using.html)
- [Docker Compose profiles](https://docs.docker.com/compose/how-tos/profiles/)
