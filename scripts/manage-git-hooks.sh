#!/usr/bin/env bash
set -euo pipefail

FORCE=false
UNINSTALL=false

for argument in "$@"; do
  case "$argument" in
    --force) FORCE=true ;;
    --uninstall) UNINSTALL=true ;;
    *)
      echo "Usage: $0 [--force] [--uninstall]" >&2
      exit 2
      ;;
  esac
done

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$REPO_ROOT" ]]; then
  echo "ERROR: current directory is not inside a Git repository." >&2
  exit 1
fi

cd "$REPO_ROOT"
CURRENT="$(git config --local --get core.hooksPath || true)"

if [[ "$UNINSTALL" == "true" ]]; then
  if [[ -z "$CURRENT" ]]; then
    echo "Local Git hooks are not configured."
    exit 0
  fi
  if [[ "$CURRENT" != ".githooks" && "$FORCE" != "true" ]]; then
    echo "ERROR: core.hooksPath is '$CURRENT', not '.githooks'." >&2
    echo "Use --force --uninstall only after confirming the existing hook path may be removed." >&2
    exit 1
  fi
  git config --local --unset core.hooksPath
  echo "Local Git hook configuration removed."
  exit 0
fi

if [[ ! -d ".githooks" || ! -f "quality-gates.json" ]]; then
  echo "ERROR: .githooks or quality-gates.json is missing from repository root." >&2
  exit 1
fi

if [[ -n "$CURRENT" && "$CURRENT" != ".githooks" && "$FORCE" != "true" ]]; then
  echo "ERROR: core.hooksPath is already set to '$CURRENT'." >&2
  echo "Re-run with --force only after confirming the existing hooks may be replaced." >&2
  exit 1
fi

chmod +x .githooks/pre-commit .githooks/commit-msg .githooks/pre-push
chmod +x scripts/quality_gate.py scripts/run-python.sh scripts/run-quality-gate.sh
git config --local core.hooksPath .githooks

echo "Local Git hooks enabled:"
echo "  pre-commit  -> staged file checks"
echo "  commit-msg  -> commit message checks"
echo "  pre-push    -> branch and full local checks"
