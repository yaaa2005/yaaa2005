"""Terminal chat loop for the local Grok bot."""

from __future__ import annotations

import sys
from pathlib import Path

from .client import GrokClient, GrokError
from .config import Settings

try:  # Gives arrow-key history on macOS and Linux; absent on stock Windows.
    import readline  # noqa: F401
except ImportError:
    pass

HELP = """Commands:
  /help            show this message
  /reset           forget the conversation so far
  /system <text>   replace the system prompt and reset the conversation
  /model [name]    show or switch the model
  /save <file>     write the conversation to a text file
  /exit            quit (Ctrl-D also works)
"""


class Conversation:
    def __init__(self, system_prompt: str) -> None:
        self.system_prompt = system_prompt
        self.turns: list[dict[str, str]] = []

    def messages(self) -> list[dict[str, str]]:
        return [{"role": "system", "content": self.system_prompt}, *self.turns]

    def add(self, role: str, content: str) -> None:
        self.turns.append({"role": role, "content": content})

    def reset(self) -> None:
        self.turns.clear()

    def transcript(self) -> str:
        return "\n\n".join(f"{turn['role']}: {turn['content']}" for turn in self.turns)


def answer(client: GrokClient, messages: list[dict[str, str]], *, stream: bool) -> str:
    """Print the model's answer, streaming it when possible, and return the text."""
    if not stream:
        text = client.chat(messages)
        print(text)
        return text

    parts: list[str] = []
    try:
        for delta in client.stream_chat(messages):
            parts.append(delta)
            print(delta, end="", flush=True)
    except KeyboardInterrupt:
        print("\n[stopped]")
        return "".join(parts)
    if parts:
        print()
    return "".join(parts)


def run_once(client: GrokClient, settings: Settings, prompt: str, *, stream: bool) -> int:
    messages = [
        {"role": "system", "content": settings.system_prompt},
        {"role": "user", "content": prompt},
    ]
    try:
        answer(client, messages, stream=stream)
    except GrokError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


def run_chat(client: GrokClient, settings: Settings, *, stream: bool) -> int:
    conversation = Conversation(settings.system_prompt)
    print(f"Grok bot ready - model {client.model}. Type /help for commands, /exit to quit.\n")

    while True:
        try:
            line = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not line:
            continue
        if line.startswith("/"):
            if _handle_command(line, client, conversation) is False:
                return 0
            continue

        conversation.add("user", line)
        print("grok > ", end="", flush=True)
        try:
            reply = answer(client, conversation.messages(), stream=stream)
        except GrokError as error:
            print(f"\nerror: {error}")
            conversation.turns.pop()
            continue
        if reply:
            conversation.add("assistant", reply)
        print()


def _handle_command(line: str, client: GrokClient, conversation: Conversation) -> bool:
    """Run a slash command. Returns False when the bot should quit."""
    command, _, argument = line.partition(" ")
    argument = argument.strip()

    if command in ("/exit", "/quit"):
        return False
    if command == "/help":
        print(HELP)
    elif command == "/reset":
        conversation.reset()
        print("Conversation cleared.")
    elif command == "/system":
        if not argument:
            print(f"Current system prompt: {conversation.system_prompt}")
        else:
            conversation.system_prompt = argument
            conversation.reset()
            print("System prompt updated and conversation cleared.")
    elif command == "/model":
        if not argument:
            print(f"Current model: {client.model}")
        else:
            client.model = argument
            print(f"Model set to {argument}.")
    elif command == "/save":
        if not argument:
            print("Usage: /save <file>")
        else:
            path = Path(argument).expanduser()
            try:
                path.write_text(conversation.transcript(), encoding="utf-8")
            except OSError as error:
                print(f"Could not write {path}: {error}")
            else:
                print(f"Saved to {path}.")
    else:
        print(f"Unknown command {command}. Type /help.")
    return True
