# Frontend review and Vercel handoff

The Vue interface and routing are deployed on Vercel with the primary domain
flareledger.fun. Production Gemini is explicitly enabled on the VPS; code defaults
remain disabled. The steps below are review/reconfiguration procedures, not a claim
that setup is still pending. See [current release audit](RELEASE_AUDIT.md).

## Review before merging

1. Run the four [frontend checks](../frontend/README.md#checks-and-build).
2. Start Vite with the local backend or the public development proxy described in
   the frontend README. Confirm corpus readiness and the reported corpus version.
3. Check the catalogue, a metadata-only investigation, a record with a missing
   value, a source link, FLEX measurements and an evidence search such as PMMA.
4. Open a comparison URL directly, refresh it and inspect an original point.
   Droplet diameter and flame diameter must not share an overlay. Source-specific
   camera/calibration limitations and unknown uncertainty must stay visible.
5. Check Ask error/disabled states locally with generation disabled or mocked
   responses. Production Ask spends shared allowance and requires separate
   authorization, a fresh preflight and a recorded single attempt. Do not submit
   a live question as an automatic UI smoke test.
   For controlled enabled-mode review, follow [AI setup](AI_SETUP.md); check model,
   source links, exact excerpts, limitations, insufficient evidence and quota states.
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

## Verify the real deployment with read-only checks

Run these requests against the actual preview hostname printed by Vercel, then
repeat them after connecting the project domain. Use reviewer-authorized access
if the preview is protected; a Vercel sign-in page is not an application response.
These checks use GET requests only and do not submit Ask or reserve its allowance:

```bash
WEB_ORIGIN='https://THE-ACTUAL-PREVIEW-HOSTNAME.vercel.app'
curl -i "$WEB_ORIGIN/api/health/ready"
curl -i "$WEB_ORIGIN/api/meta"
curl -i "$WEB_ORIGIN/api/records/FLARELEDGER-NONEXISTENT-ID"
curl -i "$WEB_ORIGIN/api/search?q=PMMA"
```

Expect 200/JSON for readiness, metadata and search, and 404/JSON for the missing
record. An API path must never return the SPA HTML document. Verify that the search
query parameter reaches the backend. Check the browser network panel for mixed
content, CORS failures and unexpectedly cached API responses.

Open and refresh `/investigations/PSI-25`, `/measurements` and
`/compare?ids=SERIES-FLEX-002-DropletData,SERIES-FLEX-003-DropletData`.
Verify their data, sources and error states, not just the HTML status.

After preview verification, attach **flareledger.fun** through the project's
Settings → Domains. Follow only the records Vercel displays for that project.
Keep `api.flareledger.fun` pointing to Tymofii's VPS and preserve its current HTTPS
ingress. Confirm public HTTPS, catalogue and API readiness from another network.
Record the deployment URL, commit and verification time in infrastructure status.

### Separately authorized live Ask verification

A deployment smoke test or ordinary frontend review does not authorize a live
Ask. Production generation has been enabled; a request may spend the shared
allowance even if it fails. Test disabled/error UI states locally with generation
disabled or mocked responses, as described above.

For a deliberately authorized single live attempt:

1. Agree with the operator on the exact target release, frozen question and who
   will submit it. Keep the existing questions, receipts and scientific grades.
2. Obtain a fresh [read-only operator preflight](AI_SETUP.md#read-only-operator-preflight)
   from the actual deployed API environment and database. Require
   `ready_to_attempt_generation=true`, `active_generation=false`, and positive
   `remaining_24h` and `remaining_60s`. Confirm the selected project's provider
   allowance separately: `provider_probed=false` is not proof of Google access.
3. Submit the agreed question once through `/ask`. Save a new, uniquely identified
   receipt with the exact question, frontend/backend release SHAs, deployment URL,
   model, corpus version, UTC start/end times, HTTP status and response. Retain
   the operator's before/after quota evidence; do not overwrite an earlier attempt.
4. Review the answer, exact context excerpts, citations, links and limitations.
   Apply the [response contract](AI_SETUP.md#request-and-response-contract):
   generated/insufficient-evidence 200, rate-limited 429 and unavailable 503 are
   different outcomes. Do not require 503 from an enabled deployment or grade a
   transport success as a scientific pass. Save failures/timeouts without retry;
   treat allowance as potentially consumed until the operator reconciles it.

## Recovery and remaining work

Use Vercel's prior verified deployment to roll back the web application. A frontend
rollback does not require touching SQLite, corpus ingestion, Nginx or QResto.

Production activation was operator-confirmed on 15 November 2026; this is not a
new provider probe. Full live scientific evaluation remains unfinished, and the
new release journal was prepared with 15 NOT_RUN outcomes. Historical presentation
and submission drafts are not current development gates.
The current VPS lease ends on 1 December 2026; confirm the exact cutoff and keep a
tested off-VPS backup before the lease end.
