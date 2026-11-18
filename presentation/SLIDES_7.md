# Seven-slide demo content

> Historical hackathon material prepared on 15 November 2026. Development continues after the event; this file does not attest that a submission or pitch occurred. The current application uses the restored flame; see [branding provenance](../design/BRANDING.md).

Use exactly seven English slides, including title and closing content. This is a content plan, not a published slide file. Preserve the logo's visible SI marking. Use real screenshots; do not invent an answer-accuracy score.

## 1. FlareLedger

**Explore the research. Follow the evidence.**

Proofonauts: **Denys Voloshyn and Tymofii Chernoivanov**.
**Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data.**
2026 NASA Space Apps Challenge, Kyiv.

Visual: marked project logo and catalogue screenshot.

## 2. The problem

**Combustion data need context.**

- Conditions and quality notes are spread across sources.
- A table row is not automatically an independent experiment.
- An explanation is useful when its evidence can be inspected.

Visual: record and original-row locator; no invented hazard statistics.

## 3. NASA data, preserved

**A traceable snapshot, not synthetic measurements.**

- 10 PSI investigations; 9 experimental tables.
- 6 measured series; 1,844 original points.
- Source versions, units, hashes and limitations retained.

Visual: source page and FLEX plot. Credit BASS/BASS-II, FLEX, Saffire, SAME/SAME-R, SPICE and PSI-62; full references remain in the project description.

## 4. The user workflow

**Find -> inspect -> compare -> trace.**

- Search an investigation or material.
- Open records, units and source locators.
- Compare matching quantities and inspect limitations.

Visual: PMMA search and compatible comparison, large enough to read.

## 5. SI with evidence boundaries

**Source context first. Generated interpretation second.**

- Selected original cells/text are sent to Gemini.
- Claim-bound citations and markers are checked by the backend.
- Missing evidence and generation failures remain visible.

Visual: genuine generated answer if available. Otherwise caption the form as "Question form; no generated result shown", paired with the comparison refusal. Do not imply scientific validation.

## 6. What we built and checked

**A working application with explicit limits.**

- Vue/TypeScript, FastAPI/SQLite, Docker/CI and monitored deployment.
- 163 backend tests reported passing at PR22.
- 15 offline questions, 45 anchors; live answer review unfinished.

Visual: desktop/mobile product screens. Technical checks are not scientific accuracy. Update only from reviewed results.

## 7. Value and next steps

**Make evidence easier to inspect.**

For students, researchers and engineers exploring microgravity combustion. Next: independent answer review, broader source coverage and separate evaluation questions.

**Research exploration prototype. Not validated fire-safety advice.**
Try <https://flareledger.fun/>. Code/references: <https://github.com/Denofix/flareledger>.
Proofonauts - Denys Voloshyn and Tymofii Chernoivanov.

Visual: marked logo and product image. Do not add an eighth credits slide.
