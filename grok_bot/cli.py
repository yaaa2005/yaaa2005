from __future__ import annotations

import sys

from grok_bot import config
from grok_bot.client import GrokError, iter_chat


def run_cli() -> int:
    if not config.is_configured():
        print("No XAI_API_KEY found.")
        print("1. Copy .env.example to .env")
        print("2. Paste your key from https://console.x.ai/")
        print("3. Run this command again.")
        print("Or use the web app: python -m grok_bot serve")
        return 1

    print(f"Grok local chat  |  model: {config.model_name()}  |  running on this computer")
    print("Type a message and press Enter. Type /exit to quit.\n")
    history: list[dict[str, str]] = []
    while True:
        try:
            prompt = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return 0
        if not prompt:
            continue
        if prompt.lower() in {"/exit", "/quit", "exit", "quit"}:
            print("Bye.")
            return 0
        history.append({"role": "user", "content": prompt})
        print("Grok: ", end="", flush=True)
        reply_parts: list[str] = []
        try:
            for chunk in iter_chat(history):
                reply_parts.append(chunk)
                print(chunk, end="", flush=True)
        except GrokError as exc:
            print(f"\nError: {exc}")
            history.pop()
            continue
        print("\n")
        history.append({"role": "assistant", "content": "".join(reply_parts)})


if __name__ == "__main__":
    sys.exit(run_cli())
