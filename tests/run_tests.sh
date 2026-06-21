#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VENV="$ROOT/tests/.venv"
if [[ ! -d "$VENV" ]]; then
  python3 -m venv "$VENV"
fi

if [[ -x "$VENV/bin/python" ]]; then
  PYTHON="$VENV/bin/python"
elif [[ -x "$VENV/Scripts/python.exe" ]]; then
  PYTHON="$VENV/Scripts/python.exe"
else
  echo "Unable to locate virtualenv Python under $VENV" >&2
  exit 2
fi

"$PYTHON" -m pip install -q -r tests/requirements-test.txt
"$PYTHON" -m pytest tests/ -c tests/pytest.ini "$@"
