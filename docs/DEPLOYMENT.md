# Deployment decision

The selected layout is live: the Vue frontend is published on Vercel at
https://flareledger.fun/ and https://flareledger.vercel.app/. Its `/api` rewrite
forwards to FastAPI at https://api.flareledger.fun. SQLite remains on the VPS;
Vercel does not host the persistent database or run Docker Compose.

As checked on 15 November 2026, the API runs
`969cb9460de9115fe0a16016bd02bf168aa7175e` (`flareledger-api:969cb94`). The managed
checkout is `/home/tymofii/flareledger`; tooling is `/home/tymofii/flareledger-ops`.
The existing Nginx keeps ports 80/443 and reaches `flareledger-api:8000` through
`flareledger_ingress`. The API publishes no host port. DNS, HTTPS, the persistent
ingress attachment and explicit corpus import are complete.

Both domains return HTTP 200 / `ready` for `/api/health/ready` with the same corpus
version. Gemini 3.6 Flash is explicitly enabled with persistent shared limits;
readiness is checked without calling Ask. See [AI setup](AI_SETUP.md),
[infrastructure status](INFRA_STATUS.md) and [release audit](RELEASE_AUDIT.md).
The API revision was verified directly; the public frontend does not expose an
independently verifiable source SHA, so the initial frontend commit must not be
reported as its current deployed revision.

## Updates and recovery

Use the [production runbook](../infra/proxy/PRODUCTION.md) and
[explicit deploy/rollback procedure](DEPLOY_ROLLBACK.md). A frontend merge can
trigger Vercel publication; it does not update the VPS API. Keep code, the
read-only `data/` mount (including `data/ask-context`) and the selected backend
image consistent. Take and verify the required backup before a release.

The current release is the frozen evaluation baseline. Review open UI/documentation
PRs separately and agree any release change before resuming its live evaluation.
PR20–22 preserved the existing database and quota history and needed no new
migration. Fresh databases require the explicit setup steps; never re-import or
reset production state to obtain quota.

## Local/fallback layout

The local Compose override can serve frontend and API together for development;
it is not the selected public ingress. For native startup, use the pinned Python
3.12 and Node 24 instructions in [backend setup](../backend/README.md) and
[frontend setup](../frontend/README.md). Keep generation disabled for an offline
catalog/chart demonstration; no key is needed for those features. The final
fallback walkthrough and operator handoff still require team confirmation.

## Domain and hosting continuity

The existing routing is configured in `frontend/vercel.json` and the production
proxy files. Do not replace working DNS with example records. Consult the
[domain guide](DOMAIN_SETUP.md) only when deliberately changing the deployment.
The VPS lease ends on 1 December 2026; the exact shutdown hour is unconfirmed.
Use [backup and recovery](BACKUP_RECOVERY.md) to plan continuity before that date.

## References

- [Vercel domains](https://vercel.com/docs/domains/working-with-domains/add-a-domain)
- [Vercel monorepos](https://vercel.com/docs/monorepos)
- [Vercel Vite support](https://vercel.com/docs/frameworks/frontend/vite)
