#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -d .venv ]]; then
  echo "Run ./start.sh once first so Python packages are installed."
  exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate
exec python -m grok_bot chat
