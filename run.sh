#!/usr/bin/env bash
# Start the Grok bot on this machine. Pass --web for the browser UI.
set -euo pipefail

cd "$(dirname "$0")"

for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    exec "$candidate" -m grokbot "$@"
  fi
done

echo "Python 3 was not found. Install it from https://www.python.org/downloads/ and try again." >&2
exit 1
