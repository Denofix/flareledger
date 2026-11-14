# Deployment decision

The team selected Vercel for the frontend at flareledger.fun and the existing VPS
for FastAPI and persistent SQLite. This is the intended deployment architecture,
not a completed deployment. The selected backend hostname is api.flareledger.fun;
the existing Nginx keeps 80/443 and routes to API through a dedicated Docker network.
DNS, HTTPS, server availability period and persistent ingress attachment still need
verification. This infrastructure phase changes no remote service. See the
[production runbook](../infra/proxy/PRODUCTION.md).

## Previous candidate

Hosting the built frontend and API together on QResto was the original candidate.
It remains a possible local/fallback layout, but is not the selected public frontend
hosting route. Do not use the local Compose override as a production deployment.

The VPS already has services using 80/443. The team selected reuse of that existing
proxy without stopping QResto. compose.prod.yaml supplies API-only routing to the
external flareledger_ingress network. Host inspection and explicit deployment are
still required; no remote service has been modified by the infrastructure PR.

## Selected Vercel frontend and VPS backend

Once a real Vite application is merged, import this GitHub repository into Vercel, choose frontend/ as the project root, use the verified install/build commands and dist output, and connect flareledger.fun to the project. Follow the DNS values provided for that specific project.

The current FastAPI/SQLite plan still needs a backend hosting decision. A static frontend deployment does not run Docker Compose or provide the proposed persistent local SQLite volume. To retain same-origin /api, add an explicit route to the verified HTTPS backend. Do not deploy a catch-all SPA rewrite that captures API routes first.

A full Vercel backend is a separate design choice. Verify its current Python runtime, request limits, filesystem behavior, and persistence requirements before adapting the backend. This repository does not assume that change.

## Domain steps

The [domain guide](DOMAIN_SETUP.md) explains how to connect the purchased domain after hosting is selected. Do not replace DNS with an example address. Use the actual VPS address or the DNS values Vercel displays for the imported project.

## References

- [Vercel domains](https://vercel.com/docs/domains/working-with-domains/add-a-domain)
- [Vercel monorepos](https://vercel.com/docs/monorepos)
- [Vercel Vite support](https://vercel.com/docs/frameworks/frontend/vite)
