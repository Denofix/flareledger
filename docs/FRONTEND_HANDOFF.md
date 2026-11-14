# Frontend review and Vercel handoff

This change implements the Vue interface and its routing configuration. It does
not create a Vercel project, connect a domain, enable a model, or change the VPS.

## Review before merging

1. Run the four [frontend checks](../frontend/README.md#checks-and-build).
2. Start Vite with the local backend or the public development proxy described in
   the frontend README. Confirm corpus readiness and the reported corpus version.
3. Check the catalogue, a metadata-only investigation, a record with a missing
   value, a source link, FLEX measurements and an evidence search such as PMMA.
4. Open a comparison URL directly, refresh it and inspect an original point.
   Droplet diameter and flame diameter must not share an overlay. Source-specific
   camera/calibration limitations and unknown uncertainty must stay visible.
5. Submit an Ask question. In this release, the API returns structured 503
   llm_unavailable; the screen displays retrieved evidence and explicitly states
   that no AI answer was generated. A different outage must display an error.
6. Check a nonexistent record and a nonexistent frontend route. Check keyboard
   navigation and a narrow phone viewport. No page should silently replace errors
   with empty research data.
7. Require passing hosted checks and another team member's review. Record the
   final reviewed commit before publication.

## Vercel project settings

Import `Denofix/flareledger` in the existing Vercel account and use:

| Setting           | Value                                                  |
| ----------------- | ------------------------------------------------------ |
| Root Directory    | `frontend`                                             |
| Framework Preset  | Vite                                                   |
| Node.js Version   | 24.x                                                   |
| Install Command   | `npm ci`                                               |
| Build Command     | `npm run build`                                        |
| Output Directory  | `dist`                                                 |
| Production Branch | `main` after frontend review and merge                 |
| Public API base   | `/api` (default; no environment variable is necessary) |

Use a preview deployment first. Do not set a model key, database path or secret in
Vercel frontend build variables. Do not set VITE_API_BASE_URL to the VPS hostname:
same-origin `/api` goes through the committed HTTPS rewrite.

`frontend/vercel.json` forwards `/api` and `/api/:path*` to the same API path at
`https://api.flareledger.fun`. Its non-API fallback serves `index.html` for Vue
Router deep links. Existing built assets retain Vercel's normal filesystem routing.
The configuration includes nosniff, referrer and device-permission headers.

## Verify the real deployment

Run these requests against the actual preview hostname printed by Vercel, then
repeat them after connecting the project domain:

```bash
WEB_ORIGIN='https://THE-ACTUAL-PREVIEW-HOSTNAME.vercel.app'
curl -i "$WEB_ORIGIN/api/health/ready"
curl -i "$WEB_ORIGIN/api/meta"
curl -i "$WEB_ORIGIN/api/records/FLARELEDGER-NONEXISTENT-ID"
curl -i -X POST "$WEB_ORIGIN/api/ask" \
  -H 'Content-Type: application/json' \
  --data '{"question":"PMMA"}'
```

Expect 200/JSON for readiness and metadata, 404/JSON for the missing record, and
503/JSON with llm_unavailable and retrieved_evidence for Ask. An API path must
never return the SPA HTML document. Verify that query parameters and POST bodies
reach the backend. Check the browser network panel for mixed content, CORS failures
and unexpectedly cached API responses.

Open and refresh `/investigations/PSI-25`, `/measurements` and
`/compare?ids=SERIES-FLEX-002-DropletData,SERIES-FLEX-003-DropletData`.
Verify their data, sources and error states, not just the HTML status.

After preview verification, attach **flareledger.fun** through the project's
Settings → Domains. Follow only the records Vercel displays for that project.
Keep `api.flareledger.fun` pointing to Timofey's VPS and preserve its current HTTPS
ingress. Confirm public HTTPS, catalogue and API readiness from another network.
Record the deployment URL, commit and verification time in infrastructure status.

## Recovery and remaining work

Use Vercel's prior verified deployment to roll back the web application. A frontend
rollback does not require touching SQLite, corpus ingestion, Nginx or QResto.

LLM integration, provider/quota verification, server-side request limits for an
enabled model, bilingual presentation and final submission remain separate tasks.
The current VPS lease ends on 1 December 2026; confirm the exact cutoff and keep a
tested off-VPS backup before judging or the lease end.
