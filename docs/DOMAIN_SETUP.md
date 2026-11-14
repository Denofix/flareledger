# Connect flareledger.fun

The domain is registered with Vercel. Its address and nameservers exist, while the application still needs a hosting destination. Choose one route below after the corresponding application is ready.

## Frontend on Vercel

The current frontend directory contains a layout scaffold rather than a buildable Vite application. The first frontend PR must add package.json, package-lock.json, application source, and a verified build before these deployment steps can succeed.

1. Open [Vercel New Project](https://vercel.com/new).
2. Import Denofix/flareledger from GitHub.
3. If the repository is not listed, configure the Vercel GitHub integration to grant access to this selected repository.
4. Select frontend as Root Directory and Vite as Framework Preset.
5. Use the verified npm ci installation command, npm run build build command, and dist output directory.
6. Deploy and confirm that the provided vercel.app address serves the application.
7. Open that project's Settings > Domains and choose Add Existing or Add Domain.
8. Enter flareledger.fun without a scheme or path. Use the same Vercel team that owns the domain.
9. Follow the exact DNS instructions shown for that project. With Vercel-managed DNS, configuration can be applied through the dashboard. Existing records should match the project's required values.
10. Wait for valid domain configuration and certificate issuance, then verify the HTTPS address from another device.

The domain-level Connected Projects > Connect button can attach an existing project. If there is no project yet, deploy one first. Keep the existing Vercel nameservers for this route. Values shown as form placeholders are not saved DNS records.

The API still needs a verified backend deployment and an explicit /api route. Secrets, SQLite state, and source-corpus originals remain on the backend. Full backend hosting on Vercel would require a separate persistence and runtime decision.

## Whole application on QResto infrastructure

For the current FastAPI and SQLite architecture, QResto reuse remains a candidate after Timofey confirms access, capacity, and the existing ingress. Domain registration can stay with Vercel.

1. Obtain the actual public server IPv4 and the approved deployment route.
2. Deploy and check isolated FlareLedger services behind the existing server ingress.
3. Open the [Vercel domain dashboard](https://vercel.com/denofix-2940/~/domains/flareledger.fun).
4. Set the root-domain A record to the verified IPv4. The dashboard may represent the root as @ or an empty name. Resolve any conflicting root record deliberately rather than stacking two different hosting destinations.
5. Add IPv6 only after end-to-end IPv6 access is verified. Keep the existing CAA records unless a concrete certificate issue requires a change.
6. Timofey configures flareledger.fun and its certificate in the existing host ingress. Public 80/443 ownership stays with that ingress.
7. Verify external DNS, HTTPS, frontend routes, and API readiness.

This route does not require a Vercel application project. Do not use an example Vercel IP as the QResto address. An external server obtains its certificate through its own ingress.

## Verify from Ubuntu

```bash
sudo apt install -y dnsutils curl
dig +short NS flareledger.fun
dig @1.1.1.1 +short A flareledger.fun
dig @1.1.1.1 +short AAAA flareledger.fun
curl -I https://flareledger.fun
```

Compare DNS results with the chosen hosting destination. Application health checks become meaningful after the actual API implementation and deployment exist.

## References

- [Vercel custom domains](https://vercel.com/docs/domains/working-with-domains/add-a-domain)
- [Vercel DNS records](https://vercel.com/docs/domains/managing-dns-records)
- [Vercel monorepos](https://vercel.com/docs/monorepos)
