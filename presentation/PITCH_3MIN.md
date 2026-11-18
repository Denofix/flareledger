# Three-minute local pitch script

> Historical hackathon material prepared on 15 November 2026. Development continues after the event; this file does not attest that a submission or pitch occurred. The current application uses the restored flame; see [branding provenance](../design/BRANDING.md).

Speakers: Denys Voloshyn and Tymofii Chernoivanov. Use the same seven English slides. Rehearse with a timer; word count does not prove duration. This local pitch is separate from the official 30-second video option. Do not browse the repository on stage.

## Slide 1 - Opening, about 20 seconds

Hello, we are Denys and Tymofii, the two-person Proofonauts team. Our project is FlareLedger, for the Flame in Freefall challenge. It helps people explore NASA microgravity combustion research and follow an explanation back to the evidence behind it.

## Slide 2 - Problem, about 25 seconds

Combustion data are valuable, but their meaning depends on conditions and limitations. A table row may describe an operating condition rather than an independent experiment. A missing value is not zero. We wanted an interface that keeps these distinctions visible instead of hiding them behind a confident summary.

## Slide 3 - NASA data, about 25 seconds

We organized a traceable snapshot of ten NASA PSI investigations, nine experimental tables and six measured series. The curves contain 1,844 original points. We preserve source identifiers, versions, units and quality notes. Historical fire accounts are clearly separated from numerical experiment data.

## Slide 4 - Product, about 30 seconds

Here is the workflow: find an investigation, search a material such as PMMA, inspect a record and open its original source locator. Then examine a measured FLEX curve or compare compatible series. The application refuses a misleading overlay when the physical quantities differ, even if both use the same unit.

## Slide 5 - SI, about 30 seconds

Ask adds an optional Gemini interpretation using selected public source context. Claims carry citations, and the backend checks structure, source membership and exact context fragments. This is a guard, not proof of scientific correctness. When evidence or generation is unavailable, users can still inspect retrieved sources. We disclose neural-network assistance in development, text and branding.

## Slide 6 - Delivery, about 25 seconds

We built a Vue and TypeScript interface with a FastAPI and SQLite backend. Tymofii handled deployment, monitoring and checked backups; I coordinated source preparation, SI integration and evaluation. At PR22, 163 backend tests and our offline inspection passed. The full live answer review is unfinished, so we do not claim a scientific accuracy score.

## Slide 7 - Closing, about 25 seconds

FlareLedger is for students, researchers and engineers who need to inspect evidence before drawing conclusions. It is a research exploration prototype, not certified fire-safety advice. Our next steps are independent answer review and broader source coverage. Try the application at flareledger.fun. Thank you.
