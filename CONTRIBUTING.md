# Contributing

Read the [team rules](TEAM_RULES.md) and [technical contract](docs/TECHNICAL_CONTRACT.md) before starting a task. New contributors should follow the [Ubuntu setup guide](docs/SETUP_UBUNTU_RU.md).

## Branch workflow

```bash
git switch main
git pull --ff-only origin main
git switch -c feat/your-task
```

Implement the task, then review and stage your actual changes:

```bash
python3 scripts/check_repository.py
git diff --check
git add -p
git diff --cached
git commit -m "feat: describe the completed change"
git push -u origin HEAD
gh pr create --base main --fill
```

Add new files explicitly with git add before committing; git add -p only selects changes to existing tracked files. Commit a dependency lock file when adding dependencies. Never commit runtime databases, credentials, or unreviewed bulk downloads.

Use readable commit prefixes such as feat:, fix:, docs:, infra:, data:, or chore:. A commit should describe the result for the next reader.

## Review

Use the PR template. Include the commands you actually ran and any checks that could not be run. Ask another team member to review. Resolve comments and required checks before merging. The author cannot approve their own PR.

```bash
gh pr checks --watch
```

After the PR is merged:

```bash
git switch main
git pull --ff-only origin main
```

## Checks available now

Run `python3 scripts/check_repository.py` from the repository root. It checks tracked Markdown links, UTF-8 text hygiene, JSON syntax, and conflict markers. GitHub runs the same repository check. This is not an application build, integration test, or scientific data validation.

Backend and frontend checks will be added alongside real dependency files and source code. The first application PRs must document their real install, lint, typecheck, build, and test commands. Timofey can then use those commands in CI.

## Contract changes

Document changes to routes, data schema, environment variables, installation commands, or deployment assumptions in the same PR. Preserve source provenance and dataset licenses. Use [architecture decisions](docs/adr/0001-repository-layout.md) for decisions that affect more than one component.
