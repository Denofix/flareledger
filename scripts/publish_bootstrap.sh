#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
FL_BOOTSTRAP_ROOT="$(pwd -P)"
FL_BOOTSTRAP_REMOTE="https://github.com/Denofix/flareledger.git"

for FL_BOOTSTRAP_TOOL in git gh python3; do
  command -v "$FL_BOOTSTRAP_TOOL" >/dev/null || {
    printf 'Missing tool: %s\n' "$FL_BOOTSTRAP_TOOL" >&2
    exit 1
  }
done

gh auth status --hostname github.com >/dev/null
FL_BOOTSTRAP_LOGIN="$(gh api user --jq .login)"
if [[ "${FL_BOOTSTRAP_LOGIN,,}" != "denofix" ]]; then
  printf 'Sign in as Denofix before publishing this bootstrap.\n' >&2
  exit 1
fi

FL_BOOTSTRAP_REPO="$(gh api repos/Denofix/flareledger --jq .full_name)"
if [[ "${FL_BOOTSTRAP_REPO,,}" != "denofix/flareledger" ]]; then
  printf 'Unexpected repository identity.\n' >&2
  exit 1
fi

if [[ ! -e .git ]]; then
  git init -b main
fi
if [[ "$(git rev-parse --show-toplevel)" != "$FL_BOOTSTRAP_ROOT" ]]; then
  printf 'Run from the unpacked flareledger repository, not a parent checkout.\n' >&2
  exit 1
fi
if git rev-parse --verify HEAD >/dev/null 2>&1; then
  printf 'Local commits already exist. Use the normal Git workflow.\n' >&2
  exit 1
fi
if [[ "$(git symbolic-ref --short HEAD)" != "main" ]]; then
  printf 'The initial branch must be main.\n' >&2
  exit 1
fi
if git remote get-url origin >/dev/null 2>&1; then
  if [[ "$(git remote get-url origin)" != "$FL_BOOTSTRAP_REMOTE" ]]; then
    printf 'origin differs from the expected Denofix/flareledger URL.\n' >&2
    exit 1
  fi
else
  git remote add origin "$FL_BOOTSTRAP_REMOTE"
fi

FL_BOOTSTRAP_REFS="$(git ls-remote origin)"
if [[ -n "$FL_BOOTSTRAP_REFS" ]]; then
  printf 'Remote refs already exist. Refusing to overwrite repository history.\n' >&2
  exit 1
fi

git var GIT_AUTHOR_IDENT >/dev/null
git --literal-pathspecs add --pathspec-from-file=scripts/bootstrap-files.txt
python3 - <<'PY'
import pathlib
import subprocess

expected = set(pathlib.Path("scripts/bootstrap-files.txt").read_text().splitlines())
staged = set(subprocess.check_output(["git", "diff", "--cached", "--name-only", "-z"]).decode().split("\0")) - {""}
if staged != expected:
    raise SystemExit("Staged files differ from the prepared bootstrap manifest. Review git status before publishing.")
PY
python3 scripts/check_repository.py
git diff --cached --check
git commit -m "chore: bootstrap FlareLedger monorepo"
git push -u origin main
printf 'Published to https://github.com/Denofix/flareledger\n'
