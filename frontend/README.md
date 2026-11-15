# FlareLedger frontend

Vue 3, TypeScript and Vite application for the existing [backend API](../docs/BACKEND_API.md).
Node **24.x** and npm are required. Dependencies and the real lock file are committed.

## Run locally

From this directory:

```bash
node --version
npm ci
npm run dev
```

Open the local URL printed by Vite. Start the backend separately using
[its setup instructions](../backend/README.md); the development proxy forwards
`/api` to `http://127.0.0.1:8000` by default. Importing the corpus is an explicit
backend step. The frontend never creates a database or imports data.

To use the team's public API instead of a local backend, create an ignored
`frontend/.env.local` containing:

```dotenv
API_PROXY_TARGET=https://api.flareledger.fun
```

Restart Vite after changing environment configuration. Keep
`VITE_API_BASE_URL=/api` (the default). This preserves same-origin browser requests
and avoids depending on cross-origin CORS permissions. `API_PROXY_TARGET` is only
used by the development server; Vercel uses `vercel.json` instead. Never put keys
or other credentials in `VITE_*` variables: these values become public JavaScript.

## Checks and build

```bash
npm run typecheck
npm run lint
npm run test
npm run build
```

Tests cover null versus zero, incompatible scientific axes, chart gaps and point
inspection, source-link injection, stale requests, API errors/timeouts, deep-linked
comparison and structured Ask unavailability. Test fixtures are explicitly synthetic
and live under `tests/`; application screens read the API and contain no fixture fallback.

`npm run build` produces `dist/`. `npm run preview` serves that static build locally;
it is not a production reverse proxy. For API-backed development, use `npm run dev`.
The existing Dockerfile builds the same application and uses Caddy to proxy `/api`
to the Compose API service. `.dockerignore` excludes local packages, builds and
environment files. A Docker build is included in frontend CI.

## Screens

| Route                          | Purpose                                                                     |
| ------------------------------ | --------------------------------------------------------------------------- |
| `/`                            | Investigation catalogue, keyword and fuel-phase filters, real corpus counts |
| `/investigations/:id`          | Investigation, record types, metadata, evidence and source links            |
| `/measurements?ids=...`        | Original measured series and point inspector                                |
| `/compare?ids=...`             | Two to four compatible series with their source limitations                 |
| `/evidence?q=...`              | Lexical search across the corpus with source evidence                       |
| `/sources/:id`, `/records/:id` | Original source or typed record, locators and full payload                  |
| `/ask`                         | Optional source-linked explanation; explicit quota, refusal and outage states |

Vue Router uses HTML5 history. A static host must route non-API deep links to
`index.html`; API requests must retain their JSON response and HTTP status.
See the [Vercel handoff](../docs/FRONTEND_HANDOFF.md).

The `/evidence/:id` route opens the original evidence locator, extraction method and review status.

## Scientific and interface boundaries

- Original point values, order, IDs, units and source links are preserved.
  Missing coordinates create chart gaps. Time coordinates are not realigned;
  source zero events are not independently verified. Lines connect existing points;
  they do not create new measured points or apply smoothing.
- Droplet and flame diameters remain different quantities, even when both use mm.
  The backend comparison response supplies the displayed limitations.
- Unknown values display **Not reported**; a reported zero remains zero.
  Source record counts, actual trial rows and other record types remain distinct.
- An ingestion checksum establishes source identity, not an independent scientific
  review. Review status and evidence locators remain available alongside sources.
- Live LLM generation is disabled by default and the budget remains USD 0. When
  explicitly enabled, Ask can call the backend Gemini adapter and displays the
  model, corpus, exact context excerpts, linked sources and limitations. Mechanical
  checks are not scientific review; see [SI setup](../docs/AI_SETUP.md).
- API errors have explicit loading/error/retry states. There is no sample-data
  fallback, upload flow, authentication system or browser-held API key.
- Branding, SVG icons and abstract CSS artwork are original project assets.
  No NASA insignia, external font or third-party image is bundled.

The interface is English and responsive, with semantic controls, visible keyboard
focus, a skip link, chart text alternatives and a keyboard-accessible point inspector.
FlareLedger is an independent hackathon project, not a validated fire safety tool.
