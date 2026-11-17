# Release evidence and limits

Baseline: 15 November 2026. Team: Denis Voloshyn and Timofey. Product: https://flareledger.fun/.

| Claim | Evidence and boundary |
| --- | --- |
| Backend | Timofey reported deployed `969cb9460de9115fe0a16016bd02bf168aa7175e` after PR22. GitHub confirms the merged source commit, not the running container by itself |
| Readiness | Operator reported HTTP 200 / ready through API and frontend |
| ReadMe | Operator reported 21,538 bytes, matching SHA256 inside the container and text reaching context |
| State | Operator reported corpus/quota history preserved, checked off-VPS backup and no PR22 migration |
| Generation | Operator reported Gemini enabled; defaults remain disabled. Limits: 10 per rolling 24 hours, 3 per minute, one active call. No static promise of remaining quota |
| Technical checks | 163 backend tests, Ruff, mypy and CI reported passing at PR22 |
| Retrieval | 15 questions, 45/45 anchors and targeted regressions checked offline; no scientific grade implied |
| Live evaluation | Separate 969cb94 journal prepared with all 15 NOT_RUN; no completed current-release result archive provided |
| Earlier receipts | Historical evidence for their own recorded revisions, not new-release success |
| Screenshots | 66 originals supplied by Timofey; capture revision and new generation not attested |
| This change | Static branding, public terminology and submission material; no backend retrieval, frozen seed, Ask schema or quota-policy change |

Record reviewed frontend and backend deployment revisions separately. This static frontend/docs change does not require VPS deployment or database migration. Do not redeploy a pinned backend solely to change a logo while evaluating it.

After integration, verify public assets and responsive navigation. Capture genuine Ask results only under a coordinated available allowance. A local preview, build or HTML shell is not proof that the public interface completed generation. Retain a checked off-host backup with actual usage history and a source-first local fallback before the demo.

Large context packets remain partial and retrieval is lexical. Exact excerpts, context/source membership and numeric-token checks do not prove entailment or number/unit binding. No causal effect, uncertainty, missing value, independent-trial count or universal safety threshold is invented. Historical incidents are not numerical experiments. The 15-case set was used during development, not held out as an independent benchmark. Full live and independent scientific review remain unfinished.
