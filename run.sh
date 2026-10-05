#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
[ -d venv ] || python3 -m venv venv
. venv/bin/activate
pip install -q -r requirements.txt
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Put your xAI key in $(pwd)/.env, then run ./run.sh again."
    exit 0
fi
python grok_bot.py
