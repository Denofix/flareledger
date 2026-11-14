# Deployment decision

The domain flareledger.fun is registered through Vercel. Domain registration and application hosting are separate services. Keep the domain registered there while selecting either deployment route below.

## Recommended candidate for the current architecture

Reuse QResto infrastructure after Timofey confirms permission, capacity, and the existing ingress. Host the built frontend, FastAPI backend, and persistent SQLite state together. Route /api to the backend and other paths to the frontend under flareledger.fun. Manage DNS in Vercel, and let the server's existing ingress obtain and renew HTTPS certificates.

This route fits the proposed local filesystem and SQLite contract. The server IP and proxy configuration are not yet confirmed. No production Compose or ingress file is supplied by this bootstrap.

## Vercel frontend alternative

Once a real Vite application is merged, import this GitHub repository into Vercel, choose frontend/ as the project root, use the verified install/build commands and dist output, and connect flareledger.fun to the project. Follow the DNS values provided for that specific project.

The current FastAPI/SQLite plan still needs a backend hosting decision. A static frontend deployment does not run Docker Compose or provide the proposed persistent local SQLite volume. To retain same-origin /api, add an explicit route to the verified HTTPS backend. Do not deploy a catch-all SPA rewrite that captures API routes first.

A full Vercel backend is a separate design choice. Verify its current Python runtime, request limits, filesystem behavior, and persistence requirements before adapting the backend. This repository does not assume that change.

## Domain steps

The [domain guide in Russian](DOMAIN_SETUP_RU.md) explains how to connect the purchased domain after hosting is selected. Do not replace DNS with an example address. Use the actual VPS address or the DNS values Vercel displays for the imported project.

## References

- [Vercel domains](https://vercel.com/docs/domains/working-with-domains/add-a-domain)
- [Vercel monorepos](https://vercel.com/docs/monorepos)
- [Vercel Vite support](https://vercel.com/docs/frameworks/frontend/vite)
