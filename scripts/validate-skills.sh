#!/usr/bin/env bash
set -euo pipefail

# 用途：校验所有内部 Skill、manifest 和安装脚本；不会安装或覆盖任何本地 Skill。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/run-python.sh" "$SCRIPT_DIR/validate-skills.py"
