# FlareLedger project instructions

FlareLedger is an independent NASA Space Apps hackathon project. Read README.md, docs/TECHNICAL_CONTRACT.md, TEAM_RULES.md, and DATA_LICENSES.md before changing its implementation.

## Repository state

This initial repository is a documentation and layout bootstrap. Inspect the current files before claiming that the application, dependencies, Docker images, importer, or deployment exist. Commands in the target contract become runnable only when their corresponding code and dependency files are added and verified.

## Implementation boundaries

- Keep the agreed top-level paths: backend/, frontend/, data/, infra/, scripts/, docs/, design/, presentation/.
- Use Python 3.12 for the planned backend. Keep app.main:app, port 8000, and the /api prefix unless an agreed contract change is documented.
- Use Vue 3, TypeScript, Vite, and npm for the planned frontend. Commit its real package-lock.json when dependencies are introduced.
- Keep all API credentials on the backend. VITE_* is public build configuration.
- Default LLM access to disabled. Keep the current API budget at USD 0 and do not enable billing or paid fallback.
- QResto is shared infrastructure. Inspect its existing ingress and available resources before preparing a deployment change.
- The project domain is flareledger.fun, registered through Vercel. DNS routing, hosting, and certificates remain deployment tasks.

## Public language

Use English for public project-authored files, README, UI, and dataset explanations. Internal Ukrainian guidance can be distributed separately. Preserve original scientific sources and exact numerical data. See docs/adr/0002-public-language.md.

## Scientific evidence

- Preserve original source IDs, DOI, file version, units, gravity regime, and source locators.
- Keep unknown or ambiguous values unavailable; never replace them with zero.
- Distinguish investigation metadata, actual trial rows, condition definitions, measured series, derived data, and historical context.
- Do not invent trial IDs, observations, curves, uncertainty, material properties, or source quotes.
- Keep generated explanations visibly attributed to FlareLedger. Do not imply NASA endorsement.
- Preserve dataset licenses separately from the MIT code license.

## Delivery

Work in a focused branch and summarize the change, validation, and remaining gaps. Run existing checks appropriate to the edited files. Add application checks when the corresponding implementation exists; do not add green placeholder build or test jobs.
