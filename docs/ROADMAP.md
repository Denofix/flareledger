# Delivery status and remaining work

Updated 15 November 2026. Team: Denis Voloshyn and Timofey only. Evidence baseline: backend `969cb9460de9115fe0a16016bd02bf168aa7175e`. Production statements below are Timofey's operator report, not an assertion made from source inspection alone.

| Work | Status and evidence | Owner |
| --- | --- | --- |
| Corpus, importer and API | Implemented; frozen source hash, native tests and source-linked endpoints | Denis with Timofey review |
| Vue interface and charts | Implemented browsing, search, source pages and compatibility checks | Denis with Timofey verification |
| Deployment and recovery | Reported healthy Vercel/VPS deployment; checked backup copied off VPS | Timofey |
| Bounded Gemini Ask | Enabled on reported production release; defaults disabled for new installations | Both |
| Citation and retrieval fixes | PR20-22 merged; 163 backend tests at PR22 | Denis with Timofey review/deployment |
| Offline inspection | 15 questions and 45 anchors checked; not scientific answer grades | Denis |
| Current live answer evaluation | Separate journal prepared; no completed 15-case report provided | Timofey execution, Denis review |
| Final interface verification | Current-branding and genuine generated-answer captures still needed | Timofey |
| Submission text and branding | Prepared in this change; needs reviewed publication | Denis with Timofey review |
| Final demo and submission | Content plan prepared; final demo file/URL, participant checks and Submit for Judging remain owner actions | Denis |

Preserve the running backend and quota history during evaluation. Static branding/docs do not require a corpus migration or backend deployment. Record frontend and backend revisions separately. Run one AE-01 control after fresh operator preflight, then remaining cases individually as quota permits; retain failures and old-release results separately. Fix actual blockers through focused reviewed changes.

Submission preparation can proceed while scientific evaluation is unfinished. Describe that limitation honestly; do not invent a score or delay a valid partial submission solely to consume model calls. Confirm the public demo file, anonymous link access, recovery procedure and final confirmation banner before declaring submission complete.
