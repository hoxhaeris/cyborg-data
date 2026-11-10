#!/bin/bash
# Dynamic API Parity Check
# Validates that Go and Python implementations produce identical outputs.
#
# Exit codes:
#   0 - All parity checks passed
#   1 - Parity failures detected
#   2 - Infrastructure error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

# Run the parity check orchestrator.
# If PYTHON is set (e.g. CI pins an interpreter that already has the package and
# its dependencies installed), use it directly. Otherwise run through `uv`, which
# syncs the python/ project environment — including the git-sourced
# orgindex-schema dependency — before executing. A bare `python3` would lack
# that dependency and fail at import.
if [ -n "${PYTHON:-}" ]; then
    "${PYTHON}" parity/run_parity_check.py
else
    uv run --project "${REPO_ROOT}/python" python parity/run_parity_check.py
fi
