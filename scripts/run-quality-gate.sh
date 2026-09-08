#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$SCRIPT_DIR/run-python.sh" "$SCRIPT_DIR/quality_gate.py" "$@"
