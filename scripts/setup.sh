#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
python_cmd="${PYTHON:-python3}"
"$python_cmd" -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ required"'
command -v node >/dev/null || { echo 'Node.js 18+ required'; exit 1; }
node -e 'if(Number(process.versions.node.split(".")[0])<18)process.exit(1)'
if [[ -d .venv && ! -x .venv/bin/python3 ]]; then
  echo 'Existing .venv belongs to another platform or is incomplete. Use a separate checkout; do not copy a Windows virtual environment.'
  exit 1
fi
if [[ ! -x .venv/bin/python3 ]]; then "$python_cmd" -m venv .venv; fi
.venv/bin/python3 -m pip install -r requirements.txt
.venv/bin/python3 - <<'PY'
from pathlib import Path
import json
p=Path('local.settings.json')
if not p.exists():
    p.write_text(json.dumps({'model':'base','port':18764,'device':'auto','codex':'codex','cuda_library_dirs':[]},indent=2),encoding='utf-8')
PY
if [[ "${1:-}" != '--skip-translation-model' ]]; then
  .venv/bin/python3 scripts/prepare_translation.py
  .venv/bin/python3 - <<'PY'
import json
from pathlib import Path
p=Path('local.settings.json');settings=json.loads(p.read_text(encoding='utf-8-sig'))
settings['multilingual_model']='models/m2m100'
p.write_text(json.dumps(settings,ensure_ascii=False,indent=2),encoding='utf-8')
PY
fi
echo 'Dependencies installed. First start downloads, loads and warms up models.'
echo 'macOS uses CPU inference in this version; Apple GPU acceleration is not implemented.'
echo 'Next: bash scripts/install_skill.sh; node scripts/control.cjs serve'
echo 'Wait for engine.status=ready before recording. See docs/MACOS.md.'
