# Team rules

## Decisions and ownership

Proofonauts consists of exactly two members: Denis Voloshyn (@Denofix) and Timofey (@Tymofii1912). Denis coordinates product scope, architecture, SI integration, evaluation and submission. Timofey coordinates infrastructure, review, delivery, monitoring, backup/recovery, interface verification, screenshots and SI-assisted branding. Earlier four-person proposals are superseded. Record one owner, the expected result and blockers for each task.

Use English for README, commit messages, PR titles, public UI, and submission material. Public project-authored documentation and dataset explanations also use English. Internal team guidance may use Ukrainian.

Use SI for neural-network assistance in public prose. Preserve official source text, technical identifiers, API fields and historical filenames. Disclose tool assistance honestly and retain visible SI markings on generated branding. See [SI_USAGE.md](SI_USAGE.md).

## Branches and reviews

1. Start each task from an up-to-date main branch.
2. Use a short-lived branch: feat/, fix/, infra/, data/, design/, or docs/.
3. Open a PR into main. Keep one clear purpose per PR.
4. Explain what changed, how it was checked, and what remains unfinished.
5. Obtain one review from another team member and pass the checks that actually apply.
6. Merge when the change is ready to share. Use squash merge for a clean task-level history.

These are the team workflow rules. GitHub enforcement is configured separately by the repository owner after the first workflow run and collaborator invitations. The initial repository setup is the bootstrap exception to the PR workflow.

## Coordination

Post a short progress update when starting, when blocked, and when ready for review. Discuss shared API, schema, dependency, or deployment changes before changing the contract. Avoid editing the same feature in competing branches without coordination.

Before the presentation, agree on a demo commit, record the public URL and local launch procedure, and keep a working local backup. Any late change must include its verification and a clear way to return to the demo commit.

## Credentials and infrastructure

Use personal GitHub accounts and personal SSH keys. Runtime credentials belong in the approved server environment or secret store. Commit only empty examples. Repository administration, DNS access, and runtime API access are distinct permissions.

On the QResto server, use a separate project directory, service names, state, and approved ingress route. Timofey confirms the existing proxy and resource headroom before selecting deployment configuration.

## Data and SI

Every included dataset needs a source, version, license note, and extraction method. Keep source limitations visible. A successful download is not a scientific review, and a generated explanation is not a verified experimental conclusion.

Live SI starts disabled. Confirm the official API provider, exact model ID, free quota, owner, timeout, concurrency limit, and failure response before enabling it. Search, data, charts, and sources must remain useful when generation is unavailable.

## Done criteria

A task is done when its result is committed, documented where necessary, checked using real commands, reviewed, and merged. Label partial work clearly. A domain purchase, an example environment file, or a planned command is not a completed deployment.
