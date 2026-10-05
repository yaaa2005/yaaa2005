"""Chat with Grok (xAI) from your own terminal.

Setup: put your key in a `.env` file next to this script:
    XAI_API_KEY=xai-...
Then run:  python grok_bot.py
"""
import json
import os
import sys
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent


def load_dotenv(path=HERE / ".env"):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv()

API_KEY = os.environ.get("XAI_API_KEY", "")
BASE_URL = os.environ.get("XAI_BASE_URL", "https://api.x.ai/v1").rstrip("/")
MODEL = os.environ.get("GROK_MODEL", "grok-4")
SYSTEM_PROMPT = os.environ.get("GROK_SYSTEM_PROMPT", "You are Grok, a helpful assistant.")


def stream_reply(messages):
    resp = requests.post(
        f"{BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"model": MODEL, "messages": messages, "stream": True},
        stream=True,
        timeout=120,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:500]}")

    reply = []
    for raw in resp.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith("data:"):
            continue
        data = raw[len("data:"):].strip()
        if data == "[DONE]":
            break
        delta = json.loads(data)["choices"][0].get("delta", {}).get("content") or ""
        print(delta, end="", flush=True)
        reply.append(delta)
    print()
    return "".join(reply)


def main():
    if not API_KEY:
        print("Missing XAI_API_KEY. Get one at https://console.x.ai and put it in "
              f"{HERE / '.env'} as:\n  XAI_API_KEY=xai-...")
        sys.exit(1)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print(f"Grok bot ({MODEL}) - type your message, '/reset' to clear, '/exit' to quit.\n")
    while True:
        try:
            user = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user:
            continue
        if user in ("/exit", "/quit"):
            break
        if user == "/reset":
            messages = messages[:1]
            print("(conversation cleared)\n")
            continue

        messages.append({"role": "user", "content": user})
        print("grok > ", end="", flush=True)
        try:
            messages.append({"role": "assistant", "content": stream_reply(messages)})
        except (requests.RequestException, RuntimeError) as e:
            messages.pop()
            print(f"\n[error] {e}")
        print()


if __name__ == "__main__":
    main()
