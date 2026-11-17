# API production deployment preparation

The team selected frontend hosting on Vercel and API/SQLite on the existing VPS.
The existing shared Nginx keeps ports 80/443. Its container/project names,
volume names, host addresses and absolute host paths are operator-local details;
this public runbook uses parameters instead of publishing that inventory.

**Applied on 14 November 2026.** DNS (A record only), the certificate for
api.flareledger.fun, the HTTPS vhost and a scoped renewal dry-run were completed.
The API uses the deployment account's managed checkout in Compose project flareledger
(compose.yaml plus compose.prod.yaml). On 15 November 2026 the running backend
was verified at commit 969cb9460de9115fe0a16016bd02bf168aa7175e. Nginx is
attached to flareledger_ingress both live and in the host edge.yml override, with
a separate API alias. Existing shared sites still answer, and port 8000 is not
published. The sections below are the initial bootstrap procedure
that was followed and remain the rollback reference. Backup and recovery are in
[docs/BACKUP_RECOVERY.md](../../docs/BACKUP_RECOVERY.md).

Do not repeat certificate bootstrap or corpus initialization for a routine update.
Use [deploy/rollback](../../docs/DEPLOY_ROLLBACK.md) with the existing database,
and follow [AI setup](../../docs/AI_SETUP.md) to preserve enabled-generation
configuration and persistent quotas. Current evidence is in the
[release audit](../../docs/RELEASE_AUDIT.md).

## Required read-only host inspection

Before applying any command below, inspect the host and save the current config
privately. Set `NGINX_CONTAINER`, `SHARED_COMPOSE_PROJECT`, `SHARED_COMPOSE_FILE`
and `SHARED_ENV_FILE` from the private operator inventory; never guess them.
Shell commands below require these values and do not install a second proxy.

```sh
: "${NGINX_CONTAINER:?Set the existing ingress container name}"
```

Read-only inspection:

```sh
free -h
nproc
df -h /
docker stats --no-stream
docker exec "$NGINX_CONTAINER" nginx -v
docker exec "$NGINX_CONTAINER" nginx -T
docker inspect "$NGINX_CONTAINER" --format '{{json .Mounts}}'
docker inspect "$NGINX_CONTAINER" --format '{{json .NetworkSettings.Networks}}'
docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
systemctl list-timers --all
```

Do not publish raw inspection output, environment values or private key contents.
Confirm the existing Compose model, include pattern, renewal timer/script, image,
mounts and working reload command privately. The existing certificate volume must
map to `/etc/letsencrypt` and its webroot volume to `/var/www/certbot`; match these
against the running Nginx mounts before issuance. Renewal may use a different
Compose model from ingress, so compare actual resolved mount identities locally.
Use `config --quiet` for validation, not a published interpolated environment dump.
Do not upgrade Nginx or add a second certificate scheduler as part of this task.

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
docker network connect flareledger_ingress "$NGINX_CONTAINER"
```

Skip these commands if the network or attachment already exists. Do not replace
Nginx's other networks. The unique upstream alias is flareledger-api:8000. Leave
proxy configuration inactive until the network is prepared. Record a fixed image
tag/digest after real builds. Reuse the existing Certbot image and volume setup;
this project does not introduce another certificate client or scheduler.

For persistent attachment, update the existing managed ingress configuration
rather than generated snapshots. Add `flareledger_ingress` as an external network
to the existing Nginx service while preserving every existing network, image,
mount and entrypoint. Validate the complete existing Compose model with its private
environment before applying. Do not run an unrestricted `up`: unrelated services
or dependency chains may be present. A live network connection avoids recreating
Nginx; the maintained configuration must preserve the intent for future approved
recreations. This documentation change applies no host configuration.

Start the API only after its source/dependencies and explicit importer are verified:

```sh
docker compose -f compose.yaml -f compose.prod.yaml config --quiet
docker compose -f compose.yaml -f compose.prod.yaml up -d --build api
```

Set IMAGE_TAG to the release SHA and keep LLM disabled until the quota is confirmed.
Run the actual backend import command separately. Check ready and corpus version
from inside api before external acceptance. No guessed ingestion CLI is provided.

## DNS and first certificate

The DNS owner points api.flareledger.fun to the operator-confirmed VPS IPv4
address. Do not publish an example host address or add AAAA until
IPv6 is verified. The apex frontend domain remains on Vercel.

Back up the current proxy files outside conf.d. Install only api-bootstrap.conf as
the FlareLedger HTTP configuration; reload and verify existing sites. Do not install both
at once, and do not put backup .conf files inside the active include directory.
After every edit, test before reload:

```sh
docker exec "$NGINX_CONTAINER" nginx -t
docker exec "$NGINX_CONTAINER" nginx -s reload
```

Verify a temporary challenge file is reachable from another device at
http://api.flareledger.fun/.well-known/acme-challenge/TEST_NAME. Certbot must write
to the same webroot seen by Nginx. Only after DNS and HTTP are confirmed, use the
existing Certbot service, after verifying its effective volume names:

```sh
sudo docker compose --project-name "${SHARED_COMPOSE_PROJECT:?Set the existing certificate project}" --env-file "${SHARED_ENV_FILE:?Set its private environment file}" --file "${SHARED_COMPOSE_FILE:?Set its Compose file}" run --rm --no-deps certbot certonly --webroot -w /var/www/certbot --cert-name api.flareledger.fun -d api.flareledger.fun
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
sudo docker compose --project-name "${SHARED_COMPOSE_PROJECT:?Set the existing certificate project}" --env-file "${SHARED_ENV_FILE:?Set its private environment file}" --file "${SHARED_COMPOSE_FILE:?Set its Compose file}" run --rm --no-deps certbot renew --cert-name api.flareledger.fun --dry-run
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
end date with the owner: the lease ends on 1 December 2026, exact time unconfirmed.

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
