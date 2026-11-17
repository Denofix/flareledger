# English project-form text

Copy only the paragraphs for the named field. Review factual changes before pasting. The final-project URL is https://flareledger.fun/. The final-demo URL must be the actual public file; no URL or completed submission is invented here. Add the repository in Detailed Description.

## Project Name

FlareLedger

## High-Level Project Summary

FlareLedger helps students, researchers and engineers explore NASA microgravity combustion research without losing the evidence behind an explanation. Users browse investigations, inspect original records and units, trace sources, and compare compatible measured curves. Optional Gemini interpretations use selected public context, claim-bound citations and visible limitations. Our frozen snapshot includes ten NASA PSI investigations, nine experimental tables and six measured series with 1,844 original points. The two-person Proofonauts team built and deployed a responsive application with persistent generation limits, monitoring and checked backups. This is a research exploration prototype, not validated fire-safety advice; full live answer evaluation and independent scientific review remain unfinished.

## Detailed Project Description

### Purpose and users

FlareLedger is a source-linked workspace for students, researchers and engineers exploring combustion in microgravity. It addresses Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data by making NASA resources easier to inspect and keeping generated interpretations visibly connected to their supplied evidence.

Users find an investigation, inspect a record, follow its original source locator, examine a measured curve and compare compatible quantities. Unknown values remain unavailable. A condition reference is not promoted into a completed experiment; historical incidents are not numerical laboratory measurements. Equal units do not make droplet diameter and flame diameter the same quantity.

### How it works

The Vue 3/TypeScript frontend uses a Python 3.12/FastAPI backend and checksum-verified SQLite snapshot. Source IDs, rows, original units, file versions, DOI and quality limitations are retained. Six numerical series contain 1,844 original points. External file catalogue entries are separate from embedded measurements.

Ask uses lexical retrieval to select bounded source packets, including original table cells and verified document text. Gemini returns claims with source/context references. The backend checks structure, exact context fragments and markers; the UI shows model, corpus and limitations. These checks do not prove scientific correctness or source-specific entailment. Search and source inspection remain useful when generation is unavailable.

### Value and limits

The project combines traceability with deliberate refusals: it exposes incompatible comparisons, missing values and unsupported conclusions instead of silently inventing them. It helps users formulate better questions and identify where original-source review is needed. We do not claim certified safety thresholds, causal effects or new experimental discoveries.

At PR22, 163 backend tests and 15 offline questions passed, with 45 matching anchors. Full current-release live answer evaluation and independent scientific review are unfinished. The question set was used during development, not held out as an independent benchmark. Broader retrieval and separate independent review questions are future work.

### Team, tools and delivery

Proofonauts has two members: Denis Voloshyn and Timofey. Denis coordinated scope, architecture, source preparation, SI integration and evaluation tooling. Timofey coordinated Docker/CI, deployment, monitoring, checked off-host backups, PR reviews, interface checks, screenshots and SI-assisted branding. Both reviewed evidence and integration decisions.

The frontend runs on Vercel; the API/SQLite run on a VPS behind HTTPS. Shared limits persist: ten reservations per rolling 24 hours, three per minute and one active call, without automatic retry or paid fallback. These limits are not a promise of current provider availability.

We practised full-stack integration, provenance, bounded neural-network use, testing, Git review, Linux delivery, backup recovery, responsive verification and English technical communication. SI assistance is disclosed; original numerical data are not represented as model-generated measurements.

Product: https://flareledger.fun/

Public source code and documentation: https://github.com/Denofix/flareledger

### Inline screenshot captions

Upload actual PNGs using Inline Image; do not paste local filesystem paths as public URLs. Existing captures show the previous flame branding; refresh selected shots after deployment without fabricating changes inside older evidence images.

1. Catalogue: Browse NASA PSI investigations and inspect the scope of the frozen source snapshot.
2. PMMA search: Trace a matching record to its source rather than treating a keyword match as a conclusion.
3. Row locator: Inspect original table-row provenance and file identity.
4. FLEX plot: View measured quantities and original units with their limitations.
5. Comparison refusal: Different physical quantities are not overlaid merely because their units match.
6. Genuine Ask result, only if captured: FlareLedger SI interpretation with source references, exact supplied-context excerpts and limitations; not independent scientific validation.

## Use of Super Intelligence (SI)

Yes. ChatGPT/Codex neural-network assistance supported planning and architecture options, code drafts, data parsing/provenance tooling, tests, debugging, retrieval/citation improvements, operational scripts, documentation and submission text. The team selected scope, reviewed changes, ran checks and made deployment decisions. Optional Gemini 3.6 Flash produces runtime interpretations from selected public context; no model was trained or fine-tuned. Original measurements are preserved; project summaries are not called verbatim NASA quotations. Timofey created the Proofonauts logo with neural-network assistance; served variants include visible SI markings. SI_USAGE.md documents tool use and human responsibilities. Mechanical checks do not establish scientific correctness, and full live answer evaluation is unfinished.

## NASA Data

We used a frozen source-linked NASA PSI snapshot: BASS-II (PSI-25), BASS (PSI-26), Saffire-I/II/III (PSI-98/99/100), FLEX (PSI-69), SAME-R (PSI-101), SAME (PSI-102), SPICE (PSI-107) and PSI-62 modeling/tomography metadata. Resources include nine experimental tables, selected FLEX raw text/test sheets, metadata and original ReadMe documents. Six charted series contain 1,844 original points. PSI-62 metadata does not imply included numerical simulation results. Original licenses, units and file versions are retained separately from the project's MIT license.

Investigation landing pages:

- https://psi.nasa.gov/physci/repo/data/investigations/PSI-25
- https://psi.nasa.gov/physci/repo/data/investigations/PSI-26
- https://psi.nasa.gov/physci/repo/data/investigations/PSI-98
- https://psi.nasa.gov/physci/repo/data/investigations/PSI-99
- https://psi.nasa.gov/physci/repo/data/investigations/PSI-100
- https://psi.nasa.gov/physci/repo/data/investigations/PSI-69
- https://psi.nasa.gov/physci/repo/data/investigations/PSI-101
- https://psi.nasa.gov/physci/repo/data/investigations/PSI-102
- https://psi.nasa.gov/physci/repo/data/investigations/PSI-107
- https://psi.nasa.gov/physci/repo/data/investigations/PSI-62

NASA combustion guidance, safety/history and Spinoff resources support contextual cards, not numerical BASS/FLEX measurements. The repository's docs/NASA_DATA.md lists all 46 source records and raw-file links, DOI and licensing boundaries. NASA has not endorsed the project.

## Space Agency Partner Data and Other References

Primary scientific resources are NASA PSI and the NASA contextual resources listed in docs/NASA_DATA.md. We make no claim to have used another agency's dataset. Software and infrastructure include Python, FastAPI, SQLite, Vue 3, TypeScript, Vite, Git/GitHub, GitHub Actions, Docker/Compose, Linux, Nginx and Vercel. ChatGPT/Codex assistance, Gemini runtime use and SI-assisted branding are disclosed. No NASA insignia is used as team branding. Dependency files and DATA_LICENSES.md record exact versions and separate terms.
