#!/usr/bin/env bash
set -euo pipefail

FORCE=false
if [[ "${1:-}" == "--force" ]]; then
  FORCE=true
elif [[ $# -gt 0 ]]; then
  echo "Unknown option: $1"
  echo "Usage: $0 [--force]"
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE_DIR="$REPO_ROOT/skills"
TARGET_DIR="$HOME/.grok/skills"

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "ERROR: skills directory not found: $SOURCE_DIR"
  exit 1
fi

mkdir -p "$TARGET_DIR"

timestamp="$(date +%Y%m%d-%H%M%S)"
installed=0
skipped=0

for skill_dir in "$SOURCE_DIR"/*; do
  [[ -d "$skill_dir" ]] || continue
  [[ -f "$skill_dir/SKILL.md" ]] || continue

  name="$(basename "$skill_dir")"
  target="$TARGET_DIR/$name"

  if [[ -L "$target" ]]; then
    current="$(readlink "$target" || true)"
    if [[ "$current" == "$skill_dir" ]]; then
      echo "[OK] $name already linked"
      ((skipped+=1))
      continue
    fi
  fi

  if [[ -e "$target" || -L "$target" ]]; then
    if [[ "$FORCE" != "true" ]]; then
      echo "[SKIP] $name already exists: $target"
      echo "       Re-run with --force to back it up and replace it."
      ((skipped+=1))
      continue
    fi

    backup="${target}.bak.${timestamp}"
    mv "$target" "$backup"
    echo "[BACKUP] $target -> $backup"
  fi

  ln -s "$skill_dir" "$target"
  echo "[LINK] $name -> $target"
  ((installed+=1))
done

echo
echo "Grok Skill installation complete."
echo "Source : $SOURCE_DIR"
echo "Target : $TARGET_DIR"
echo "Linked : $installed"
echo "Skipped: $skipped"
