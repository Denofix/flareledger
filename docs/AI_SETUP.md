# Optional Gemini explanations

This change implements an opt-in adapter; it does not enable generation on the VPS.
The API budget remains **USD 0**, with no billing activation, paid fallback, automatic
retries or automatic provider/model substitution. Browsing, measurements, sources,
readiness and backups do not call a model.

## Verified access and limits

On 15 November 2026 Denis successfully tested `gemini-4-hydrogen` using the official
Google Gen AI Python SDK 3.3.0: the interaction completed and returned
`FLARELEDGER_OK`. This proves account/model access, not scientific answer quality
or successful execution of this adapter's structured-output request.

The FlareLedger project's AI Studio screen showed Free Tier and these Hydrogen
limits: **5 requests/minute, 250,000 tokens/minute and 20 requests/day**. Quotas
belong to the Google project, not an individual API key. Other tools using that
project consume the same allowance. Recheck the actual project before activation;
subscription access in the Gemini chat application is a separate entitlement.

Start this demo with **10 reservations per rolling 24 hours, 3 per rolling minute
and one active generation lease**. Do not increase limits to bypass the provider's
quota. Google resets daily request quotas at midnight Pacific; the application's
rolling window is deliberately more conservative. A public visitor can consume
this shared allowance; there is no per-user authentication or private judge quota.
If it is exhausted, evidence browsing still works. Do not use paid fallback.

### Explicit Gemini 3.6 Flash evaluation

`gemini-3.6-flash` is also accepted when selected explicitly with `LLM_MODEL`.
Google documents this stable model, Interactions support, structured JSON output,
`thinking_level=low` and a Standard Free Tier. Hydrogen remains the default;
there is no automatic substitution after an error. Check actual project access
and model quotas in AI Studio before a live evaluation. Listed Free Tier pricing
does not establish this project's eligibility or available quota.

The first Flash evaluation is still pending: offline transport tests establish
request construction and failure handling, not live access or scientific quality.
An observed upstream HTTP 503 from Hydrogen does not establish a permanent model
failure or prove that Flash will work. Google's API error reference describes 503
as temporary service overload or downtime.

Model selection uses the same SQLite reservation history. Switching model, key
or process does not refill the application's shared rolling quota. Keep the
existing database and limits, and do not enable billing as a workaround.

## Runtime configuration

All values are server environment variables, read when the API starts. Native
Python does not automatically load `.env`. Docker Compose reads its interpolation
file and forwards the explicitly listed settings to `api`.

| Variable | Initial value / behavior |
| --- | --- |
| `LLM_ENABLED` | `false` by default; enable explicitly after review and local evaluation |
| `LLM_PROVIDER` | `gemini` |
| `LLM_MODEL` | `gemini-4-hydrogen` by default; explicit `gemini-3.6-flash` also accepted |
| `GEMINI_API_KEY` | Secret in the backend environment; never Git, Vercel or `VITE_*` |
| `LLM_BASE_URL` | Empty; custom gateways/URLs are rejected |
| `ASK_MAX_REQUESTS_PER_DAY` | `0` by default; use `10` for the first controlled activation; allowed 1–18 |
| `ASK_MAX_REQUESTS_PER_MINUTE` | `0` by default; use `3`; allowed 1–3 |
| `LLM_MAX_CONCURRENT_REQUESTS` | `1`; other values disable generation |
| `LLM_TIMEOUT_SECONDS` | `30` network timeout; allowed 5–45 |
| `LLM_MAX_OUTPUT_TOKENS` | `2048`; allowed 512–4096, including thinking and output |

Missing credentials, invalid values, zero quotas or missing/incompatible Ask state
disable generation. A changed key does not reset the application's counters.
An OpenAI or other provider adapter is **not implemented**: changing its key and
model name alone will not make it work. The provider interface allows a separate
future implementation and review.

## Explicit additive migration

Take a verified SQLite backup first, using the existing recovery runbook. Import
the corpus only if this is a new local database. With the reviewed backend code
and its Python environment, from `backend/`:

```bash
python -m app.migrate_ask
```

Use the same `DATABASE_PATH` and `DATA_DIR` as the API. This command adds only
`fl_ask_schema`, `fl_ask_calls` and a time index. It preserves the original corpus,
source values, seed hash, corpus `user_version=1` and existing reservations.
Running it twice does not reset usage. Startup, GET routes and POST requests do
not create tables or silently migrate databases.

For Timofey's Docker deployment, keep generation disabled, create a fresh verified
backup, build/select the reviewed release with the existing deploy process, and
run the migration with that **same explicit image tag, Compose project and volume**:

```bash
docker compose -f compose.yaml -f compose.prod.yaml run --rm --no-deps api python -m app.migrate_ask
```

This is a runbook step, not authorization to execute it on the production VPS.
Do not run it from an unrelated checkout with the default `local` tag. Existing
deploy scripts do not automatically migrate Ask state. Restart/recreate the API
through the reviewed deployment process after changing its environment.

Reservations are committed to the corpus SQLite file **before** contacting Google.
Failed, timed-out, refused and invalid-output calls count. A transactional lease
serializes callers across processes; a crashed caller leaves its lease until
`timeout + 60` seconds. Network timeouts are socket timeouts, not a guarantee about
every possible OS/network stall. No background retries are performed.

Existing SQLite backup API snapshots include Ask counters. **Restoring an older
database can rewind usage**: keep `LLM_ENABLED=false` during recovery and re-enable
only after reconciling project usage or allowing the old allowance to expire.
A pre-migration snapshot remains corpus-ready but cannot generate until the
explicit migration. Image-only rollback does not remove the additive tables.

## Local controlled evaluation

After checks and review, use a private local backend terminal. Keep the key in
that shell; the following input does not echo it or put its value in history:

```bash
read -r -s -p "Gemini API key: " GEMINI_API_KEY
printf '\n'
export GEMINI_API_KEY
export LLM_PROVIDER=gemini LLM_MODEL=gemini-4-hydrogen
export ASK_MAX_REQUESTS_PER_DAY=10 ASK_MAX_REQUESTS_PER_MINUTE=3
export LLM_MAX_CONCURRENT_REQUESTS=1 LLM_TIMEOUT_SECONDS=30 LLM_MAX_OUTPUT_TOKENS=2048
export LLM_ENABLED=true
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

For an explicit Flash evaluation, use `export LLM_MODEL=gemini-3.6-flash` instead
of the Hydrogen model assignment **before starting that API process**. Use the
same existing `DATABASE_PATH`, credentials and limits. A launcher that hardcodes
Hydrogen must also be changed or replaced; setting a parent environment variable
does not override a later shell assignment inside that launcher.

From a second terminal, start the existing frontend with `npm run dev` and use
`/ask`. First inspect `/api/meta` and `/api/health/ready`; neither spends quota.
`live_generation_available` means configured and migrated, not a successful
live probe or proof that Google quota remains. Submit only a few reviewed
questions because the earlier access test already used project allowance.
Check every claim, citation, linked source, number, unit and limitation against
the original corpus. Include a question asking for an unsupported exact safety
threshold: it must not be presented as established experimental evidence.
Stop and revise the adapter if the structured request is rejected or the answer
is scientifically unsupported. Do not switch to a paid model as a workaround.

Stop Uvicorn and run `unset GEMINI_API_KEY LLM_ENABLED` when finished. Disabling
the provider on a running deployment requires restarting/recreating that API with
`LLM_ENABLED=false`. Do not share screenshots containing a key or a full env dump.

## Request and response contract

`POST /api/ask` accepts only `{"question":"..."}`, 1–1000 characters after trim,
and at most 8192 JSON bytes, including streamed requests. Users cannot select a
provider, URL, key, model, system prompt, output limit or tools.

Ask uses up to eight non-stopword keywords, OR matching and a stable match-count
rank to select up to five source-linked entities. `/api/search` retains its
existing AND keyword contract. Ask's context contains complete selected fields,
source IDs, quality issues and evidence locators within byte limits. Oversized
entities are omitted; original measured points and original file payloads are
not sent. This is lexical retrieval, not embeddings, scientific reasoning over
the full corpus, curve analysis or a search of the live web.

| HTTP / status | Behavior |
| --- | --- |
| 200 / `generated` | Plain-text explanation, verified context/source IDs, exact context excerpts, limitations, provider/model/corpus, `scientific_review=false` |
| 200 / `insufficient_evidence` | `answer=null`; no invented answer; no provider call if no context was retrieved |
| 429 / `rate_limited` | Shared local quota/lease reached; `Retry-After` and `retry_after_seconds`; retrieved evidence remains visible |
| 503 / `unavailable` | Disabled/missing state, provider quota, network/provider error, incomplete or invalid output; `answer=null`, evidence retained |
| 413 / 422 | Oversized body / invalid input; no provider call |

Every response is `Cache-Control: no-store`. Provider 429 does not cause retries
or paid fallback. The UI gives Ask a separate 55-second timeout, handles these
states and renders generated text with normal Vue escaping. Source links are
constructed from validated corpus IDs, never model-provided URLs.

## Scientific and data limits

The model must return structured JSON. The server rejects unknown context/source
IDs, non-exact context excerpts, unrecognized citation markers, new numeric tokens,
model-supplied links and missing support/limitations. These are mechanical checks;
they do **not** prove entailment, correct number-to-unit binding, causal validity,
complete support for every sentence or scientific correctness. Independent human
evaluation remains required before a judging demo.

An "exact context excerpt" can come from FlareLedger's authored source-based
summary or record JSON; it is not automatically a quotation from NASA. Answers
are visibly attributed to FlareLedger, with no NASA endorsement or fire-safety
certification. Do not infer extinguishment, safety thresholds, material rankings
or compatible conditions merely from shared units or the model's explanation.

Questions and selected public corpus context are sent to Google when enabled.
No key is included in the prompt, no arbitrary tools are enabled, and prompts,
answers and provider bodies are not written to application logs or SQLite.
`store=false` disables stored Interactions conversations; it is not a promise
that Google does no processing or training. Check the applicable Free Tier terms
before sending private data; this demo is intended for public source material.

Offline tests stub the model transport and use the real corpus. They cover quota
survival, backup/restore, cross-process reservation, invalid citations/numbers,
large bodies, configuration errors and frontend states. They consume no API quota
and do not establish that the live structured scientific answer has been reviewed.

Official implementation references:

- [Hydrogen model guidance](https://aistudio.google.com/docs/whats-new-gemini-4-hydrogen)
- [Gemini 3.6 Flash model](https://aistudio.google.com/docs/models/gemini-3.6-flash)
- [Thinking levels](https://aistudio.google.com/docs/thinking#thinking-levels)
- [Interactions API errors](https://aistudio.google.com/docs/api-errors)
- [Create Interaction](https://aistudio.google.com/api-reference/interactions-api/create-interaction)
- [Structured output](https://aistudio.google.com/docs/structured-output)
- [Rate limits](https://aistudio.google.com/docs/rate-limits)
- [Pricing and Free Tier](https://aistudio.google.com/docs/pricing)
