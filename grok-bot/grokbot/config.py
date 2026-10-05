"""Settings resolution for the local Grok bot."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_BASE_URL = "https://api.x.ai/v1"
DEFAULT_MODEL = "grok-4"
DEFAULT_SYSTEM_PROMPT = "You are Grok, a helpful and concise assistant."
DEFAULT_TIMEOUT = 120.0

ENV_FILE_NAME = ".env"


class ConfigError(Exception):
    """Raised when the bot cannot be configured."""


def load_env_file(path: Path) -> None:
    """Load ``KEY=value`` pairs from ``path`` without overriding real env vars."""
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return

    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export ") :].strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


def _find_env_file(start: Path) -> Path | None:
    for directory in (start, *start.parents):
        candidate = directory / ENV_FILE_NAME
        if candidate.is_file():
            return candidate
    return None


@dataclass
class Settings:
    api_key: str
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    timeout: float = DEFAULT_TIMEOUT


def load_settings(
    *,
    model: str | None = None,
    system_prompt: str | None = None,
    base_url: str | None = None,
    timeout: float | None = None,
    require_key: bool = True,
) -> Settings:
    """Build settings from CLI overrides, the environment, and a nearby ``.env``."""
    env_file = _find_env_file(Path.cwd()) or _find_env_file(Path(__file__).resolve().parent)
    if env_file is not None:
        load_env_file(env_file)

    api_key = (os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY") or "").strip()
    if require_key and not api_key:
        raise ConfigError(
            "No API key found. Put XAI_API_KEY=your-key in a .env file next to run.sh, "
            "or export it in your shell. Create a key at https://console.x.ai/."
        )

    env_timeout = os.environ.get("GROK_TIMEOUT")
    if timeout is None and env_timeout:
        try:
            timeout = float(env_timeout)
        except ValueError:
            raise ConfigError(f"GROK_TIMEOUT must be a number, got {env_timeout!r}") from None

    return Settings(
        api_key=api_key,
        model=model or os.environ.get("GROK_MODEL") or DEFAULT_MODEL,
        base_url=(base_url or os.environ.get("XAI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/"),
        system_prompt=system_prompt or os.environ.get("GROK_SYSTEM_PROMPT") or DEFAULT_SYSTEM_PROMPT,
        timeout=timeout if timeout is not None else DEFAULT_TIMEOUT,
    )
