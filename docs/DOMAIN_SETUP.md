# Domains and project routing

Account inspection on 17 November 2026 confirmed the registered apex domain **flareledger.fun** in the Vercel team **denofix-2940**. Domain registration, project assignment, authoritative DNS and application routing are different settings.

## Existing assignments

| Hostname | Vercel project | State at inspection |
| --- | --- | --- |
| flareledger.fun | flareledger | Verified |
| flareledger.vercel.app | flareledger | Verified |
| pulseboard.flareledger.fun | pulse-board | Verified |
| servermedic.flareledger.fun | servermedic | Verified |
| download-convert.flareledger.fun | download-convert | Verified |

The FlareLedger project uses the `frontend` Vite application. Its same-origin `/api` routes forward to the existing VPS API at `https://api.flareledger.fun`; SQLite and runtime credentials remain on that backend. The API hostname must continue to point to the VPS, not to a static frontend.

## Independent names and reuse

Registering `flareledger.fun` gives control over that name and its subdomains. It does not register the `.fun` top-level domain or unrelated names such as `pulseboard.fun`. Each independent name requires separate availability, registration and renewal. No additional purchase or renewal is performed by this repository change.

Existing projects can instead use their own `vercel.app` aliases without a FlareLedger subdomain. Paths such as `flareledger.fun/projects/pulseboard` would require explicit route/base-path integration, not a DNS rename. Moving the apex to another project would change the current FlareLedger website and is not needed to use subdomains on other projects.

## Routine verification

Use the existing Vercel project rather than the original project-creation/bootstrap instructions. Resolve the expected project and team before a domain mutation. Inspect the required DNS values for that exact hostname; preserve unrelated records and existing certificates.

```sh
curl --fail --silent --show-error https://flareledger.fun/api/health/ready
curl --fail --silent --show-error https://api.flareledger.fun/api/health/ready
```

Both returned HTTP 200 and `ready` on 17 November 2026. This checks corpus readiness, not a Gemini model call or current quota. The domain review made no DNS or domain-assignment changes.

## References

- [Vercel domain assignment](https://vercel.com/docs/domains/working-with-domains/add-a-domain)
- [Vercel DNS records](https://vercel.com/docs/domains/managing-dns-records)
- [Vercel rewrites](https://vercel.com/docs/routing/rewrites)
