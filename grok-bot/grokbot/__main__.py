"""Entry point: ``python3 -m grokbot`` for chat, ``--web`` for the browser UI."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .cli import run_chat, run_once
from .client import GrokClient, GrokError
from .config import DEFAULT_MODEL, ConfigError, load_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="grokbot",
        description="Chat with Grok from your own machine.",
    )
    parser.add_argument("prompt", nargs="*", help="ask one question and exit")
    parser.add_argument("--web", action="store_true", help="serve a local browser chat UI")
    parser.add_argument("--port", type=int, default=8777, help="port for --web (default: 8777)")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser with --web")
    parser.add_argument("-m", "--model", help=f"model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("-s", "--system", help="system prompt")
    parser.add_argument("--base-url", help="override the API base URL")
    parser.add_argument("--timeout", type=float, help="request timeout in seconds")
    parser.add_argument("--no-stream", action="store_true", help="wait for the full answer")
    parser.add_argument("--list-models", action="store_true", help="list models your key can use")
    parser.add_argument("--version", action="version", version=f"grokbot {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        settings = load_settings(
            model=args.model,
            system_prompt=args.system,
            base_url=args.base_url,
            timeout=args.timeout,
        )
    except ConfigError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    client = GrokClient(
        settings.api_key,
        model=settings.model,
        base_url=settings.base_url,
        timeout=settings.timeout,
    )

    if args.list_models:
        try:
            models = client.list_models()
        except GrokError as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
        print("\n".join(models) if models else "No models returned.")
        return 0

    if args.web:
        from .web import serve

        return serve(client, settings, port=args.port, open_browser=not args.no_browser)

    prompt = " ".join(args.prompt).strip()
    if not prompt and not sys.stdin.isatty():
        prompt = sys.stdin.read().strip()
    if prompt:
        return run_once(client, settings, prompt, stream=not args.no_stream)

    return run_chat(client, settings, stream=not args.no_stream)


if __name__ == "__main__":
    sys.exit(main())
