# SI use and human responsibility

SI means neural-network assistance in this project's public materials. The submission guide names the field **Use of Super Intelligence (SI)**. The accountable human team is **Denis Voloshyn and Timofey**; a model is a tool, not a third member.

## Development and text

ChatGPT/Codex assistance was used for planning and architecture options, implementation drafts for the Python/FastAPI backend and Vue/TypeScript frontend, source-data parsing and provenance tooling, tests, debugging, retrieval/citation fixes, operational scripts, documentation and submission text. SI-assisted brainstorming refined the selected challenge solution; we do not claim every idea or line of code was produced without assistance.

The team selected scope, ran checks, reviewed changes and made integration decisions. Timofey performed production operations and reported deployment and backup evidence. A generated patch or explanation was not accepted as proof that it worked. Additional tools should be listed only after the relevant member confirms actual use; access to a subscription is not evidence of use.

## Runtime interpretation

The optional Google Gemini adapter uses `gemini-3.6-flash` in the last reported production configuration. Only the question and bounded selected public corpus context are sent. Credentials stay on the backend. No model is trained or fine-tuned for this project; retrieval is lexical, without a vector embedding service.

The model returns claims with context/source IDs and exact context fragments. The backend validates structure and membership and renders markers. The UI attributes interpretations to FlareLedger and identifies model, corpus and limitations. Mechanical validation does not prove scientific correctness, causal effects or source-specific entailment. Search and measured data remain useful when generation is unavailable. Reserved failures count; there is no automatic retry or paid fallback.

## Data

The frozen snapshot records zero synthetic numerical values. Original measurements, units, missing values and source hashes are preserved. SI-assisted code/editorial work organizes and explains these sources; project-authored summaries and normalized quality notes are not verbatim NASA quotations or new experiments. Original corpus and evaluation fixture bytes remain hash-pinned. Official technical identifiers, fields and historical filenames stay compatible when public prose says SI.

## Visuals and audio

Timofey supplied the Proofonauts logo, and Denis confirmed it was created with neural-network assistance. Served variants contain visible SI markings, and the application also displays **SI-generated logo** beside the team credit. [Branding provenance](design/BRANDING.md) records the source and transformation. No NASA insignia, flag or mission logo was generated or modified for team branding.

Application screenshots capture the implemented interface; they are not generated mockups or invented measurements. Captions identify their limits. A typed question is not a generated answer. The implemented software and original decorative CSS were developed with SI assistance.

No generated narration or video is included in this change. If SI-created media are added later, apply the guide's visible generation marking for images/video and descriptive/metadata acknowledgement for audio before publication.

## Verification boundary

The 15 offline questions and 45 matching anchors validate selection against the frozen snapshot, not a 15/15 answer score. Earlier receipts belong to their recorded revisions. Full current-release live answer evaluation and independent scientific review remain unfinished unless a reviewed result archive establishes otherwise.

FlareLedger is an independent research exploration prototype, not validated fire-safety advice. NASA has not endorsed its implementation, branding or interpretations.

Machine-readable acknowledgement: [docs/SI_PROVENANCE.json](docs/SI_PROVENANCE.json).
