# Infrastructure progress

Owner: Timofey. Current branch: infra/production-api, following merged PR #4.
This phase prepares production configuration and tests it locally.
This package changes no server, DNS or Vercel setting. Git publication and team
review are separate from deployment.

| Deliverable | State | Remaining validation |
| --- | --- | --- |
| Backend Dockerfile | Prepared against target contract | Real app/dependencies and image build |
| Local frontend Dockerfile and Caddy | Caddy routing tested in isolation | Real npm lock/scripts, image build and app integration |
| Compose | Configuration validation available | Real application startup |
| LLM environment | Disabled defaults, day/minute/concurrency settings passed | Backend implementation and confirmed provider |
| Infrastructure CI | Workflow prepared | GitHub execution after push |
| SQLite backup | Utility and disposable WAL tests available | Real database and complete restore rehearsal |
| Smoke utility | Prepared, no LLM calls | Actual catalog, health and SPA routes |
| English operations guide | Written | Rehearsal with the application |
| Application CI | Deferred | Existing Python/npm commands and meaningful tests |
| API-only production Compose | Prepared and configuration-tested | Real app, host network attachment |
| Nginx HTTP/HTTPS and Certbot webroot | Local vhost tests passed | Host inspection, real issuance and renewal scheduler |
| VPS deployment and DNS | Not performed | Server apply and external acceptance |

## Local validation on 14 November 2026

- Local Compose configuration parsed successfully, with no public API port and web
  bound to 127.0.0.1 only.
- LLM defaults checked: disabled, day/minute limits zero, concurrency one.
- Both backup tests passed, including committed data in an active WAL.
- Caddy configuration and routing passed in disposable Docker containers: static
  files, SPA routes, API prefix/query, POST body, JSON 404 and upstream failure.
  The fixtures contain no application implementation or scientific data.
- Nginx HTTP bootstrap, challenge route, local TLS, redirect, /api routing and
  upstream-failure isolation passed with temporary fixtures and a local certificate.
  This does not verify actual QResto configuration or real certificate renewal.
- Production Compose boundaries and Certbot configuration parse passed; renewal
  wrapper passes bash -n. The candidate timer is not installed or runtime-tested.
- Existing repository checker reported 51 tracked text files and zero problems.
- Working-tree and staged whitespace checks passed; smoke --help works.

These checks do not establish that application images build or that GitHub has
executed the new workflow. The application and its dependencies are still absent.

## Handoff required

- Backend app.main:app, fixed requirements and real lint/test commands.
- Frontend source, package.json, package-lock.json, build/typecheck/lint scripts.
- Confirm health endpoints, environment semantics, writable paths and import command.
- Importer compatible with the actual demo seed, retaining record types and evidence.
- Versioned corpus, manifest/source hashes and recovery-compatible database schema.

The presence of the NASA demo seed does not imply the importer exists or that its
scientific content has received independent human review. No data is modified here.

## Acceptance before release

Record the exact commit and corpus version. Build both images, initialize the real
corpus, pass smoke checks and manually verify evidence/units/graphs. Recreate API
and compare records. Rehearse backup restore separately. Check Ask unavailable,
insufficient evidence and quota states with the backend owner. Verify the deployed
URL and HTTPS only after server work is authorized and configured.
