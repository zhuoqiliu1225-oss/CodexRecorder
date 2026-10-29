#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
python_cmd="${PYTHON:-python3}"
if [[ -x .venv/bin/python3 ]]; then python_cmd=.venv/bin/python3; fi
"$python_cmd" scripts/install_skill.py "$@"
