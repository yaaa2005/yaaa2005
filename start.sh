#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

pick_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo python3
  elif command -v python >/dev/null 2>&1; then
    echo python
  else
    echo "Python 3 is required. Install it from https://www.python.org/downloads/ then run this script again." >&2
    exit 1
  fi
}

PYTHON_BIN="$(pick_python)"
if [[ ! -d .venv ]]; then
  "$PYTHON_BIN" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt
echo
echo "Starting Grok on this computer (http://127.0.0.1:8787)"
echo "Not a virtual machine — this is your local Python app."
echo
exec python -m grok_bot serve
