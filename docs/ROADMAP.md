# Implementation roadmap

## Start

| Task | Coordinator | Completion evidence |
| --- | --- | --- |
| Authenticate Ubuntu VM and clone main | Denis | gh auth status, correct account, clean clone |
| Confirm GitHub usernames and invite contributors | Denis | Accepted invitations and push access |
| Enable main branch rules | Denis | One approval and actual repository check required |
| Assign the first implementation tasks | Denis with the team | One owner and acceptance criteria per task |

## First implementation PRs

| Task | Proposed coordination | Completion evidence |
| --- | --- | --- |
| Backend scaffold and health endpoints | Denis and Sayat | Real dependency files, both health routes, readiness checks, existing tests |
| Frontend shell | Sayat with Ivan | package.json, lock file, working scripts, routes, /api proxy |
| Reviewed NASA seed and ingestion | Denis with backend developer | Source hash, explicit import command, versioned corpus, data checks |
| UI and evidence presentation | Ivan with frontend developer | Screens and states aligned with real available data |
| Docker and application CI | Timofey | Local builds and CI using the merged component commands |

These are coordination proposals. Confirm the implementer and availability in the team.

## Public demo

1. Timofey confirms permission, resource headroom, SSH access, and existing QResto ingress.
2. Select hosting, document the decision, and build the application at a known commit.
3. Connect flareledger.fun to that hosting and verify DNS and HTTPS.
4. Verify search, source links, charts, readiness, and AI-disabled behavior from another device.
5. Enable live AI only after official free access, the exact model, quotas, and failure behavior are verified.
6. Record the demo commit, local backup procedure, public URL, and an owner for recovery.

## Current open decisions

The hosting address, deploy user, ingress route, LLM provider/model, and the GitHub usernames of Timofey and Ivan are not confirmed in this repository. No additional server or LLM purchase is required for repository preparation.
