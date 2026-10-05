from __future__ import annotations

import argparse
import sys
import webbrowser
from threading import Timer

import uvicorn

from grok_bot import config
from grok_bot.cli import run_cli
from grok_bot.server import app


def _open_browser(url: str) -> None:
    webbrowser.open(url)


def run_server(host: str, port: int, open_browser: bool) -> None:
    url = f"http://{host}:{port}"
    print(f"Grok local bot  ->  {url}")
    print("This is running on THIS computer, not in a virtual machine.")
    if not config.is_configured():
        print("No API key yet. The browser will ask you to paste one from https://console.x.ai/")
    if open_browser and host in {"127.0.0.1", "localhost"}:
        Timer(0.8, _open_browser, args=[url]).start()
    uvicorn.run(app, host=host, port=port, log_level="info")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Grok live on this computer (no VM)."
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="serve",
        choices=["serve", "chat"],
        help="serve = browser chat (default). chat = terminal chat.",
    )
    parser.add_argument("--host", default=config.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=config.DEFAULT_PORT)
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open a browser window.",
    )
    args = parser.parse_args(argv)

    if args.command == "chat":
        return run_cli()
    run_server(args.host, args.port, open_browser=not args.no_browser)
    return 0


if __name__ == "__main__":
    sys.exit(main())
