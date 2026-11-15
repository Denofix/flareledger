# Ubuntu and GitHub setup

Use a terminal inside the Ubuntu VM. The repository is already initialized; contributors clone it and work through pull requests. Application dependencies and runtime commands will be introduced with their implementations.

## Install Git and GitHub CLI

Check git --version and gh --version first. If GitHub CLI is unavailable or outdated, use its official package repository:

```bash
sudo apt update
sudo apt install -y git curl ca-certificates
sudo install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /tmp/flareledger-githubcli-keyring.gpg
sudo install -m 0644 /tmp/flareledger-githubcli-keyring.gpg /etc/apt/keyrings/githubcli-archive-keyring.gpg
printf '%s\n' "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install -y gh
```

Follow the [official installation documentation](https://github.com/cli/cli/blob/trunk/docs/install_linux.md) if a step fails.

## Authenticate

```bash
gh auth login --hostname github.com --git-protocol https --web --scopes repo,workflow
```

Enter the device code shown in the VM terminal at [github.com/login/device](https://github.com/login/device). The browser may run on Windows or inside the VM. Complete authentication, then run:

```bash
gh auth setup-git
gh auth status
gh api user --jq .login
```

Each contributor uses their own account. If an already authenticated account cannot push workflow changes, request the workflow scope with gh auth refresh --hostname github.com --scopes workflow. Device codes and credentials stay private.

## Configure commit identity

Set your own name and GitHub-verified or noreply email. Check the address in [GitHub email settings](https://github.com/settings/emails). For the repository owner:

```bash
git config --global user.name "Denis Voloshyn"
git config --global user.email "108155470+Denofix@users.noreply.github.com"
git config --global init.defaultBranch main
git config --global pull.ff only
git config --global fetch.prune true
git config --global core.autocrlf input
```

Git authentication controls access; commit identity records authorship. Other contributors must use their own identity.

## Clone and check

```bash
mkdir -p ~/projects
cd ~/projects
gh repo clone Denofix/flareledger
cd flareledger
git status --short --branch
python3 scripts/check_repository.py
```

For an existing clean clone, switch to main and pull with git pull --ff-only origin main. Keep work in a Linux filesystem directory. Read [CONTRIBUTING.md](../CONTRIBUTING.md) before editing.

## Team access

The owner manages invitations in [repository access settings](https://github.com/Denofix/flareledger/settings/access). Confirm exact accounts before inviting anyone. The confirmed two-person team uses Denofix and Tymofii1912; earlier proposals for additional participants are superseded.

Inspect pending invitations and accepted collaborators:

```bash
gh api --paginate repos/Denofix/flareledger/invitations --jq '.[] | {login: .invitee.login, permissions: .permissions}'
gh api --paginate repos/Denofix/flareledger/collaborators --jq '.[] | {login: .login, push: .permissions.push}'
```

For a personal repository, collaborators can push code while the owner manages administrative settings and secrets. A collaborator must accept an invitation before using the granted access.

## Main branch rules

In [Settings > Rules > Rulesets](https://github.com/Denofix/flareledger/settings/rules), create a branch ruleset named main-protection. Select Active and target the default branch or main explicitly. Require a PR, one approval, conversation resolution, and the actual Repository checks status check. Restrict deletion and block force pushes. Click Create to save and enforce it.

Have another contributor accept access before relying on one required approval. An author cannot approve their own PR. Keep code-owner approval optional while CODEOWNERS lists only the owner. Requiring signed commits is a separate configuration from web-based commit sign-off.

Current CI includes repository metadata, backend, frontend and infrastructure workflows. Inspect the actual run for the reviewed commit; historical green checks do not verify a later deployment.

## First development tasks

Follow [ROADMAP.md](ROADMAP.md): implement the backend and frontend scaffolds, an explicit data importer, and the corresponding real checks. Python 3.12 and Node 24 are the targets. Docker installation, if needed, follows the [official Ubuntu guide](https://docs.docker.com/engine/install/ubuntu/).

Domain instructions are in [DOMAIN_SETUP.md](DOMAIN_SETUP.md). Hosting and live LLM access remain separate decisions.
